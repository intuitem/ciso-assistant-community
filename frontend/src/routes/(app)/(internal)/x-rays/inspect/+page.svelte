<script lang="ts">
	import type { PageData } from './$types';
	import TreeChart from '$lib/components/Chart/TreeChart.svelte';
	import { goto, invalidateAll } from '$app/navigation';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let includeEnclaves = $state(data.includeEnclaves);

	$effect(() => {
		includeEnclaves = data.includeEnclaves;
	});

	async function toggleEnclaves() {
		await goto(`/x-rays/inspect?include_enclaves=${includeEnclaves}`);
		await invalidateAll();
	}
</script>

<div class="bg-white p-6 shadow-sm flex flex-col overflow-x-auto">
	<div class="flex items-center gap-4 mb-4">
		<label class="flex items-center gap-2 text-sm font-medium cursor-pointer">
			<input
				type="checkbox"
				class="checkbox"
				bind:checked={includeEnclaves}
				onchange={toggleEnclaves}
			/>
			{m.includeEnclaves()}
		</label>
		<div class="flex items-center gap-4 text-sm text-gray-600">
			<span class="flex items-center gap-1">
				<span class="inline-block w-3 h-3 rounded-sm" style="background-color: #B0C4DE;"></span>
				{m.domain()}
			</span>
			<span class="flex items-center gap-1">
				<span
					class="inline-block w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[10px]"
					style="border-bottom-color: #6366f1;"
				></span>
				{m.enclave()}
			</span>
			<span class="flex items-center gap-1">
				<span class="inline-block w-2.5 h-2.5 rounded-full" style="background-color: #222436;"
				></span>
				{m.perimeter()}
			</span>
		</div>
	</div>
	<div class="w-full h-dvh">
		{#key data.includeEnclaves}
			<TreeChart title="Organisation overview" tree={data.data} name="org_tree" />
		{/key}
	</div>
</div>
