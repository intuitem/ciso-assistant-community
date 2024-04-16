<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms/client';
	import { ProgressRadial } from '@skeletonlabs/skeleton';
	import { RangeSlider } from '@skeletonlabs/skeleton';
	import * as m from '$paraglide/messages';
	import type { AnyZodObject } from 'zod';

	export let label: string | undefined = undefined;
	export let field: string;

	export let form: SuperForm<AnyZodObject>;

	const { value, errors, constraints } = formFieldProxy(form, field);
	
	$: scoringEnabled = $value === null ? false : true

	console.log($value)

	function preventNull(value: number){
		if(value === null){
			return 0
		}
		return value
	
	}

	function displayNoValue(value: number){
		if(value === null){
			return '--'
		}
		return value
	}
</script>

<div>
	{#if label !== undefined}
		{#if $constraints?.required}
			<label class="text-sm font-semibold" for={field}
				>{label} <span class="text-red-500">*</span></label
			>
		{:else}
			<label class="text-sm font-semibold" for={field}>{label}</label>
		{/if}
	{/if}
	{#if $errors && $errors.length > 0}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	<div class="flex flex-row w-full items-center space-x-4 ml-2">
		<input
			name={field}
			type="checkbox"
			class="checkbox"
			data-testid="form-input-{field.replaceAll('_', '-')}"
			bind:checked={scoringEnabled}
			on:change={() => $value = null}
			{...$constraints}
			{...$$restProps}
			{...$constraints}
			{...$$restProps}
		/>
		<div class="flex w-1/2 items-center justify-center">
			<RangeSlider disabled={!scoringEnabled} class="w-full" name="range-slider" bind:value={$value} max={100} step={1} ticked></RangeSlider>
		</div>
		<div class="flex w-1/2 items-center justify-center">
			{#if scoringEnabled}
				<ProgressRadial stroke={175} value={preventNull($value)} width={'w-32'}>{displayNoValue($value)}</ProgressRadial>
			{:else}
				<ProgressRadial stroke={175} value={0} width={'w-32'}>--</ProgressRadial>
			{/if}
		</div>
	</div>
	<p class="text-sm text-gray-500">{m.scoringHelpText()}</p>
</div>
