<script lang="ts">
	import { run } from 'svelte/legacy';

	import OTPItem from './OTPItem.svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		field?: string;
		form: SuperForm<Record<string, string>>;
		numOfInputs?: number;
		separator?: string;
		inputClass?: string;
		wrapperClass?: string;
		separatorClass?: string;
		inputStyle?: string;
		wrapperStyle?: string;
		separatorStyle?: string;
		numberOnly?: boolean;
		placeholder?: string;
		onlyShowMiddleSeparator?: boolean;
		clearOnError?: boolean;
	}

	let {
		field = 'code',
		form,
		numOfInputs = 6,
		separator = '',
		inputClass = '',
		wrapperClass = '',
		separatorClass = '',
		inputStyle = '',
		wrapperStyle = '',
		separatorStyle = '',
		numberOnly = true,
		placeholder = '',
		onlyShowMiddleSeparator = false,
		clearOnError = true
	}: Props = $props();

	const { value, errors } = formFieldProxy(form, field);

	let codes: string[] = $state([
		...$value.slice(0, numOfInputs).split(''),
		...Array(numOfInputs <= $value.length ? 0 : numOfInputs - $value.length).fill('')
	]);
	let inputs: (null | HTMLInputElement)[] = $state(Array(numOfInputs).fill(null));

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

	$effect(() => {
		codes = [
			...$value.slice(0, numOfInputs).split(''),
			...Array(numOfInputs <= $value.length ? 0 : numOfInputs - $value.length).fill('')
		];
	});

	run(() => {
		if ($errors && clearOnError) {
			console.log('clearing');
			reset();
		}
	});

	let placeholders = $derived(
		placeholder.length < numOfInputs
			? [...placeholder.split(''), ...Array(numOfInputs - placeholder.length).fill('')]
			: placeholder.split('')
	);

	run(() => {
		$value = codes.join('');
	});

	$effect(() => {
		if (!inputs[0]) return;
		const id = setTimeout(() => {
			if (document.activeElement !== inputs[0]) {
				inputs[0]?.focus();
			}
		}, 200);
		return () => clearTimeout(id);
	});

	let autoSubmitInFlight = false;
	$effect(() => {
		const complete = codes.length === numOfInputs && codes.every((code) => code !== '');
		if (!complete || autoSubmitInFlight) return;

		const id = setTimeout(() => {
			autoSubmitInFlight = true;
			form.submit().finally(() => {
				autoSubmitInFlight = false;
			});
		}, 100);

		return () => clearTimeout(id);
	});
</script>

{#if $errors}
	<div>
		{#each $errors as error}
			<p class="text-error-500 text-xs font-medium">{safeTranslate(error)}</p>
		{/each}
	</div>
{/if}
<div class={`wrapper ${wrapperClass}`} style={wrapperStyle} onkeyup={keyUpHandler}>
	{#each codes as value, i (i)}
		<OTPItem
			num={numberOnly}
			bind:input={inputs[i]}
			bind:value={codes[i]}
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
