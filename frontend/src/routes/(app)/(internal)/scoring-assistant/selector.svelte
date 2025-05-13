<script lang="ts">
	import { run } from 'svelte/legacy';

	import { createEventDispatcher } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		text: string;
		id: string;
		choices: (string | null)[];
		disabled?: boolean;
	}

	let {
		text,
		id,
		choices,
		disabled = false
	}: Props = $props();

	const dispatch = createEventDispatcher();

	let value = $state(0);
	run(() => {
		dispatch('change', value);
	});
</script>

<div>{safeTranslate(text)}</div>
<select class="select w-full" {id} bind:value {disabled}>
	{#each choices as text, i}
		<option class="text-{i}" value={i}
			>{i}{#if text}
				- {safeTranslate(text)}{/if}</option
		>
	{/each}
</select>
