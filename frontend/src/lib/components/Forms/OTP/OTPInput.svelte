<!-- @migration-task Error while migrating Svelte code: Can't migrate code with afterUpdate. Please migrate by hand. -->
<script lang="ts">
	import { afterUpdate } from 'svelte';
	import OTPItem from './OTPItem.svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import { safeTranslate } from '$lib/utils/i18n';

	export let field = 'code';
	export let form: SuperForm<Record<string, string>>;
	export let numOfInputs: number = 6;
	export let separator = '';
	export let inputClass = '';
	export let wrapperClass = '';
	export let separatorClass = '';
	export let inputStyle = '';
	export let wrapperStyle = '';
	export let separatorStyle = '';
	export let numberOnly = true;
	export let placeholder = '';
	export let onlyShowMiddleSeparator = false;
	export let clearOnError = true;

	const { value, errors } = formFieldProxy(form, field);

	let codes: string[] = [
		...$value.slice(0, numOfInputs).split(''),
		...Array(numOfInputs <= $value.length ? 0 : numOfInputs - $value.length).fill('')
	];
	let inputs: (null | HTMLInputElement)[] = Array(numOfInputs).fill(null);

	function reset() {
		$value = '';
		codes = Array(numOfInputs).fill('');

		inputs[0]?.focus();
	}

	function keyUpHandler(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			form.submit();
		}
	}

	$: if ($errors && clearOnError) {
		console.log('clearing');
		reset();
	}

	afterUpdate(() => {
		codes = [
			...$value.slice(0, numOfInputs).split(''),
			...Array(numOfInputs <= $value.length ? 0 : numOfInputs - $value.length).fill('')
		];
	});

	$: placeholders =
		placeholder.length < numOfInputs
			? [...placeholder.split(''), ...Array(numOfInputs - placeholder.length).fill('')]
			: placeholder.split('');

	$: $value = codes.join('');
</script>

{#if $errors}
	<div>
		{#each $errors as error}
			<p class="text-error-500 text-xs font-medium">{safeTranslate(error)}</p>
		{/each}
	</div>
{/if}
<div class={`wrapper ${wrapperClass}`} style={wrapperStyle} on:keyup={keyUpHandler}>
	{#each codes as value, i (i)}
		<OTPItem
			num={numberOnly}
			bind:input={inputs[i]}
			bind:value
			index={i}
			bind:codes
			{inputs}
			className={inputClass}
			style={inputStyle}
			placeholder={placeholders[i]}
		/>
		{#if separator && i !== codes.length - 1 && (!onlyShowMiddleSeparator || (onlyShowMiddleSeparator && i === codes.length / 2 - 1 && numOfInputs % 2 === 0))}
			<span class={separatorClass} style={separatorStyle}>{separator}</span>
		{/if}
	{/each}
</div>

<style>
	.wrapper {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}
</style>
