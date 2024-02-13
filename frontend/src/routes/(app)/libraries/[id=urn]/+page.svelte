<script lang="ts">
	import { enhance } from '$app/forms';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { Library } from '$lib/utils/types.js';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import TreeViewItemContent from '../../frameworks/[id=uuid]/TreeViewItemContent.svelte';

	export let data;
	let loading = false;
	const library: Library = data.library;
	const showRisks = true;
	interface LibraryObjects {
		[key: string]: any;
	}

	const libraryObjects: LibraryObjects = library.objects ?? [];
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
				// lead: TreeViewItemLead,
				children: node.children ? transformToTreeView(Object.entries(node.children)) : []
			};
		});
	}
	let treeViewNodes: TreeViewNode[] = transformToTreeView(Object.entries(tree));

	import { tableSourceMapper, type TableSource, type TreeViewNode } from '@skeletonlabs/skeleton';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';

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
</script>

<div class="card bg-white p-4 shadow space-y-4">
	<div class="flex flex-row justify-between w-full">
		<div class="flex flex-col space-y-2">
			<h1 class="font-medium text-xl">{library.name}</h1>
			<div class="space-y-1">
				<p class="text-md leading-5 text-gray-700">Description: {library.description}</p>
				<p class="text-md leading-5 text-gray-700">Provider: {library.provider}</p>
				<p class="text-md leading-5 text-gray-700">Packager: {library.packager}</p>
				{#if library.dependencies}
					<p class="text-md leading-5 text-gray-700">
						Dependencies:
						{#each library.dependencies as dependency}
							<li>
								<a href="/libraries/{dependency}" target="_parent" class="anchor">{dependency}</a>
							</li>
						{/each}
					</p>
				{/if}
				{#if library.copyright}
					<p class="text-sm leading-5 text-gray-500">Copyright: {library.copyright}</p>
				{/if}
			</div>
		</div>
		{#if !library.id}
			<div class="flex">
				{#if loading}
					<div class="flex items-center mr-4 cursor-progress" role="status">
						<svg
							aria-hidden="true"
							class="w-5 h-5 text-gray-200 animate-spin dark:text-gray-600 fill-primary-500"
							viewBox="0 0 100 101"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
						>
							<path
								d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z"
								fill="currentColor"
							/>
							<path
								d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z"
								fill="currentFill"
							/>
						</svg>
					</div>
				{:else}
					<span class="text-gray-500 hover:text-primary-500">
						<form
							method="post"
							use:enhance={() => {
								loading = true;
								return async ({ update }) => {
									loading = false;
									update();
								};
							}}
						>
							<button type="submit" class="btn text-xl">
								<i class="fa-solid fa-file-import" />
							</button>
						</form>
					</span>
				{/if}
			</div>
		{/if}
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
