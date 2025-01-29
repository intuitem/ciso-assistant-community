<script lang="ts">
	import { onMount } from 'svelte';
	import type { TableSource } from './types';

	export let source: TableSource;

	const next = source.meta.next;
	const previous = source.meta.previous;

	export let server = Boolean(next || previous);

	let modelTable: ConstructorOfATypedSvelteComponent;

	onMount(async () => {
		const modulePath = server ? './server/ModelTable.svelte' : './client/ModelTable.svelte';
		await import(modulePath).then((module) => {
			modelTable = module.default;
		});
	});

	$: _source = { ...source, meta: source.meta.results || source.meta };
</script>

<svelte:component this={modelTable} source={_source} {...$$restProps}>
	<slot />
	<slot name="addButton" slot="addButton" />
	<slot name="optButton" slot="optButton" />
</svelte:component>
