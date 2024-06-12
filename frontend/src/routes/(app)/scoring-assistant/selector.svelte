<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { localItems } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	export let text: string;
	export let id: string;
	export let choices: (string | null)[];
	export let disabled = false;

	const dispatch = createEventDispatcher();

	let value = 0;
	$: dispatch('change', value);
</script>

<div>{m[text]()}</div>
<select class="select w-full" {id} bind:value {disabled}>
	{#each choices as text, i}
		<option class="text-{i}" value={i}
			>{i}{#if text} - {m[text]()}{/if}</option
		>
	{/each}
</select>
