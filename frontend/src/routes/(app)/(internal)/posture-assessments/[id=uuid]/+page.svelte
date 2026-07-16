<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import PostureTrendChart from '$lib/components/Chart/PostureTrendChart.svelte';
	import PostureHeatmapChart from '$lib/components/Chart/PostureHeatmapChart.svelte';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import { deserialize, enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { copy } from '@svelte-put/copy';
	import { page } from '$app/state';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';
	import { postureResultTailwindColorMap } from '$lib/utils/constants';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const resultLabels: Record<string, string> = {
		pass: m.pass(),
		fail: m.fail(),
		not_applicable: m.notApplicable(),
		error: m.error(),
		not_checked: m.notChecked()
	};

	const assetLabel = (a: any) => (a?.folder?.str ? `${a.folder.str}/${a.str}` : (a?.str ?? ''));

	let activeTab = $state('overview');

	const results = $derived(data.posture?.results ?? []);
	const totalChecks = $derived(data.posture?.total_checks ?? 0);

	// overview filters
	let filterAsset = $state('');
	let filterStatuses = $state<string[]>([]);

	function toggleStatus(status: string) {
		filterStatuses = filterStatuses.includes(status)
			? filterStatuses.filter((s) => s !== status)
			: [...filterStatuses, status];
	}

	const filterActive = $derived(filterAsset !== '' || filterStatuses.length > 0);

	const filteredResults = $derived(
		results.filter(
			(row: any) =>
				(!filterAsset || row.asset.id === filterAsset) &&
				(filterStatuses.length === 0 || filterStatuses.includes(row.result))
		)
	);

	$effect(() => {
		if (filterAsset && !(data.data?.assets ?? []).some((a: any) => a.id === filterAsset)) {
			filterAsset = '';
		}
	});

	const assets = $derived.by(() => {
		const columns = (data.data?.assets ?? []).map((a: any) => ({ id: a.id, name: assetLabel(a) }));
		const known = new Set(columns.map((a: any) => a.id));
		for (const row of results) {
			if (!known.has(row.asset.id)) {
				columns.push({ id: row.asset.id, name: row.asset.str });
				known.add(row.asset.id);
			}
		}
		return columns;
	});

	const checks = $derived.by(() => {
		const seen = new Map();
		for (const row of filteredResults) seen.set(row.requirement.id, row.requirement);
		return [...seen.values()].sort((a, b) =>
			(a.ref_id ?? '').localeCompare(b.ref_id ?? '', undefined, { numeric: true })
		);
	});

	const counts = $derived.by(() => {
		const acc: Record<string, number> = {};
		for (const row of filteredResults) acc[row.result] = (acc[row.result] ?? 0) + 1;
		return acc;
	});

	const displayedScore = $derived.by(() => {
		if (!filterActive) return data.posture?.score != null ? `${data.posture.score}%` : '--';
		const applicable = (counts['pass'] ?? 0) + (counts['fail'] ?? 0);
		return applicable ? `${Math.round((100 * (counts['pass'] ?? 0)) / applicable)}%` : '--';
	});

	const trendPoints = $derived(data.trend?.points ?? []);

	const scopedAssets = $derived(data.data?.assets ?? []);
	const measuredAssets = $derived.by(() => {
		const scoped = new Set(scopedAssets.map((a: any) => a.id));
		const measured = new Set(
			results.map((r: any) => r.asset.id).filter((id: string) => scoped.has(id))
		);
		return measured.size;
	});

	const actionPlanRows = $derived.by(() => {
		const rows = data.actionPlan?.results ?? [];
		if (filterStatuses.length > 0 && !filterStatuses.includes('fail')) return [];
		return filterAsset ? rows.filter((row: any) => row.asset.id === filterAsset) : rows;
	});

	// per-asset rollups for the Assets tab
	const assetRows = $derived.by(() => {
		const byAsset: Record<string, { measured: number; pass: number; fail: number; last: string }> =
			{};
		for (const row of results) {
			const acc = (byAsset[row.asset.id] ??= { measured: 0, pass: 0, fail: 0, last: '' });
			acc.measured += 1;
			if (row.result === 'pass') acc.pass += 1;
			if (row.result === 'fail') acc.fail += 1;
			if (row.timestamp > acc.last) acc.last = row.timestamp;
		}
		return [...scopedAssets]
			.map((a: any) => {
				const acc = byAsset[a.id];
				const applicable = (acc?.pass ?? 0) + (acc?.fail ?? 0);
				return {
					id: a.id,
					name: assetLabel(a),
					measured: acc?.measured ?? 0,
					passRate: applicable ? Math.round((100 * (acc?.pass ?? 0)) / applicable) : null,
					lastRun: acc?.last || null
				};
			})
			.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
	});

	const modalStore: ModalStore = getModalStore();

	async function confirmPurge(asset: { id: string; name: string }) {
		let impact = '';
		try {
			const res = await fetch(`/posture-assessments/${data.data.id}/runs?asset=${asset.id}`);
			const body = await res.json();
			const stored = (body.runs ?? []).reduce((acc: number, r: any) => acc + r.checks, 0);
			impact = ` ${m.purgeAssetImpact({ results: stored, runs: (body.runs ?? []).length })}`;
		} catch {
			/* preview is best-effort */
		}
		modalStore.trigger({
			type: 'component',
			title: m.purgeAssetColumn(),
			body: m.purgeAssetConfirm({ asset: asset.name }) + impact,
			component: {
				ref: PromptConfirmModal,
				props: { bodyComponent: undefined }
			},
			response: async (confirmed: boolean) => {
				if (!confirmed) return;
				const fd = new FormData();
				fd.set('asset', asset.id);
				await fetch('?/purgeAsset', {
					method: 'POST',
					body: fd,
					headers: { 'x-sveltekit-action': 'true' }
				});
				await invalidateAll();
			}
		});
	}

	// file import (per asset row)
	let importInput: HTMLInputElement | undefined = $state();
	let importAssetId = $state('');
	let importSummary: any = $state(null);

	function startImport(assetId: string) {
		importAssetId = assetId;
		importSummary = null;
		importInput?.click();
	}

	async function onImportFile(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file || !importAssetId) return;
		const fd = new FormData();
		fd.set('asset', importAssetId);
		fd.set('file', file);
		const res = await fetch('?/importFile', {
			method: 'POST',
			body: fd,
			headers: { 'x-sveltekit-action': 'true' }
		});
		const result = deserialize(await res.text());
		importSummary =
			result.type === 'success' ? (result.data?.importSummary ?? { done: true }) : null;
		input.value = '';
		await invalidateAll();
	}

	// API snippet
	let snippetCopied = $state(false);
	const apiSnippet = $derived.by(() => {
		const origin = page.url.origin.replace(':5173', ':8000');
		const assetId = scopedAssets[0]?.id ?? '<asset-uuid>';
		const refId = checks[0]?.ref_id ?? '1.1';
		return [
			`curl -X POST ${origin}/api/automation/posture-assessments/${data.data.id}/upload-results/ \\`,
			`  -H "Authorization: Token <your-personal-access-token>" \\`,
			`  -H "Content-Type: application/json" \\`,
			`  -d '{`,
			`    "asset": "${assetId}",`,
			`    "tool": "kube-bench 0.7",`,
			`    "results": [`,
			`      {"ref_id": "${refId}", "result": "pass", "actual": "", "expected": "", "message": ""}`,
			`    ]`,
			`  }'`
		].join('\n');
	});

	// add-asset picker
	let pickerOpen = $state(false);
	let pickerQuery = $state('');
	let pickerResults: any[] = $state([]);

	async function searchAssets() {
		const scoped = new Set(scopedAssets.map((a: any) => a.id));
		const res = await fetch(`/assets?search=${encodeURIComponent(pickerQuery)}&limit=10`);
		const body = await res.json();
		pickerResults = (body.results ?? body).filter((a: any) => !scoped.has(a.id));
	}
</script>

<div class="flex flex-col space-y-4">
	<DetailView {data}>
		{#snippet actions()}
			<div class="flex flex-col space-y-2">
				<Anchor
					href="/posture-assessments/{data.data.id}/tree"
					class="btn preset-filled-primary-500 h-fit w-full"
					label={m.treeView()}
				>
					<i class="fa-solid fa-folder-tree mr-2"></i>{m.treeView()}
				</Anchor>
				<Anchor
					href="/posture-assessments/{data.data.id}/matrix"
					class="btn preset-filled-primary-500 h-fit w-full"
					label={m.matrixEdit()}
				>
					<i class="fa-solid fa-table-cells mr-2"></i>{m.matrixEdit()}
				</Anchor>
				<Anchor
					href="/posture-assessments/{data.data.id}/runs/new"
					class="btn preset-filled-primary-500 h-fit w-full"
					label={m.newManualRun()}
				>
					<i class="fa-solid fa-plus mr-2"></i>{m.newManualRun()}
				</Anchor>
			</div>
		{/snippet}
		{#snippet widgets()}
			<div class="h-full flex flex-col space-y-4">
				<div class="card p-4 bg-surface-50-950 shadow-xs">
					<h3 class="text-lg font-semibold mb-2">{m.currentPosture()}</h3>
					<div class="grid grid-cols-3 gap-2">
						<div class="rounded-lg bg-primary-100 p-3 text-center">
							<p class="text-xs font-medium text-primary-800-200">{m.passRate()}</p>
							<p class="text-xl font-bold text-primary-900" data-testid="posture-score">
								{displayedScore}
							</p>
						</div>
						<div class="rounded-lg bg-primary-100 p-3 text-center">
							<p class="text-xs font-medium text-primary-800-200">{m.measuredChecks()}</p>
							<p class="text-xl font-bold text-primary-900" data-testid="posture-measured">
								{checks.length}/{totalChecks}
							</p>
						</div>
						<div
							class="rounded-lg p-3 text-center {measuredAssets < scopedAssets.length
								? 'bg-amber-100 dark:bg-amber-900'
								: 'bg-primary-100'}"
						>
							<p class="text-xs font-medium text-primary-800-200">{m.assetCoverage()}</p>
							<p class="text-xl font-bold text-primary-900" data-testid="posture-coverage">
								{measuredAssets}/{scopedAssets.length}
							</p>
						</div>
					</div>
					<div class="mt-3 space-y-1">
						{#each Object.entries(resultLabels) as [value, label]}
							{#if counts[value]}
								<div class="flex items-center justify-between text-sm">
									<span class="flex items-center gap-2">
										<span
											class="inline-block w-3 h-3 rounded-sm {postureResultTailwindColorMap[value]}"
										></span>
										{label}
									</span>
									<span class="font-semibold">{counts[value]}</span>
								</div>
							{/if}
						{/each}
					</div>
				</div>
			</div>
		{/snippet}
	</DetailView>

	<div class="card bg-surface-50-950 shadow-xs">
		<Tabs value={activeTab} onValueChange={(e) => (activeTab = e.value)} class="w-full">
			<Tabs.List class="border-b border-surface-200-800 px-4">
				<Tabs.Trigger
					value="overview"
					class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
				>
					<i class="fa-solid fa-gauge-high mr-2"></i>{m.overview()}
				</Tabs.Trigger>
				<Tabs.Trigger
					value="assets"
					class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
				>
					<i class="fa-solid fa-server mr-2"></i>{m.assets()}
				</Tabs.Trigger>
				<Tabs.Trigger
					value="runs"
					class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
				>
					<i class="fa-solid fa-clock-rotate-left mr-2"></i>{m.postureRuns()}
				</Tabs.Trigger>
				<Tabs.Trigger
					value="action-plan"
					class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
				>
					<i class="fa-solid fa-clipboard-list mr-2"></i>{m.actionPlan()}
				</Tabs.Trigger>
				<Tabs.Trigger
					value="api"
					class="px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500"
				>
					<i class="fa-solid fa-plug mr-2"></i>{m.apiIntegration()}
				</Tabs.Trigger>
			</Tabs.List>

			<Tabs.Content value="overview" class="p-4 space-y-4">
				<div class="flex items-center gap-3 flex-wrap text-sm">
					<label class="flex items-center gap-2">
						{m.filterByAsset()}
						<select
							class="select w-56 py-1"
							data-testid="posture-filter-asset"
							bind:value={filterAsset}
						>
							<option value="">{m.allAssets()}</option>
							{#each scopedAssets as asset (asset.id)}
								<option value={asset.id}>{assetLabel(asset)}</option>
							{/each}
						</select>
					</label>
					<div class="flex items-center gap-1">
						{#each Object.entries(resultLabels) as [value, label]}
							<button
								type="button"
								data-testid="posture-filter-{value}"
								class="btn btn-sm {filterStatuses.includes(value)
									? 'preset-filled-primary-500'
									: 'preset-tonal'}"
								onclick={() => toggleStatus(value)}
							>
								<span
									class="inline-block w-2.5 h-2.5 rounded-sm mr-1 {postureResultTailwindColorMap[
										value
									]}"
								></span>
								{label}
							</button>
						{/each}
					</div>
					{#if filterActive}
						<button
							type="button"
							class="anchor text-sm"
							onclick={() => {
								filterAsset = '';
								filterStatuses = [];
							}}
						>
							{m.clearFilters()}
						</button>
					{/if}
				</div>

				{#if trendPoints.length > 1}
					{#key trendPoints}
						<div>
							<h3 class="text-lg font-semibold mb-2">{m.passRate()}</h3>
							<PostureTrendChart points={trendPoints} name="posture_trend" />
						</div>
					{/key}
				{/if}

				{#if filteredResults.length}
					{#key filteredResults}
						<div>
							<h3 class="text-lg font-semibold mb-2">{m.currentPosture()}</h3>
							<PostureHeatmapChart
								results={filteredResults}
								assets={filterAsset ? assets.filter((a) => a.id === filterAsset) : assets}
								name="posture_heatmap"
							/>
						</div>
					{/key}
				{:else if results.length}
					<p class="text-sm text-surface-500 p-4">{m.noEntriesFound()}</p>
				{:else}
					<div class="p-8 flex flex-col items-center gap-3 text-center">
						<i class="fa-solid fa-list-check text-3xl text-surface-400"></i>
						<p class="font-semibold">{m.noPostureResultsYet()}</p>
						<p class="text-sm text-surface-600-400">{m.noPostureResultsHelp()}</p>
						<Anchor
							href="/posture-assessments/{data.data.id}/tree"
							class="btn preset-filled-primary-500"
							label={m.treeView()}
						>
							<i class="fa-solid fa-folder-tree mr-2"></i>{m.treeView()}
						</Anchor>
					</div>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="assets" class="p-4">
				<div data-testid="posture-assets-card" class="space-y-3">
					<input
						bind:this={importInput}
						type="file"
						accept=".csv,.xlsx,.json"
						class="hidden"
						onchange={onImportFile}
					/>
					{#if importSummary}
						<p class="text-sm text-primary-700 dark:text-primary-300">
							<i class="fa-solid fa-file-import mr-1"></i>
							{m.importSummary({
								created: importSummary.created ?? '?',
								updated: importSummary.updated ?? 0,
								skipped:
									(importSummary.skipped_suppressed ?? 0) + (importSummary.skipped_other_class ?? 0)
							})}
						</p>
					{/if}
					<div class="flex items-center justify-between relative">
						<h3 class="text-lg font-semibold">{m.assets()}</h3>
						<div class="flex items-center gap-2">
							<a
								href="/posture-assessments/{data.data.id}/export?file_format=csv"
								class="btn btn-sm preset-tonal"
							>
								<i class="fa-solid fa-download mr-1"></i>{m.exportButton()}
								{m.asCSV()}
							</a>
							<a
								href="/posture-assessments/{data.data.id}/export?file_format=xlsx"
								class="btn btn-sm preset-tonal"
							>
								<i class="fa-solid fa-download mr-1"></i>{m.exportButton()}
								{m.asXLSX()}
							</a>
							<button
								class="btn btn-sm preset-filled-primary-500"
								onclick={() => {
									pickerOpen = !pickerOpen;
									if (pickerOpen) {
										pickerQuery = '';
										searchAssets();
									}
								}}
							>
								<i class="fa-solid fa-plus mr-1"></i>{m.addAssetColumn()}
							</button>
						</div>
						{#if pickerOpen}
							<div
								class="absolute right-0 top-full mt-1 card bg-surface-50-950 shadow-lg p-3 w-72 z-20 space-y-2"
							>
								<input
									type="search"
									class="input w-full py-1 text-sm"
									placeholder={m.searchPlaceholder()}
									bind:value={pickerQuery}
									oninput={searchAssets}
								/>
								<div class="max-h-64 overflow-y-auto">
									{#each pickerResults as candidate (candidate.id)}
										<form
											method="POST"
											action="?/addAsset"
											use:enhance={() =>
												({ update }) => {
													pickerOpen = false;
													update();
												}}
										>
											<input type="hidden" name="asset" value={candidate.id} />
											<button
												type="submit"
												class="w-full text-left px-2 py-1 text-sm rounded hover:bg-surface-100-900"
											>
												{candidate.folder?.str ? `${candidate.folder.str}/` : ''}{candidate.name ??
													candidate.str}
											</button>
										</form>
									{:else}
										<p class="text-xs text-surface-600-400">{m.noEntriesFound()}</p>
									{/each}
								</div>
							</div>
						{/if}
					</div>
					<table class="table-auto w-full text-sm">
						<thead>
							<tr class="text-left">
								<th class="px-2 py-1">{m.name()}</th>
								<th class="px-2 py-1">{m.coverage()}</th>
								<th class="px-2 py-1">{m.passRate()}</th>
								<th class="px-2 py-1">{m.lastRun()}</th>
								<th class="px-2 py-1"></th>
							</tr>
						</thead>
						<tbody>
							{#each assetRows as row (row.id)}
								<tr class="border-t border-surface-200-800" data-testid="posture-asset-row">
									<td class="px-2 py-2 font-medium">{row.name}</td>
									<td class="px-2 py-2 {row.measured === 0 ? 'text-surface-500' : ''}">
										{row.measured}/{totalChecks}
									</td>
									<td class="px-2 py-2">
										{row.passRate != null ? `${row.passRate}%` : '--'}
									</td>
									<td class="px-2 py-2 whitespace-nowrap">
										{row.lastRun ? new Date(row.lastRun).toLocaleString() : '--'}
									</td>
									<td class="px-2 py-2">
										<div class="flex items-center gap-3 justify-end">
											<Anchor
												href="/posture-assessments/{data.data.id}/tree?asset={row.id}"
												class="text-surface-500 hover:text-primary-500"
												label={m.treeView()}
											>
												<i class="fa-solid fa-folder-tree"></i>
											</Anchor>
											<Anchor
												href="/posture-assessments/{data.data.id}/runs/new?asset={row.id}"
												class="text-surface-500 hover:text-primary-500"
												label={m.newManualRun()}
											>
												<i class="fa-solid fa-plus"></i>
											</Anchor>
											<button
												type="button"
												class="text-surface-500 hover:text-primary-500"
												title={m.importResultsHelp()}
												onclick={() => startImport(row.id)}
											>
												<i class="fa-solid fa-file-import"></i>
											</button>
											<a
												href="/posture-assessments/{data.data
													.id}/export?asset={row.id}&file_format=csv"
												class="text-surface-500 hover:text-primary-500"
												title="{m.exportButton()} {m.asCSV()}"
											>
												<i class="fa-solid fa-download"></i>
											</a>
											{#if row.measured === 0}
												<form method="POST" action="?/removeAsset" use:enhance class="inline">
													<input type="hidden" name="asset" value={row.id} />
													<button
														type="submit"
														class="text-surface-400 hover:text-red-500"
														title={m.remove()}
													>
														<i class="fa-solid fa-xmark"></i>
													</button>
												</form>
											{:else}
												<button
													type="button"
													class="text-surface-400 hover:text-red-500"
													title={m.purgeAssetColumn()}
													onclick={() => confirmPurge(row)}
												>
													<i class="fa-solid fa-xmark"></i>
												</button>
											{/if}
										</div>
									</td>
								</tr>
							{:else}
								<tr><td colspan="5" class="px-2 py-4 text-surface-500">{m.noEntriesFound()}</td></tr
								>
							{/each}
						</tbody>
					</table>
				</div>
			</Tabs.Content>

			<Tabs.Content value="runs" class="p-4">
				{#if data.runs?.runs?.length}
					<div class="overflow-x-auto">
						<table class="table-auto w-full text-sm">
							<thead>
								<tr class="text-left">
									<th class="px-2 py-1">{m.date()}</th>
									<th class="px-2 py-1">{m.scanTool()}</th>
									<th class="px-2 py-1">{m.source()}</th>
									<th class="px-2 py-1">{m.assets()}</th>
									<th class="px-2 py-1">{m.measuredChecksShort()}</th>
									<th class="px-2 py-1">{m.pass()}</th>
									<th class="px-2 py-1">{m.fail()}</th>
								</tr>
							</thead>
							<tbody>
								{#each [...data.runs.runs].reverse() as run (run.run_id)}
									<tr class="border-t border-surface-200-800 hover:bg-surface-100-900">
										<td class="px-2 py-1 whitespace-nowrap">
											<Anchor
												href="/posture-assessments/{data.data.id}/runs/{run.run_id}"
												class="anchor"
												label={m.runDetail()}
											>
												{new Date(run.started_at).toLocaleString()}
											</Anchor>
										</td>
										<td class="px-2 py-1">{run.tool || '--'}</td>
										<td class="px-2 py-1">{run.source}</td>
										<td class="px-2 py-1">{run.assets}</td>
										<td class="px-2 py-1">{run.checks}</td>
										<td class="px-2 py-1 text-green-600 dark:text-green-400">{run.passed}</td>
										<td class="px-2 py-1 {run.failed ? 'text-red-600 dark:text-red-400' : ''}">
											{run.failed}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<p class="text-sm text-surface-500 p-4">{m.noEntriesFound()}</p>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="action-plan" class="p-4">
				{#if actionPlanRows.length}
					<div class="flex items-center justify-between mb-4">
						<p class="text-sm text-surface-600-400">
							{data.actionPlan.total_fails}
							{m.fail()} — {data.actionPlan.planned}
							{m.planned()}, {data.actionPlan.total_fails - data.actionPlan.planned}
							{m.unplanned()}
						</p>
					</div>
					<div class="overflow-x-auto">
						<table class="table-auto w-full text-sm">
							<thead>
								<tr class="text-left">
									<th class="px-2 py-1"></th>
									<th class="px-2 py-1">{m.assets()}</th>
									<th class="px-2 py-1">{m.observedValue()}</th>
									<th class="px-2 py-1">{m.actionPlan()}</th>
								</tr>
							</thead>
							<tbody>
								{#each actionPlanRows as row (`${row.requirement.id}:${row.asset.id}`)}
									<tr class="border-t border-surface-200-800 align-top">
										<td
											class="px-2 py-2 font-medium whitespace-nowrap"
											title={row.requirement.name}
										>
											{row.requirement.ref_id}
											<span class="font-normal text-surface-600-400 hidden lg:inline">
												{row.requirement.name?.length > 50
													? `${row.requirement.name.slice(0, 50)}…`
													: (row.requirement.name ?? '')}
											</span>
										</td>
										<td class="px-2 py-2 whitespace-nowrap">{row.asset.str}</td>
										<td class="px-2 py-2 text-surface-600-400">
											{[row.actual, row.expected ? `(expected: ${row.expected})` : '', row.message]
												.filter(Boolean)
												.join(' ') || '--'}
										</td>
										<td class="px-2 py-2">
											{#if row.finding}
												<div class="flex items-center gap-2 flex-wrap">
													<Anchor
														href="/findings/{row.finding.id}"
														class="anchor whitespace-nowrap"
														label={row.finding.name}
													>
														{row.finding.name}
													</Anchor>
													<span class="badge preset-tonal-secondary text-xs">
														{safeTranslate(row.finding.status)}
													</span>
													{#if row.finding.eta}
														<span class="text-xs text-surface-600-400"
															>{m.eta()}: {row.finding.eta}</span
														>
													{/if}
												</div>
											{:else}
												<form method="POST" action="?/createFinding" use:enhance>
													<input type="hidden" name="requirement" value={row.requirement.id} />
													<input type="hidden" name="asset" value={row.asset.id} />
													<button type="submit" class="btn btn-sm preset-filled-primary-500">
														<i class="fa-solid fa-clipboard-list mr-2"></i>{m.createFinding()}
													</button>
												</form>
											{/if}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<p class="text-sm text-surface-500 p-4">{m.noEntriesFound()}</p>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="api" class="p-4 space-y-3">
				<p class="text-sm text-surface-600-400">{m.apiSnippetHelp()}</p>
				<div class="relative">
					<pre
						class="text-xs bg-surface-100-900 rounded p-4 overflow-x-auto"
						data-testid="posture-api-snippet">{apiSnippet}</pre>
					<button
						type="button"
						class="btn btn-sm preset-tonal absolute top-2 right-2"
						use:copy={{ text: apiSnippet }}
						onclick={() => {
							navigator.clipboard?.writeText(apiSnippet);
							snippetCopied = true;
							setTimeout(() => (snippetCopied = false), 2000);
						}}
					>
						<i class="fa-solid {snippetCopied ? 'fa-check' : 'fa-copy'} mr-1"></i>
						{m.copy()}
					</button>
				</div>
			</Tabs.Content>
		</Tabs>
	</div>
</div>
