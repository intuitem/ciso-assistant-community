<script lang="ts">
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
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
	{#if options}
		{#each options as option}
			<div class="flex items-center mb-2 {classes} {classesDisabled(disabled)}">
				<input
					type="checkbox"
					name={field}
					id={option.value}
					value={option.value}
					checked={$value.includes(option.value)}
					bind:group={$value}
					{disabled}
					class="mr-2"
				/>
				<label for={option.value}>{option.label}</label>
			</div>
		{:else}
			<LoadingSpinner />
		{/each}
	{/if}
</div>
