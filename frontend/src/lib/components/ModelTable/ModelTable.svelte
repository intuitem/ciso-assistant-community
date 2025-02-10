<script lang="ts">
	import { onMount } from 'svelte';
	import ClientModelTable from './client/ModelTable.svelte';
	import ServerModelTable from './server/ModelTable.svelte';
	import type { TableSource } from './types';

	export let source: TableSource;

	const { next, previous } = source.meta ?? {};

	export let server = Boolean(next || previous);

	let modelTable: ConstructorOfATypedSvelteComponent;

	onMount(() => {
		const selectedComponent = server ? ServerModelTable : ClientModelTable;
		modelTable = selectedComponent;
	});

	$: _source = {
		...source,
		meta: source.meta?.results ?? source.meta
	};
</script>

<svelte:component this={modelTable} source={_source} {...$$restProps}>
	<slot />
	<slot name="addButton" slot="addButton" />
	<slot name="optButton" slot="optButton" />
	<slot name="actionsHead" slot="actionsHead" />
</svelte:component>
