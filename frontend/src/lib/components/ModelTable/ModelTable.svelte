<script lang="ts">
	import { onMount } from 'svelte';
	import ClientModelTable from './client/ModelTable.svelte';
	import ServerModelTable from './server/ModelTable.svelte';
	import type { TableSource } from './types';

	export let source: TableSource;

	const next = source.meta?.next;
	const previous = source.meta?.previous;

	export let server = Boolean(next || previous);

	let modelTable: ConstructorOfATypedSvelteComponent;

	onMount(async () => {
		modelTable = server ? ServerModelTable : ClientModelTable;
	});

	$: _source = { ...source, meta: source.meta?.results || source.meta };
</script>

<svelte:component this={modelTable} source={_source} {...$$restProps}>
	<slot />
	<slot name="addButton" slot="addButton" />
	<slot name="optButton" slot="optButton" />
	<slot name="actionsHead" slot="actionsHead" />
</svelte:component>
