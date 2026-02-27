<script lang="ts">
	import GraphComponent from './OperatingModeGraph.svelte';
	import OperatingModeEditor from './OperatingModeEditor.svelte';
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let editMode = $state(false);

	const graphViewData = $derived({
		nodes: data.data.nodes,
		links: data.data.links
	});
	const panelNodes = $derived(data.data.panelNodes);
	const linkFlow = $derived(data.animated);

	function handleSaved() {
		editMode = false;
		invalidateAll();
	}
</script>

<div class="flex justify-between items-center mb-4">
	<a
		class="text-primary-800 hover:text-primary-500 cursor-pointer"
		href="/operating-modes/{data.data.mo_id ?? data.operatingModeId}/"
	>
		<i class="fa-solid fa-arrow-left mr-2"></i>{m.returnToMo()}
	</a>

	<div class="flex items-center gap-3">
		<!-- Edit/View toggle -->
		<button
			class="flex items-center gap-1.5 px-3 py-1.5 rounded-base text-sm font-medium transition-colors
				{editMode
				? 'bg-violet-100 text-violet-700 border border-violet-300'
				: 'bg-surface-100 text-surface-600 border border-surface-200 hover:bg-surface-200'}"
			onclick={() => (editMode = !editMode)}
		>
			{#if editMode}
				<i class="fa-solid fa-eye"></i>
				{m.viewMode()}
			{:else}
				<i class="fa-solid fa-pen"></i>
				{m.editMode()}
			{/if}
		</button>

		{#if !editMode}
			{#if data.animated}
				<a
					href="/operating-modes/{data.data.mo_id ?? data.operatingModeId}/graph"
					data-sveltekit-reload
					class="text-primary-800 hover:text-primary-500 cursor-pointer text-sm"
				>
					{m.graphStop()}
				</a>
			{:else}
				<a
					href="/operating-modes/{data.data.mo_id ?? data.operatingModeId}/graph?animated=true"
					data-sveltekit-reload
					class="text-primary-800 hover:text-primary-500 cursor-pointer text-sm"
				>
					{m.graphAnimate()}
				</a>
			{/if}
		{/if}
	</div>
</div>

{#if editMode}
	<OperatingModeEditor
		elementaryActions={data.elementaryActions}
		killChainSteps={data.killChainSteps}
		operatingModeId={data.operatingModeId}
		onSaved={handleSaved}
	/>
{:else}
	<div
		class="card rounded-xl w-full bg-linear-to-r from-surface-50 to-white shadow mb-4 p-2 text-xs text-surface-600 whitespace-pre-line mr-auto"
	>
		<i class="fa-solid fa-circle-info"></i>
		{m.graphMoHelp()}
	</div>
	<GraphComponent data={graphViewData} {panelNodes} {linkFlow} />
{/if}
