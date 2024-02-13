<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import TreeViewItemContent from '../../frameworks/[id=uuid]/TreeViewItemContent.svelte';

	export let data;
	let loading = false;
	const showRisks = true;
	interface LibraryObjects {
		[key: string]: any;
	}

	const libraryObjects: LibraryObjects = data.library.objects ?? [];
	const riskMatrices = libraryObjects['risk_matrix'] ?? [];
	const securityFunctions = libraryObjects['security_functions'] ?? [];
	const threats = libraryObjects['threats'] ?? [];
	const framework = libraryObjects['framework'];

	const tree = data.tree;

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
	let treeViewNodes: TreeViewNode[] = transformToTreeView(Object.entries(tree));

	import { ProgressRadial, tableSourceMapper, type TreeViewNode } from '@skeletonlabs/skeleton';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { enhance } from '$app/forms';

	const riskMatricesTable: TableSource = {
		head: ['Name', 'Description'],
		body: tableSourceMapper(riskMatrices, ['name', 'description'])
	};

	const securityFunctionsTable: TableSource = {
		head: { ref_id: 'Ref', name: 'Name', description: 'Description', category: 'Category' },
		body: tableSourceMapper(securityFunctions, ['ref_id', 'name', 'description', 'category'])
	};

	const threatsTable: TableSource = {
		head: { ref_id: 'Ref', name: 'Name', description: 'Description' },
		body: tableSourceMapper(threats, ['ref_id', 'name', 'description'])
	};

	function riskMatricesPreview(riskMatrices: []) {
		let riskMatricesDumps = [];
		let riskMatrixDump = {
			json_definition: ''
		};
		for (const riskMatrix of riskMatrices) {
			riskMatrixDump['json_definition'] = JSON.stringify(riskMatrix);
			riskMatricesDumps.push(riskMatrixDump);
		}
		return riskMatricesDumps;
	}

	$: displayImportButton = data.library.id === undefined;
</script>

<div class="card bg-white p-4 shadow space-y-4">
	<div class="flex flex-col space-y-2">
		<span class="w-full flex flex-row justify-between">
			<h1 class="font-medium text-xl">{data.library.name}</h1>
			<div>
				{#if displayImportButton}
					{#if loading}
						<ProgressRadial width="w-6" meter="stroke-primary-500" />
					{:else}
						<form
							method="post"
							use:enhance={() => {
								loading = true;
								return async ({ update }) => {
									update();
								};
							}}
						>
							<button type="submit" class="p-1 btn text-xl hover:text-primary-500">
								<i class="fa-solid fa-file-import" />
							</button>
						</form>
					{/if}
				{/if}
			</div>
		</span>
		<div class="space-y-1">
			<p class="text-md leading-5 text-gray-700">Description: {data.library.description}</p>
			<p class="text-md leading-5 text-gray-700">Provider: {data.library.provider}</p>
			<p class="text-md leading-5 text-gray-700">Packager: {data.library.packager}</p>
			{#if data.library.dependencies}
				<p class="text-md leading-5 text-gray-700">
					Dependendies:
					{#each data.library.dependencies as dependency}
						<li>
							<a href="/libraries/{dependency}" target="_parent" class="anchor">{dependency}</a>
						</li>
					{/each}
				</p>
			{/if}
			{#if data.library.copyright}
				<p class="text-sm leading-5 text-gray-500">Copyright: {data.library.copyright}</p>
			{/if}
		</div>
	</div>

	{#if riskMatrices.length > 0}
		<Dropdown
			open={riskMatrices.length == 1}
			style="hover:text-indigo-700"
			icon="fa-solid fa-table-cells-large"
			header="{riskMatrices.length} Risk matrix"
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

	{#if securityFunctions.length > 0}
		<Dropdown
			style="hover:text-indigo-700"
			icon="fa-solid fa-gears"
			header="{securityFunctions.length} Security functions"
		>
			<ModelTable source={securityFunctionsTable} displayActions={false} interactive={false} />
		</Dropdown>
	{/if}

	{#if threats.length > 0}
		<Dropdown
			style="hover:text-indigo-700"
			icon="fa-solid fa-biohazard"
			header="{threats.length} Threats"
		>
			<ModelTable source={threatsTable} displayActions={false} interactive={false} />
		</Dropdown>
	{/if}

	{#if framework}
		<h4 class="h4 font-medium">Framework</h4>
		<RecursiveTreeView nodes={treeViewNodes} hover="hover:bg-initial" />
	{/if}
</div>
