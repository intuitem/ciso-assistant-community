<script lang="ts">
	import { tableSourceMapper } from '$lib/utils/table';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import TreeViewItemContent from './TreeViewItemContent.svelte';
	import TreeExpandCollapseToggle from '$lib/components/TreeView/TreeExpandCollapseToggle.svelte';

	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';

	let { data } = $props();
	let expandedNodes: string[] = $state([]);
	const flash = getFlash(page);

	// Workflow libraries (spec D31): loaded workflows are divorced rows, so the
	// library only carries a count (objects_meta) — instantiation reads the
	// stored content server-side and can be repeated at will.
	const workflowCount = $derived(data.library.objects_meta?.workflows ?? 0);
	let instantiating = $state(false);
	let instantiateFolder = $state('');
	let instantiateBusy = $state(false);

	// Standalone SPA form backing the hierarchical domain picker
	// (FolderTreeSelect requires a SuperForm); the picked id mirrors into
	// instantiateFolder via onChange. Field is target_folder (not "folder")
	// so the personal-space option never appears.
	const folderSchema = z.object({ target_folder: z.string() });
	const _folderForm = superForm(defaults({ target_folder: '' }, zod(folderSchema)), {
		dataType: 'json',
		taintedMessage: false,
		validators: zod(folderSchema),
		SPA: true
	});

	async function instantiateWorkflows() {
		if (!instantiateFolder) return;
		instantiateBusy = true;
		try {
			const res = await fetch(`/loaded-libraries/${data.library.id}/instantiate-workflows`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ folder: instantiateFolder })
			});
			const body = await res.json().catch(() => ({}));
			if (!res.ok) {
				flash.set({ type: 'error', message: String(body.error ?? res.statusText) });
				return;
			}
			const names = (body.workflows ?? []).map((w: any) => w.name).join(', ');
			flash.set({ type: 'success', message: m.workflowInstantiated({ names }) });
			instantiating = false;
		} finally {
			instantiateBusy = false;
		}
	}

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

<div class="card bg-surface-50-950 p-4 shadow-sm space-y-4">
	<div class="flex flex-col space-y-2">
		<span class="w-full flex flex-row justify-between">
			<h1 class="font-medium text-xl">{data.library.name}</h1>
		</span>
		<div class="space-y-1">
			<p class="text-md leading-5 text-surface-700-300">
				<strong>{m.description()}</strong>: {data.library.description}
			</p>
			<p class="text-md leading-5 text-surface-700-300">
				<strong>{m.provider()}</strong>: {data.library.provider}
			</p>
			<p class="text-md leading-5 text-surface-700-300">
				<strong>{m.packager()}</strong>: {data.library.packager}
			</p>
			<p class="text-md leading-5 text-surface-700-300">
				<strong>{m.version()}</strong>: {data.library.version}
			</p>
			{#if data.library.publication_date}
				<p class="text-md leading-5 text-surface-700-300">
					<strong>{m.publicationDate()}</strong>: {formatDateOrDateTime(
						data.library.publication_date,
						getLocale()
					)}
				</p>
			{/if}
			{#if data.library.dependencies}
				<p class="text-md leading-5 text-surface-700-300">
					<strong>{m.dependencies()}</strong>:
				</p>
				<ul class="list-disc list-inside">
					{#each data.library.dependencies as dependency}
						<li>{dependency.name}</li>
					{/each}
				</ul>
			{/if}
			{#if data.library.copyright}
				<p class="text-md leading-5 text-surface-700-300">
					<strong>{m.copyright()}</strong>: {data.library.copyright}
				</p>
			{/if}
		</div>
	</div>

	{#if workflowCount > 0}
		<div class="space-y-2">
			<div class="flex items-center gap-3">
				<span class="font-medium">
					<i class="fa-solid fa-diagram-project mr-2"></i>{workflowCount}
					{m.workflows()}
				</span>
				<button
					type="button"
					class="btn preset-filled-primary-500 text-sm"
					onclick={() => (instantiating = !instantiating)}
					data-testid="instantiate-workflows"
				>
					<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>{m.instantiateWorkflow()}
				</button>
			</div>
			{#if instantiating}
				<div class="flex items-end gap-2">
					<div class="w-64" data-testid="instantiate-folder">
						<FolderTreeSelect
							form={_folderForm}
							field="target_folder"
							label={m.domain()}
							writePermission="add_workflow"
							onChange={(value: any) => (instantiateFolder = value ?? '')}
						/>
					</div>
					<button
						type="button"
						class="btn preset-tonal text-sm"
						disabled={!instantiateFolder || instantiateBusy}
						onclick={instantiateWorkflows}
						data-testid="instantiate-confirm"
					>
						{#if instantiateBusy}
							<i class="fa-solid fa-circle-notch fa-spin mr-1"></i>
						{/if}
						{m.instantiateHere()}
					</button>
				</div>
			{/if}
		</div>
	{/if}

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
				<RiskMatrix {riskMatrix} showLegend={showRisks} wrapperClass="mt-8" />
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
		{#await data.tree}
			<span data-testid="loading-field">
				{m.loading()}...
			</span>
		{:then tree}
			{@const treeViewNodes = transformToTreeView(Object.entries(tree))}
			<div class="flex items-center justify-between">
				<h4 class="h4 font-medium">{m.framework()}</h4>
				<TreeExpandCollapseToggle nodes={treeViewNodes} bind:expandedNodes />
			</div>
			<RecursiveTreeView nodes={treeViewNodes} bind:expandedNodes hover="hover:bg-initial" />
		{/await}
	{/if}
</div>
