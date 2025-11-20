<script lang="ts">
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	interface Option {
		label: string;
		value: string;
	}

	interface Props {
		label?: string | undefined;
		field: string;
		valuePath?: any;
		options?: Option[];
		form: SuperForm<Record<string, any | undefined>>;
		hidden?: boolean;
		disabled?: boolean;
		classes?: string;
		classesContainer?: string;
		[key: string]: any;
	}

	let {
		label = $bindable(),
		field,
		valuePath = field,
		options = [],
		form,
		hidden = false,
		disabled = false,
		classes = '',
		classesContainer = ''
	}: Props = $props();

	label = label ?? field;

	let searchQuery = $state('');

	const { value, errors, constraints } = formFieldProxy(form, valuePath);

	const getModelName = (option: Option): string | null => {
		if (typeof option.value !== 'string' || !option.value.includes('.')) {
			console.warn('Skipping option with invalid value:', option);
			return null;
		}
		return option.value.split('.')[0];
	};

	const optionsByModel = (options: Option[]) => {
		return options.reduce((acc: Record<string, Option[]>, option) => {
			const modelName = getModelName(option);
			if (modelName) {
				(acc[modelName] = acc[modelName] || []).push(option);
			}
			return acc;
		}, {});
	};

	const modelNameLocaleMap = (options: Option[]) => {
		return Object.values(URL_MODEL_MAP).reduce((acc: Record<string, any>, model) => {
			if (!model?.name) return acc;
			if (acc?.[model.name]) return acc;

			acc[model.name] = {
				i18nName: model.localName,
				options: optionsByModel(options)[model.name] || []
			};
			return acc;
		}, {});
	};

	let allModelGroups = $derived(
		Object.values(modelNameLocaleMap(options)).filter(
			(e: Record<string, any>) => e?.options?.length
		)
	);

	let filteredModelGroups = $derived(
		allModelGroups.filter((model: any) => {
			if (!searchQuery) return true;
			// Translate the name first so we search against what the user sees
			const name = safeTranslate(model.i18nName).toLowerCase();
			return name.includes(searchQuery.toLowerCase());
		})
	);

	const isModelAllSelected = (modelOptions: Option[]) => {
		if (!$value || modelOptions.length === 0) return false;
		return modelOptions.every((opt) => $value.includes(opt.value));
	};

	const toggleModelSelection = (
		e: Event & { currentTarget: HTMLInputElement },
		modelOptions: Option[]
	) => {
		const isChecked = e.currentTarget.checked;
		const modelValues = modelOptions.map((o) => o.value);
		const currentValues = $value ?? [];

		if (isChecked) {
			$value = [...new Set([...currentValues, ...modelValues])];
		} else {
			$value = currentValues.filter((v) => !modelValues.includes(v));
		}
	};

	let classesDisabled = $derived((d: boolean) => (d ? 'opacity-50' : ''));
</script>

<div class={classesContainer} {hidden}>
	<div class={classesDisabled(disabled)}>
		{#if label !== undefined && !hidden}
			{#if $constraints?.required}
				<label class="text-sm font-semibold" for={field}
					>{label} <span class="text-red-500">*</span></label
				>
			{:else}
				<label class="text-sm font-semibold" for={field}>{label}</label>
			{/if}
		{/if}
		{#if $errors}
			<div>
				{#each $errors as error}
					<p class="text-error-500 text-xs font-medium">{safeTranslate(error)}</p>
				{/each}
			</div>
		{/if}
	</div>

	{#if options.length}
		<div class="mb-4 mt-2">
			<input
				type="text"
				bind:value={searchQuery}
				placeholder={m.searchResourcesPlaceholder()}
				class="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 {classesDisabled(
					disabled
				)}"
				{disabled}
			/>
		</div>

		{#each filteredModelGroups as model (model.i18nName)}
			{@const allSelected = isModelAllSelected(model.options)}

			<div class="flex items-center mt-4 mb-2">
				<input
					type="checkbox"
					class="mr-2 font-medium"
					id={`select-all-${model.i18nName}`}
					checked={allSelected}
					{disabled}
					onchange={(e) => toggleModelSelection(e, model.options)}
				/>
				<label for={`select-all-${model.i18nName}`} class="font-medium cursor-pointer select-none">
					{safeTranslate(model.i18nName)}
				</label>
			</div>

			<div class="ml-6 border-l pl-3">
				{#each model.options as option}
					{@const action = option.value.split('.')[1]}
					<div class="flex items-center mb-2 {classes} {classesDisabled(disabled)}">
						<input
							type="checkbox"
							name={field}
							id={option.value}
							value={option.value}
							checked={$value?.includes(option.value)}
							bind:group={$value}
							{disabled}
							class="mr-2"
						/>
						<label for={option.value}>{safeTranslate(action)}</label>
					</div>
				{/each}
			</div>
		{/each}

		{#if filteredModelGroups.length === 0 && searchQuery}
			<p class="text-sm text-gray-500 mt-2 italic">{m.noResourceMatchQuery()}</p>
		{/if}
	{:else}
		<LoadingSpinner />
	{/if}
</div>
