<script lang="ts">
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	interface Option {
		label: string;
		value: string;
	}

	interface Props {
		label?: string | undefined;
		field: string;
		valuePath?: any; // the place where the value is stored in the form. This is useful for nested objects
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
			if (!model?.name) {
				console.warn('Skipping model with no name:', model);
				return acc;
			}

			if (acc?.[model.name]) {
				// skip duplicates (e.g. policies)
				return acc;
			}

			acc[model.name] = {
				i18nName: model.localName,
				options: optionsByModel(options)[model.name] || []
			};

			return acc;
		}, {});
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
		{#each Object.values(modelNameLocaleMap(options)).filter((e: Record<string, any>) => e?.options?.length) as model}
			<p class="font-medium">{safeTranslate(model.i18nName)}</p>
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
		{/each}
	{:else}
		<LoadingSpinner />
	{/if}
</div>
