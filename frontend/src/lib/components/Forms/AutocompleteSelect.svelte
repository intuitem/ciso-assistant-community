<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock } from '$lib/utils/types';
	import { onMount } from 'svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import { getSearchTarget, normalizeSearchString } from '$lib/utils/helpers';
	import MultiSelect from 'svelte-multiselect';
	import { getContext, onDestroy } from 'svelte';
	import * as m from '$paraglide/messages.js';
	import { run } from 'svelte/legacy';

	interface Option {
		label: string;
		value: string | number;
		suggested?: boolean;
		translatedLabel?: string;
		path?: string[];
		infoString?: {
			string: string;
			position: 'suffix' | 'prefix';
			classes?: string;
		};
		contentType?: string;
	}

	type FieldContext = 'form-input' | 'filter-input';

	interface Props {
		fieldContext?: FieldContext;
		label?: string | undefined;
		baseClass?: string;
		field: string;
		valuePath?: string; // Default will be handled in destructuring
		helpText?: string | undefined;
		form: SuperForm<Record<string, unknown>, any>;
		resetForm?: boolean;
		multiple?: boolean;
		nullable?: boolean;
		mandatory?: boolean;
		disabled?: boolean;
		hidden?: boolean;
		translateOptions?: boolean;
		options?: Option[];
		optionsEndpoint?: string;
		optionsDetailedUrlParameters?: [string, string][];
		optionsLabelField?: string;
		optionsValueField?: string;
		browserCache?: RequestCache;
		optionsExtraFields?: [string, string][];
		optionsInfoFields?: {
			fields: {
				field: string; // Field name in the object
				path?: string; // Optional, used for nested fields};
				translate?: boolean; // Optional, used for translating the field
				display?: (value: any) => string;
			}[];
			position?: 'suffix' | 'prefix'; // Default: 'suffix'
			separator?: string; // Default: ' '
			classes?: string; // Optional, used for custom styling
		};
		pathField?: string;
		optionsSuggestions?: any[];
		optionsSelf?: any;
		optionsSelfSelect?: boolean;
		allowUserOptions?: boolean | 'append';
		onChange: (value: any) => void;
		cacheLock?: CacheLock;
		cachedValue?: any[] | undefined;
		mount?: (value: any) => void;
	}

	let {
		fieldContext = 'form-input',
		label = undefined,
		baseClass = '',
		field,
		valuePath = field,
		helpText = undefined,
		form,
		resetForm = false,
		multiple = false,
		nullable = false,
		mandatory = false,
		disabled = false,
		hidden = false,
		translateOptions = true,
		options = [],
		optionsEndpoint = '',
		optionsDetailedUrlParameters = [],
		optionsLabelField = 'name',
		optionsValueField = 'id',
		browserCache = 'default',
		optionsExtraFields = [],
		optionsInfoFields = {
			fields: [],
			position: 'suffix',
			separator: ' ',
			classes: 'text-surface-500'
		},
		pathField = '',
		optionsSuggestions = [],
		optionsSelf = null,
		optionsSelfSelect = false,
		allowUserOptions = false,
		onChange = () => {},
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x: any) => x
		},
		cachedValue = $bindable(),
		mount = () => null
	}: Props = $props();

	if (translateOptions) {
		options = options.map((option) => {
			return {
				...option,
				translatedLabel:
					safeTranslate(option.label) !== option.label
						? safeTranslate(option.label)
						: safeTranslate(option.value) !== option.value
							? safeTranslate(option.value)
							: option.label
			};
		});
	}

	let optionHashmap: Record<string, Option> = {};
	let _disabled = $state(disabled);

	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	let selected: typeof options = $state([]);
	let selectedValues: (string | undefined)[] = $derived(
		selected.map((item) => item.value || item.label || item)
	);
	let isInternalUpdate = false;
	let optionsLoaded = $state(Boolean(options.length));
	const initialValue = resetForm ? undefined : $value;
	const default_value = nullable ? null : selectedValues[0];

	const multiSelectOptions = {
		minSelect: $constraints && $constraints.required === true ? 1 : 0,
		maxSelect: multiple ? undefined : 1,
		liSelectedClass: multiple ? '!chip !preset-filled' : '!bg-transparent',
		inputClass: 'focus:ring-0! focus:outline-hidden!',
		outerDivClass: '!input !bg-surface-100 !px-2 !flex',
		closeDropdownOnSelect: !multiple
	};

	let isLoading = $state(false);
	const updateMissingConstraint = getContext<Function>('updateMissingConstraint');
	async function fetchOptions() {
		isLoading = true;
		try {
			if (optionsEndpoint) {
				let endpoint = `/${optionsEndpoint}`;
				const urlParams = new URLSearchParams();

				if (Array.isArray(optionsDetailedUrlParameters)) {
					for (const [param, value] of optionsDetailedUrlParameters) {
						if (param && value) {
							urlParams.append(encodeURIComponent(param), encodeURIComponent(value));
						}
					}
				}

				const queryString = urlParams.toString();
				if (queryString) {
					endpoint += endpoint.includes('?') ? '&' : '?';
					endpoint += queryString;
				}
				const response = await fetch(endpoint, { cache: browserCache });
				if (response.ok) {
					const data = await response.json().then((res) => res?.results ?? res);
					if (data.length > 0) {
						options = processOptions(data);
					}
					const isRequired = mandatory || $constraints?.required;
					const hasNoOptions = options.length === 0;
					const isMissing = isRequired && hasNoOptions;
					if (updateMissingConstraint) {
						updateMissingConstraint(field, isMissing);
					}
					optionsLoaded = true;
				}
			}
			// After options are loaded, set initial selection using stored initial value
			if (initialValue) {
				selected = options.filter((item) =>
					Array.isArray(initialValue)
						? initialValue.includes(item.value)
						: item.value === initialValue
				);
			} else if (options.length === 1 && $constraints?.required) {
				selected = [options[0]];
			}
		} catch (error) {
			console.error(`Error fetching ${optionsEndpoint}:`, error);
		} finally {
			isLoading = false;
		}
	}

	function processOptions(objects: any[]) {
		const append = (x: string, y: string) => (!y ? x : !x || x == '' ? y : x + ' - ' + y);

		return objects
			.map((object) => {
				const mainLabel =
					optionsLabelField === 'auto'
						? append(object.ref_id, object.name || object.description)
						: getNestedValue(object, optionsLabelField);

				const extraParts = optionsExtraFields.map((fieldPath) => {
					const value = getNestedValue(object, fieldPath[0], fieldPath[1]);
					return value !== undefined ? value.toString() : '';
				});

				const path: string[] =
					pathField && object?.[pathField]
						? object[pathField].map((obj: { str: string; id: string }) => {
								return obj.str;
							})
						: [];

				const infoFields = optionsInfoFields.fields
					.map((f) => {
						const value = getNestedValue(object, f.field, f.path);
						return f.display ? f.display(value) : f.translate ? safeTranslate(value) : value;
					})
					.filter(Boolean);

				let infoString: { string: string; position: 'suffix' | 'prefix' } | undefined = undefined;
				if (infoFields.length > 0) {
					const separator = optionsInfoFields.separator || ' ';
					const position = optionsInfoFields.position || 'suffix';
					infoString = {
						string: infoFields.join(separator),
						position: position,
						...optionsInfoFields
					};
				}

				const fullLabel = `${extraParts.length ? extraParts.join('/') + '/' : ''}${mainLabel}`;
				const valueField = getNestedValue(object, optionsValueField);

				return {
					label: fullLabel,
					value: valueField,
					suggested: optionsSuggestions?.some(
						(s) => getNestedValue(s, optionsValueField) === valueField
					),
					translatedLabel:
						safeTranslate(fullLabel) !== fullLabel
							? safeTranslate(fullLabel)
							: safeTranslate(valueField) !== valueField
								? safeTranslate(valueField)
								: fullLabel,
					path,
					infoString,
					contentType: object?.content_type || ''
				};
			})
			.filter(
				(option) =>
					optionsSelfSelect || option.value !== getNestedValue(optionsSelf, optionsValueField)
			)
			.sort((a, b) => {
				// Show suggested items first
				if (a.suggested && !b.suggested) return -1;
				if (!a.suggested && b.suggested) return 1;
				// Sort folder by path
				if (a.contentType && b.contentType) {
					const aPath = a.path.join('') + a.label;
					const bPath = b.path.join('') + b.label;
					const alphaCompare = aPath.localeCompare(bPath);
					return alphaCompare !== 0 ? alphaCompare : aPath.length - bPath.length;
				}

				return a.translatedLabel!.toLowerCase().localeCompare(b.translatedLabel!.toLowerCase());
			});
	}

	function getNestedValue(obj: any, path: string, field = '') {
		if (field) return obj[path]?.[field];
		return path.split('.').reduce((o, p) => (o || {})[p], obj);
	}

	onMount(async () => {
		await fetchOptions();
		mount($value);
		const cacheResult = await cacheLock.promise;
		if (cacheResult && cacheResult.length > 0) {
			selected = cacheResult.map((value: string | number) => optionHashmap[value]).filter(Boolean);
		}
	});

	$effect(() => {
		if (!isInternalUpdate && $value && optionsLoaded && $value !== initialValue) {
			const valueArray = Array.isArray($value) ? $value : [$value];
			if (valueArray.length !== 0) {
				selected = options.filter((item) => valueArray.includes(item.value));
			}
		}
	});

	async function handleSelectChange() {
		if (allowUserOptions && selectedValues.length > 0) {
			for (const val of selectedValues) {
				if (!options.some((opt) => opt.value === val)) {
					const newOption: Option = { label: val as string, value: val as string };
					options = [...options, newOption];
				}
			}
		}

		// change($value);
		await onChange($value);
		// dispatch('cache', selected);
	}

	function arraysEqual(
		arr1: string | (string | undefined)[] | null | undefined,
		arr2: string | (string | undefined)[] | null | undefined
	): boolean {
		const normalize = (val: string | (string | undefined)[] | null | undefined) => {
			if (typeof val === 'string') return [val];
			return val ?? [];
		};

		const a1 = normalize(arr1);
		const a2 = normalize(arr2);

		if (a1.length !== a2.length) return false;

		const set1 = new Set(a1);
		const set2 = new Set(a2);

		for (const value of set1) {
			if (!set2.has(value)) return false;
		}

		return true;
	}

	run(() => {
		optionHashmap = options.reduce((acc, option) => {
			acc[option.value] = option;
			return acc;
		}, {});
	});

	run(() => {
		cachedValue = selected.map((option) => option.value);
	});

	run(() => {
		// Only update value after options are loaded
		if (!isInternalUpdate && optionsLoaded && !arraysEqual(selectedValues, $value)) {
			isInternalUpdate = true;
			$value = multiple ? selectedValues : (selectedValues[0] ?? default_value);
			handleSelectChange();
			isInternalUpdate = false;
		}
	});

	run(() => {
		_disabled =
			disabled || Boolean(selected.length && options.length === 1 && $constraints?.required);
	});

	onDestroy(() => {
		if (updateMissingConstraint) {
			updateMissingConstraint(field, false);
		}
	});

	const searchTargetMap = $derived(new Map(options.map((opt) => [opt, getSearchTarget(opt)])));

	const fastFilter = (opt: Option, searchText: string) => {
		if (!searchText) {
			return true;
		}

		const target = searchTargetMap.get(opt) || '';

		const normalizedSearch = normalizeSearchString(searchText);
		const searchTerms = normalizedSearch.split(' ').filter(Boolean);

		if (searchTerms.length === 0) {
			return true;
		}

		return searchTerms.every((term) => target.includes(term));
	};
</script>

<div class={baseClass} {hidden}>
	{#if label !== undefined}
		{#if $constraints?.required || mandatory}
			<label class="text-sm font-semibold" for={field}
				>{label} <span class="text-red-500">*</span></label
			>
		{:else}
			<label class="text-sm font-semibold" for={field}>{label}</label>
		{/if}
	{/if}
	{#if $errors && $errors._errors}
		<div>
			{#each $errors._errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{:else if $errors && $errors.length > 0}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	<div
		class="control overflow-x-clip flex items-center space-x-2"
		data-testid="{fieldContext}-{field.replaceAll('_', '-')}"
	>
		{#if Array.isArray($value)}
			{#each $value as val}
				<input type="hidden" name={field} value={val} />
			{/each}
		{:else if $value}
			<input type="hidden" name={field} value={$value} />
		{/if}

		<MultiSelect
			bind:selected
			{options}
			{...multiSelectOptions}
			disabled={_disabled}
			allowEmpty={true}
			{allowUserOptions}
			duplicates={false}
			key={JSON.stringify}
			filterFunc={fastFilter}
		>
			{#snippet option({ option })}
				{#if option.infoString?.position === 'prefix'}
					<span class="text-xs {option.infoString.classes}">
						{option.infoString.string}
					</span>
				{/if}
				{#if option.path}
					<span>
						{#each option.path as item}
							<span class="text-surface-500 font-light">
								{item} /&nbsp;
							</span>
						{/each}
					</span>
				{/if}
				{#if translateOptions && option}
					{#if field === 'ro_to_couple'}
						{@const [firstPart, ...restParts] = option.label.split(' - ')}
						{safeTranslate(firstPart)} - {restParts.join(' - ')}
					{:else}
						{option.translatedLabel}
					{/if}
				{:else}
					{option.label || option}
				{/if}
				{#if option.infoString?.position === 'suffix'}
					<span class="text-xs {option.infoString.classes}">
						{option.infoString.string}
					</span>
				{/if}
				{#if option.suggested}
					<span class="text-sm text-surface-500"> {m.suggestedParentheses()}</span>
				{/if}
			{/snippet}
			{#snippet selectedItem({ option })}
				{#if option.infoString?.position === 'prefix'}
					<span class="text-xs text-surface-500">&nbsp;{option.infoString.string}</span>
				{/if}
				{#if option.path}
					<span>
						{#each option.path as item, idx}
							<span class="text-xs font-light">
								{item}
								{#if idx < option.path.length - 1}
									&nbsp;/
								{/if}&nbsp;
							</span>
						{/each}
					</span>
				{/if}
				{#if translateOptions && option}
					{#if field === 'ro_to_couple'}
						{@const [firstPart, ...restParts] = option.label.split(' - ')}
						{safeTranslate(firstPart)} - {restParts.join(' - ')}
					{:else}
						{option.translatedLabel}
					{/if}
				{:else}
					{option.label || option}
				{/if}
				{#if option.infoString?.position === 'suffix'}
					<span class="text-xs text-surface-500">&nbsp;{option.infoString.string}</span>
				{/if}
				{#if option.suggested}
					<span class="text-sm text-surface-500"> {m.suggestedParentheses()}</span>
				{/if}
			{/snippet}
		</MultiSelect>
		{#if isLoading}
			<svg
				class="animate-spin h-5 w-5 text-primary-500 loading-spinner"
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				data-testid="loading-spinner"
			>
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
				></circle>
				<path
					class="opacity-75"
					fill="currentColor"
					d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
				></path>
			</svg>
		{/if}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500 whitespace-pre-line">{helpText}</p>
	{/if}
</div>
