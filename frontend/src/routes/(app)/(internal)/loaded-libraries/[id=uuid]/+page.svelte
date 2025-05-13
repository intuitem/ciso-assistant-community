<script lang="ts">
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import { tableSourceMapper } from '@skeletonlabs/skeleton';
	import TreeViewItemContent from '../../frameworks/[id=uuid]/TreeViewItemContent.svelte';

	let { data } = $props();

	const showRisks = true;

	interface LibraryObjects {
		[key: string]: any;
	}

	const libraryObjects: LibraryObjects = data?.library?.objects ?? [];
	const riskMatrices = libraryObjects['risk_matrix'] ?? [];
	const referenceControls = libraryObjects['reference_controls'] ?? [];
	const threats = libraryObjects['threats'] ?? [];
	const framework = libraryObjects['framework'];

	function transformToTreeView(nodes) {
		return nodes.map(([id, node]) => {
			return {
				id: id,
				content: TreeViewItemContent,
				contentProps: node,
				children: node.children ? transformToTreeView(Object.entries(node.children)) : []
			};
		});
	}

	const riskMatricesTable: TableSource = {
		head: { name: 'name', description: 'description' },
		body: tableSourceMapper(riskMatrices, ['name', 'description']),
		meta: { count: riskMatrices.length }
	};

	const referenceControlsTable: TableSource = {
		head: {
			ref_id: 'ref',
			name: 'name',
			description: 'description',
			category: 'category',
			csf_function: 'csfFunction'
		},
		body: tableSourceMapper(referenceControls, [
			'ref_id',
			'name',
			'description',
			'category',
			'csf_function'
		]),
		meta: { count: referenceControls.length }
	};

	const threatsTable: TableSource = {
		head: { ref_id: 'ref', name: 'name', description: 'description' },
		body: tableSourceMapper(threats, ['ref_id', 'name', 'description']),
		meta: { count: threats.length }
	};

	function riskMatricesPreview(riskMatrices: []) {
		let riskMatricesDumps = [];
		for (const riskMatrix of riskMatrices) {
			const riskMatrixDump = {
				json_definition: JSON.stringify(riskMatrix)
			};
			riskMatricesDumps.push(riskMatrixDump);
		}
		return riskMatricesDumps;
	}
</script>

<div class="card bg-white p-4 shadow space-y-4">
	<div class="flex flex-col space-y-2">
		<span class="w-full flex flex-row justify-between">
			<h1 class="font-medium text-xl">{data.library.name}</h1>
		</span>
		<div class="space-y-1">
			<p class="text-md leading-5 text-gray-700">
				<strong>{m.description()}</strong>: {data.library.description}
			</p>
			<p class="text-md leading-5 text-gray-700">
				<strong>{m.provider()}</strong>: {data.library.provider}
			</p>
			<p class="text-md leading-5 text-gray-700">
				<strong>{m.packager()}</strong>: {data.library.packager}
			</p>
			<p class="text-md leading-5 text-gray-700">
				<strong>{m.version()}</strong>: {data.library.version}
			</p>
			{#if data.library.publication_date}
				<p class="text-md leading-5 text-gray-700">
					<strong>{m.publicationDate()}</strong>: {formatDateOrDateTime(
						data.library.publication_date,
						getLocale()
					)}
				</p>
			{/if}
			{#if data.library.dependencies}
				<p class="text-md leading-5 text-gray-700">
					<strong>{m.dependencies()}</strong>:
				</p>
				<ul class="list-disc list-inside">
					{#each data.library.dependencies as dependency}
						<li>{dependency.name}</li>
					{/each}
				</ul>
			{/if}
			{#if data.library.copyright}
				<p class="text-md leading-5 text-gray-700">
					<strong>{m.copyright()}</strong>: {data.library.copyright}
				</p>
			{/if}
		</div>
	</div>

	{#if riskMatrices.length > 0}
		<Dropdown
			open={riskMatrices.length == 1}
			style="hover:text-indigo-700"
			icon="fa-solid fa-table-cells-large"
			header="{riskMatrices.length} {m.riskMatrices()}"
		>
			<ModelTable
				source={riskMatricesTable}
				displayActions={false}
				pagination={false}
				rowCount={false}
				rowsPerPage={false}
				search={false}
				interactive={false}
			/>
			{#each riskMatricesPreview(riskMatrices) as riskMatrix}
				<RiskMatrix {riskMatrix} {showRisks} wrapperClass="mt-8" />
			{/each}
		</Dropdown>
	{/if}

	{#if referenceControls.length > 0}
		<Dropdown
			style="hover:text-indigo-700"
			icon="fa-solid fa-gears"
			header="{referenceControls.length} {m.referenceControls()}"
		>
			<ModelTable
				source={referenceControlsTable}
				displayActions={false}
				pagination={false}
				rowCount={false}
				rowsPerPage={false}
				search={false}
				interactive={false}
			/>
		</Dropdown>
	{/if}

	{#if threats.length > 0}
		<Dropdown
			style="hover:text-indigo-700"
			icon="fa-solid fa-biohazard"
			header="{threats.length} {m.threats()}"
		>
			<ModelTable
				source={threatsTable}
				displayActions={false}
				pagination={false}
				rowCount={false}
				rowsPerPage={false}
				search={false}
				interactive={false}
			/>
		</Dropdown>
	{/if}

	{#if framework}
		<h4 class="h4 font-medium">{m.framework()}</h4>
		{#await data.tree}
			<span data-testid="loading-field">
				{m.loading()}...
			</span>
		{:then tree}
			<RecursiveTreeView
				nodes={transformToTreeView(Object.entries(tree))}
				hover="hover:bg-initial"
			/>
		{/await}
	{/if}
</div>
