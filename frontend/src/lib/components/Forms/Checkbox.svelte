<script lang="ts">
	import { formFieldProxy } from 'sveltekit-superforms';

	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;
	// The cachedValue isn't used in the ModelForm because we don't need it yet
	export let cachedValue: boolean | undefined = undefined;
	export let form;
	export let hidden = false;
	export let disabled = false;

	label = label ?? field;

	const { value, errors, constraints } = formFieldProxy(form, field);

	$: if (cachedValue !== undefined) {
		value.set(cachedValue);
	} else {
		cachedValue = $value;
	}

	$: classesHidden = (h: boolean) => (h ? 'hidden' : '');
	$: classesDisabled = (d: boolean) => (d ? 'opacity-50' : '');
</script>

<div>
	<div
		class="flex flex-row space-x-2 items-center {classesHidden(hidden)} {classesDisabled(disabled)}"
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
			<input
				name={field}
				type="checkbox"
				class="checkbox"
				data-testid="form-input-{field.replaceAll('_', '-')}"
				bind:checked={cachedValue}
				{...$constraints}
				{...$$restProps}
				{disabled}
			/>
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
