<script lang="ts">
	import { Switch } from '@skeletonlabs/skeleton-svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	interface Props {
		label?: string | undefined;
		field: string;
		valuePath?: any; // the place where the value is stored in the form. This is useful for nested objects
		helpText?: string | undefined;
		// The cachedValue isn't used in the ModelForm because we don't need it yet
		cachedValue?: boolean | undefined;
		form: SuperForm<Record<string, boolean | undefined>>;
		hidden?: boolean;
		disabled?: boolean;
		checkboxComponent?: 'checkbox' | 'switch';
		classes?: string;
		classesContainer?: string;
		onChange?: (event: boolean) => void;
		[key: string]: any;
	}

	let {
		label = $bindable(),
		field,
		valuePath = field,
		helpText = undefined,
		cachedValue = $bindable(),
		form,
		hidden = false,
		disabled = false,
		checkboxComponent = 'checkbox',
		classes = '',
		classesContainer = '',
		onChange = () => {},
		...rest
	}: Props = $props();

	label = label ?? field;

	const { value, errors, constraints } = formFieldProxy(form, valuePath);
	$effect(() => {
		cachedValue = $value;
	});

	let classesHidden = $derived((h: boolean) => (h ? 'hidden' : ''));
	let classesDisabled = $derived((d: boolean) => (d ? 'opacity-50' : ''));
</script>

<div class="{classesContainer} {classesHidden(hidden)}">
	<div
		class="flex flex-row space-x-2 items-center {classesDisabled(disabled)}"
		aria-disabled={disabled}
	>
		{#if label !== undefined}
			{#if $constraints?.required}
				<label class="text-sm font-semibold" for={field}
					>{label} <span class="text-red-500">*</span></label
				>
			{:else}
				<label class="text-sm font-semibold" for={field}>{label}</label>
			{/if}
		{/if}
		<div class="control">
			{#if checkboxComponent === 'checkbox'}
				<input
					name={field}
					type="checkbox"
					class="checkbox"
					data-testid="form-input-{field.replaceAll('_', '-')}"
					bind:checked={$value}
					onchange={() => onChange($value)}
					{...$constraints}
					{...rest}
					{disabled}
				/>
			{:else if checkboxComponent === 'switch'}
				<Switch
					name={field}
					{classes}
					data-testid="form-input-{field.replaceAll('_', '-')}"
					checked={Boolean($value)}
					onCheckedChange={(e) => {
						$value = e.checked;
						onChange($value);
					}}
					{...$constraints}
					{...rest}
					{disabled}
				/>
			{/if}
		</div>
	</div>
	{#if $errors}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
