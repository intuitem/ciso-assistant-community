<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock } from '$lib/utils/types';
	import { beforeUpdate, onMount } from 'svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import { createEventDispatcher } from 'svelte';
	import MultiSelect from 'svelte-multiselect';
	import { getContext, onDestroy } from 'svelte';
	import * as m from '$paraglide/messages.js'
	import { toCamelCase } from '$lib/utils/locales';

	interface Option {
		label: string;
		value: string;
		suggested?: boolean;
	}

	type FieldContext = 'form-input' | 'filter-input';

	export let fieldContext: FieldContext = 'form-input';

	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;

	export let form: SuperForm<Record<string, unknown>, any>;
	export let resetForm = false;
	export let multiple = false;
	export let nullable = false;
	export let mandatory = false;

	export let hidden = false;
	export let translateOptions = true;

	export let options: Option[] = [];
	/**
	 * optionsEndpoint to fetch options from
	 * @example 'users' -> fetches from /users/
	 */
	export let optionsEndpoint: string = '';

	/**
	 * Additional endpoint URL parameters with details (ID, urn, ...)
	 * @format Array of [parameter, identifier] tuples
	 * @example [['ebios_rm_studies', 'uuid']] -> <endpointUrl>?...&ebios_rm_studies=uuid"
	 */
	export let optionsDetailedUrlParameters: [string, string][] = [];

	/**
	 * Field path to use for option labels (supports dot notation for nested fields)
	 * @default 'name'
	 * @example 'email' -> object.email
	 * @example 'profile.full_name' -> object.profile.full_name
	 * @special 'auto' -> combines ref_id with name/description
	 */
	export let optionsLabelField: string = 'name';

	/**
	 * Field path to use for option values (supports dot notation for nested fields)
	 * @default 'id'
	 * @example 'uuid' -> object.uuid
	 * @example 'meta.identifier' -> object.meta.identifier
	 */
	export let optionsValueField: string = 'id';

	export let browserCache: RequestCache = 'default';

	/**
	 * Additional fields to display in labels as prefixes
	 * @format Array of [fieldPath, type] tuples
	 * @example [['folder.str', 'string']] -> displays "folder_value/name"
	 * @example [['department', 'string'], ['team', 'string']] -> "department_value/team_value/name"
	 */
	export let optionsExtraFields: [string, string][] = [];

	/**
	 * Suggested options to highlight (matches by optionsValueField)
	 * @example [{id: 1, name: 'Suggested'}]
	 */
	export let optionsSuggestions: any[] = [];

	/**
	 * Current user/object to exclude from options (unless optionsSelfSelect=true)
	 * @example Current user object to prevent self-selection
	 */
	export let optionsSelf: any = null;

	/**
	 * Whether to include the self object in selectable options
	 * @default false
	 * @example true -> allows selecting your own user account
	 */
	export let optionsSelfSelect: boolean = false;
	export let allowUserOptions: boolean | 'append' = false;

	export let cacheLock: CacheLock = {
		promise: new Promise((res) => res(null)),
		resolve: (x) => x
	};
	export let cachedValue: any[] | undefined = undefined;

	const { value, errors, constraints } = formFieldProxy(form, field);

	let selected: (typeof options)[] = [];
	let selectedValues: (string | undefined)[] = [];
	let isInternalUpdate = false;
	let optionsLoaded = Boolean(options.length);
	const initialValue = resetForm ? undefined : $value; // Store initial value
	const default_value = nullable ? null : selectedValues[0];

	const multiSelectOptions = {
		minSelect: $constraints && $constraints.required === true ? 1 : 0,
		maxSelect: multiple ? undefined : 1,
		liSelectedClass: multiple ? '!chip !variant-filled' : '!bg-transparent',
		inputClass: 'focus:!ring-0 focus:!outline-none',
		outerDivClass: '!select',
		closeDropdownOnSelect: !multiple
	};

	const dispatch = createEventDispatcher();
	let isLoading = false;
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
					options = processOptions(data);
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
		const append = (x, y) => (!y ? x : !x || x == '' ? y : x + ' - ' + y);

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

				return {
					label: fullLabel,
					value: getNestedValue(object, optionsValueField),
					suggested: optionsSuggestions?.some(
						(s) =>
							getNestedValue(s, optionsValueField) === getNestedValue(object, optionsValueField)
					)
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
				return 0;
			});
	}

	function getNestedValue(obj: any, path: string, field = '') {
		if (field) return obj[path]?.[field];
		return path.split('.').reduce((o, p) => (o || {})[p], obj);
	}

	onMount(async () => {
		await fetchOptions();
		dispatch('mount', $value);
		const cacheResult = await cacheLock.promise;
		if (cacheResult && cacheResult.length > 0) {
			selected = cacheResult.map((value) => optionHashmap[value]).filter(Boolean);
		}
	});

	beforeUpdate(() => {
		if (!isInternalUpdate && $value && optionsLoaded && $value !== initialValue) {
			selected = options.filter((item) =>
				Array.isArray($value) ? $value.includes(item.value) : item.value === $value
			);
		}
	});

	function handleSelectChange() {
		if (allowUserOptions && selectedValues.length > 0) {
			for (const val of selectedValues) {
				if (!options.some((opt) => opt.value === val)) {
					const newOption: Option = { label: val, value: val };
					options = [...options, newOption];
				}
			}
		}

		dispatch('change', $value);
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

	$: optionHashmap = options.reduce((acc, option) => {
		acc[option.value] = option;
		return acc;
	}, {});

	$: cachedValue = selected.map((option) => option.value);

	$: selectedValues = selected.map((item) => item.value || item.label || item);

	$: {
		// Only update value after options are loaded
		if (!isInternalUpdate && optionsLoaded && !arraysEqual(selectedValues, $value)) {
			isInternalUpdate = true;
			$value = multiple ? selectedValues : (selectedValues[0] ?? default_value);
			handleSelectChange();
			isInternalUpdate = false;
		}
	}

	$: disabled = selected.length && options.length === 1 && $constraints?.required;

	onDestroy(() => {
		if (updateMissingConstraint) {
			updateMissingConstraint(field, false);
		}
	});
</script>

<div {hidden}>
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
			disabled={disabled || $$restProps.disabled}
			allowEmpty={true}
			{...$$restProps}
			let:option
			{allowUserOptions}
		>
			{#if option.suggested}
				<span class="text-indigo-600">{option.label}</span>
				<span class="text-sm text-gray-500"> (suggested)</span>
			{:else if translateOptions && option.label}
				{m[toCamelCase(option.value)] ? safeTranslate(option.value) : safeTranslate(option.label)}
			{:else}
				{option.label || option}
			{/if}
		</MultiSelect>
		{#if isLoading}
			<svg
				class="animate-spin h-5 w-5 text-primary-500"
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
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
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
