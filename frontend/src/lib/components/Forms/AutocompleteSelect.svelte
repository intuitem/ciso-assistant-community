<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock } from '$lib/utils/types';
	import { onMount } from 'svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import { createEventDispatcher } from 'svelte';
	import MultiSelect from 'svelte-multiselect';
	import { getContext, onDestroy } from 'svelte';
	import * as m from '$paraglide/messages.js';
	import { toCamelCase } from '$lib/utils/locales';

	interface Option {
		label: string;
		value: string | number;
		suggested?: boolean;
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
		hidden?: boolean;
		translateOptions?: boolean;
		options?: Option[];
		optionsEndpoint?: string;
		optionsDetailedUrlParameters?: [string, string][];
		optionsLabelField?: string;
		optionsValueField?: string;
		browserCache?: RequestCache;
		optionsExtraFields?: [string, string][];
		optionsSuggestions?: any[];
		optionsSelf?: any;
		optionsSelfSelect?: boolean;
		allowUserOptions?: boolean | 'append';
		onChange: (value: any) => void;
		cacheLock?: CacheLock;
		cachedValue?: any[] | undefined;
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
		hidden = false,
		translateOptions = true,
		options = [],
		optionsEndpoint = '',
		optionsDetailedUrlParameters = [],
		optionsLabelField = 'name',
		optionsValueField = 'id',
		browserCache = 'default',
		optionsExtraFields = [],
		optionsSuggestions = [],
		optionsSelf = null,
		optionsSelfSelect = false,
		allowUserOptions = false,
		onChange = () => {},
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x: any) => x
		},
		cachedValue = $bindable()
	}: Props = $props();

	const norm = (v: any) => (v == null ? '' : String(v));
	const lc = (v: any) => norm(v).trim().toLowerCase();
	function getNestedValue(obj: any, path: string, field = '') {
		if (field) return obj?.[path]?.[field];
		return path.split('.').reduce((o, p) => (o || {})[p], obj);
	}

	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	let optionHashmap: Record<string, Option> = {};
	let disabled = $state(false);
	// Allow strings (typed text) + Option objects from MultiSelect
	let selected: (Option | string)[] = $state([]);
	let selectedValues: (string | undefined)[] = $derived(
		selected.map((item) =>
			typeof item === 'string' ? item : ((item.value as any) ?? item.label ?? (item as any))
		)
	);

	let isInternalUpdate = false;
	let optionsLoaded = $state(Boolean(options.length));
	const initialValue = resetForm ? undefined : $value;
	const default_value = nullable ? null : selectedValues[0];

	// Disable user-created options until options are ready (prevents the early mis-add)
	const effectiveAllowUserOptions = $derived(optionsLoaded ? allowUserOptions : false);
	const multiSelectOptions = {
		minSelect: $constraints && $constraints.required === true ? 1 : 0,
		maxSelect: multiple ? undefined : 1,
		liSelectedClass: multiple ? '!chip !preset-filled' : '!bg-transparent',
		inputClass: 'focus:ring-0! focus:outline-hidden!',
		outerDivClass: '!input !px-2 !flex',
		closeDropdownOnSelect: !multiple
	};
	const dispatch = createEventDispatcher();
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
					if (data?.length > 0) {
						options = processOptions(data);
					}
					const isRequired = mandatory || $constraints?.required;
					const hasNoOptions = options.length === 0;
					const isMissing = isRequired && hasNoOptions;
					if (updateMissingConstraint) updateMissingConstraint(field, isMissing);
					optionsLoaded = true;
				}
			}
			// After options are loaded, set initial selection using stored initial value
			if (initialValue) {
				const iv = Array.isArray(initialValue) ? initialValue.map(norm) : [norm(initialValue)];
				selected = options.filter((item) => iv.includes(norm(item.value)));
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

				const fullLabel =
					optionsExtraFields.length > 0 ? `${extraParts.join('/')}/${mainLabel}` : mainLabel;

				const rawVal = getNestedValue(object, optionsValueField);
				return {
					label: fullLabel,
					value: rawVal,
					suggested: optionsSuggestions?.some(
						(s) => getNestedValue(s, optionsValueField) === rawVal
					)
				} as Option;
			})
			.filter(
				(option) =>
					optionsSelfSelect || option.value !== getNestedValue(optionsSelf, optionsValueField)
			)
			.sort((a, b) => (a.suggested && !b.suggested ? -1 : !a.suggested && b.suggested ? 1 : 0));
	}

	onMount(async () => {
		await fetchOptions();
		dispatch('mount', $value);
		const cacheResult = await cacheLock.promise;
		if (cacheResult && cacheResult.length > 0) {
			selected = cacheResult
				.map((v: string | number) => optionHashmap[norm(v)] ?? norm(v))
				.filter(Boolean);
		}
	});

	// Build hashmap early (before DOM update)
	$effect.pre(() => {
		optionHashmap = options.reduce(
			(acc, option) => {
				acc[norm(option.value)] = option;
				return acc;
			},
			{} as Record<string, Option>
		);
	});

	// Coerce typed strings in `selected` to existing options ASAP (before other effects)
	$effect.pre(() => {
		if (!options.length || !selected.length) return;
		let changed = false;
		const coerced = selected.map((item) => {
			if (typeof item === 'string') {
				const needle = lc(item);
				const found =
					options.find((o) => lc(o.value) === needle) ||
					options.find((o) => lc(o.label) === needle);
				if (found) {
					changed = true;
					return found;
				}
			}
			return item;
		});
		if (changed) selected = coerced;
	});

	// External form value -> selected
	$effect(() => {
		if (!isInternalUpdate && $value && optionsLoaded && $value !== initialValue) {
			const targets = Array.isArray($value) ? $value.map(lc) : [lc($value)];
			selected = targets.map((t) => options.find((o) => lc(o.value) === t) ?? t).filter(Boolean);
		}
	});

	async function handleSelectChange() {
		// Only create a new option if it truly doesn't exist (by value OR label)
		if (
			(effectiveAllowUserOptions === true || effectiveAllowUserOptions === 'append') &&
			selectedValues.length > 0
		) {
			for (const val of selectedValues) {
				const existsByVal = options.some((opt) => lc(opt.value) === lc(val));
				const existsByLab = options.some((opt) => lc(opt.label) === lc(val));
				if (!existsByVal && !existsByLab) {
					const newOption: Option = { label: String(val), value: String(val) };
					options = [...options, newOption];
				}
			}
		}

		await onChange($value); // direct callback (no nested $effect)
		dispatch('cache', selected);
	}

	function arraysEqual(
		arr1: string | (string | undefined)[] | null | undefined,
		arr2: string | (string | undefined)[] | null | undefined
	): boolean {
		const normalize = (val: string | (string | undefined)[] | null | undefined) => {
			if (typeof val === 'string') return [val];
			return val ?? [];
		};

		const a1 = normalize(arr1).map(norm);
		const a2 = normalize(arr2).map(norm);

		if (a1.length !== a2.length) return false;

		const set1 = new Set(a1);
		const set2 = new Set(a2);

		for (const value of set1) {
			if (!set2.has(value)) return false;
		}
		return true;
	}

	// Keep cachedValue in sync
	$effect(() => {
		cachedValue = selected.map((option) =>
			typeof option === 'string' ? option : (option.value as any)
		);
	});

	// Push selected -> form value (runs after pre-effects, so selected is already coerced)
	$effect(() => {
		if (!isInternalUpdate && optionsLoaded && !arraysEqual(selectedValues, $value)) {
			isInternalUpdate = true;
			$value = multiple ? selectedValues : (selectedValues[0] ?? default_value);
			handleSelectChange();
			isInternalUpdate = false;
		}
	});

	// Disabled state
	$effect(() => {
		disabled = Boolean(selected.length && options.length === 1 && $constraints?.required);
	});

	onDestroy(() => {
		if (updateMissingConstraint) {
			updateMissingConstraint(field, false);
		}
	});
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
		<input type="hidden" name={field} value={$value ? $value : ''} />

		<MultiSelect
			bind:selected
			{options}
			{...multiSelectOptions}
			{disabled}
			allowEmpty={true}
			allowUserOptions={effectiveAllowUserOptions}
		>
			<!-- Svelte 5 + svelte-multiselect v11 snippet API -->
			{#snippet children({ option })}
				{#if option.suggested}
					<span class="text-indigo-600">{option.label}</span>
					<span class="text-sm text-gray-500"> (suggested)</span>
				{:else if translateOptions && option.label}
					{#if field === 'ro_to_couple'}
						{safeTranslate(toCamelCase(String(option.label).split(' - ')[0]))} - {String(
							option.label
						).split('-')[1]}
					{:else}
						{m[toCamelCase(String(option.value))]
							? safeTranslate(String(option.value))
							: safeTranslate(String(option.label))}
					{/if}
				{:else}
					{String(option.label)}
				{/if}
			{/snippet}
		</MultiSelect>

		{#if isLoading}
			<svg
				class="animate-spin h-5 w-5 text-primary-500"
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
			>
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
				<path
					class="opacity-75"
					fill="currentColor"
					d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
				/>
			</svg>
		{/if}
	</div>

	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
