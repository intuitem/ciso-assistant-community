<script lang="ts">
	import { breadcrumbObject } from '$lib/utils/stores';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import TreeViewItemContent from '../../frameworks/[id=uuid]/TreeViewItemContent.svelte';
	import * as m from '$paraglide/messages';

	export let data;
	let loading = { form: false, library: '' };
	const showRisks = true;
	interface LibraryObjects {
		[key: string]: any;
	}

	const breadcrumb_library_data = {
		...data.library,
		id: data.library.id
	};
	$: breadcrumbObject.set(breadcrumb_library_data);

	const libraryObjects: LibraryObjects = data.library.objects ?? [];
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

	import { ProgressRadial, tableSourceMapper, type TreeViewNode } from '@skeletonlabs/skeleton';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { enhance } from '$app/forms';

	const riskMatricesTable: TableSource = {
		head: { name: 'name', description: 'description' },
		body: tableSourceMapper(riskMatrices, ['name', 'description'])
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
		])
	};

	const threatsTable: TableSource = {
		head: { ref_id: 'ref', name: 'name', description: 'description' },
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

	$: displayImportButton = !(data.library.is_loaded ?? true);

	async function handleSubmit(event: { currentTarget: EventTarget & HTMLFormElement }) {
		const data = new FormData(event.currentTarget);

		const response = await fetch(event.currentTarget.action, {
			method: 'POST',
			body: data
		});

		const result: ActionResult = deserialize(await response.text());

		if (result.type === 'success') {
			await invalidateAll();
		}
		applyAction(result);
	}
</script>

<div class="card bg-white p-4 shadow space-y-4">
	<div class="flex flex-col space-y-2">
		<span class="w-full flex flex-row justify-between">
			<h1 class="font-medium text-xl">{data.library.name}</h1>
			<div>
				{#if displayImportButton}
					{#if loading.form}
						<ProgressRadial width="w-6" meter="stroke-primary-500" />
					{:else}
						<form
							method="post"
							action="/libraries/{data.library.id}?/load"
							use:enhance={() => {
								loading.form = true;
								loading.library = data.library.id;
								return async ({ update }) => {
									loading.form = false;
									loading.library = '';
									update();
								};
							}}
							on:submit={handleSubmit}
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
			<p class="text-md leading-5 text-gray-700">{m.description()}: {data.library.description}</p>
			<p class="text-md leading-5 text-gray-700">{m.provider()}: {data.library.provider}</p>
			<p class="text-md leading-5 text-gray-700">{m.packager()}: {data.library.packager}</p>
			{#if data.library.dependencies}
				<p class="text-md leading-5 text-gray-700">
					{m.dependencies()}:
					{#each data.library.dependencies as dependency}
						<li>{dependency.name}</li>
					{/each}
				</p>
			{/if}
			{#if data.library.copyright}
				<p class="text-md leading-5 text-gray-700">{m.copyright()}: {data.library.copyright}</p>
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
			<ModelTable source={referenceControlsTable} displayActions={false} interactive={false} />
		</Dropdown>
	{/if}

	{#if threats.length > 0}
		<Dropdown
			style="hover:text-indigo-700"
			icon="fa-solid fa-biohazard"
			header="{threats.length} {m.threats()}"
		>
			<ModelTable source={threatsTable} displayActions={false} interactive={false} />
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
