<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { pageTitle } from '$lib/utils/stores';

	let { data } = $props();
	let crosswalk: any = $state(data.crosswalk);
	$pageTitle = `Crosswalk — ${crosswalk.name ?? ''}`;

	type Node = {
		id: string;
		urn: string;
		ref_id: string | null;
		name: string | null;
		description: string | null;
	};
	type Cell = {
		id: string;
		s: number;
		t: number;
		relationship: string;
		strength: number;
		reviewed: boolean;
		suggested: boolean;
	};

	const RELATIONSHIPS = [
		{ key: 'equal', label: 'Equal', short: 'E', color: '#10b981' },
		{ key: 'superset', label: 'Superset', short: 'U', color: '#3b82f6' },
		{ key: 'subset', label: 'Subset', short: 'B', color: '#8b5cf6' },
		{ key: 'intersect', label: 'Intersect', short: 'I', color: '#f59e0b' },
		{ key: 'not_related', label: 'Not related', short: 'N', color: '#9ca3af' }
	];
	const RELATION_COLOR: Record<string, string> = Object.fromEntries(
		RELATIONSHIPS.map((r) => [r.key, r.color])
	);

	let activeTab: 'matrix' | 'pairs' = $state('matrix');
	let matrixPayload: { source_nodes: Node[]; target_nodes: Node[]; cells: Cell[] } | null =
		$state(null);
	let matrixLoading = $state(true);
	let pairsLoading = $state(false);
	let pairs: any[] = $state([]);
	let pairsNext: string | null = $state(null);
	let filterRelationship = $state('');
	let filterReviewed = $state('');
	let selectedPairId: string | null = $state(null);
	let selectedPair: any | null = $state(null);
	let editRelationship = $state('');
	let editStrength = $state(0);
	let editAnnotation = $state('');
	let saving = $state(false);
	let statusMessage = $state('');
	let chartEl: HTMLDivElement | null = $state(null);
	let chart: any = null;

	async function loadMatrix() {
		matrixLoading = true;
		try {
			const res = await fetch(`/experimental/crosswalks/${crosswalk.id}/matrix`);
			if (res.ok) {
				matrixPayload = await res.json();
			}
		} finally {
			matrixLoading = false;
		}
	}

	async function loadPairs(reset = true) {
		pairsLoading = true;
		try {
			const params = new URLSearchParams();
			if (filterRelationship) params.set('relationship', filterRelationship);
			if (filterReviewed) params.set('reviewed', filterReviewed);
			params.set('ordering', '-strength_of_relationship');
			const res = await fetch(`/experimental/crosswalks/${crosswalk.id}/candidates?${params}`);
			if (res.ok) {
				const body = await res.json();
				pairs = reset ? body.results : pairs.concat(body.results);
				pairsNext = body.next ?? null;
			}
		} finally {
			pairsLoading = false;
		}
	}

	async function refreshCrosswalk() {
		const res = await fetch(`/experimental/crosswalks/${crosswalk.id}`);
		if (res.ok) {
			crosswalk = await res.json();
		}
	}

	async function regenerate() {
		if (!confirm('Re-run suggestion generation? This wipes unreviewed suggestions.')) return;
		const res = await fetch(`/experimental/crosswalks/${crosswalk.id}?action=regenerate`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' }
		});
		if (res.ok) {
			statusMessage = 'Regenerating…';
			startPolling();
		}
	}

	let pollTimer: ReturnType<typeof setInterval> | null = null;
	function startPolling() {
		stopPolling();
		pollTimer = setInterval(async () => {
			await refreshCrosswalk();
			if (crosswalk.status === 'ready' || crosswalk.status === 'reviewed') {
				stopPolling();
				statusMessage = 'Suggestions ready.';
				await loadMatrix();
				if (activeTab === 'pairs') await loadPairs();
				renderChart();
			} else if (crosswalk.status === 'failed') {
				stopPolling();
				statusMessage = `Generation failed: ${crosswalk.generation_error || 'unknown'}`;
			}
		}, 3000);
	}
	function stopPolling() {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
	}

	onMount(async () => {
		await loadMatrix();
		if (crosswalk.status === 'generating' || crosswalk.status === 'draft') {
			startPolling();
		}
	});
	onDestroy(() => {
		stopPolling();
		chart?.dispose?.();
		chart = null;
	});

	// Re-initialize the chart whenever the matrix tab mounts its DOM node.
	// Svelte tears down/rebuilds chartEl on tab switch, so the previous chart
	// instance ends up attached to a detached node.
	$effect(() => {
		if (activeTab !== 'matrix' || !chartEl || !matrixPayload) return;
		chart?.dispose?.();
		chart = null;
		renderChart();
	});

	async function renderChart() {
		if (!chartEl || !matrixPayload) return;
		const echarts = await import('echarts');
		if (!chart) chart = echarts.init(chartEl);

		const { source_nodes, target_nodes, cells } = matrixPayload;
		const cellSize = Math.max(8, Math.min(20, Math.floor(800 / Math.max(target_nodes.length, 1))));

		const data = cells.map((c) => ({
			value: [c.t, c.s, c.strength],
			itemStyle: {
				color: RELATION_COLOR[c.relationship] || '#d1d5db',
				opacity: c.reviewed ? 1 : 0.75,
				borderColor: c.reviewed ? '#111827' : 'transparent',
				borderWidth: c.reviewed ? 1 : 0
			},
			relationship: c.relationship,
			cellId: c.id
		}));

		chart.setOption(
			{
				grid: { left: 140, right: 20, top: 30, bottom: 120 },
				tooltip: {
					formatter: (p: any) => {
						const tgt = target_nodes[p.value[0]];
						const src = source_nodes[p.value[1]];
						const rel = p.data.relationship;
						const s = p.value[2];
						return `
							<div style="max-width:380px;">
								<div style="font-weight:600;">${src?.ref_id || ''} → ${tgt?.ref_id || ''}</div>
								<div style="margin-top:4px;"><span style="color:${RELATION_COLOR[rel]};">■</span> ${rel} · strength ${s}</div>
								<div style="margin-top:6px;font-size:11px;color:#555;"><b>Source:</b> ${escapeHtml(src?.name || '')}</div>
								<div style="font-size:11px;color:#555;">${escapeHtml((src?.description || '').slice(0, 180))}</div>
								<div style="margin-top:4px;font-size:11px;color:#555;"><b>Target:</b> ${escapeHtml(tgt?.name || '')}</div>
								<div style="font-size:11px;color:#555;">${escapeHtml((tgt?.description || '').slice(0, 180))}</div>
							</div>
						`;
					}
				},
				xAxis: {
					type: 'category',
					data: target_nodes.map((n) => n.ref_id || ''),
					position: 'top',
					axisLabel: {
						rotate: 60,
						fontSize: 10,
						interval: 0
					},
					splitArea: { show: false },
					axisTick: { alignWithLabel: true }
				},
				yAxis: {
					type: 'category',
					data: source_nodes.map((n) => n.ref_id || ''),
					inverse: true,
					axisLabel: { fontSize: 10, interval: 0 }
				},
				dataZoom: [
					{ type: 'inside', xAxisIndex: 0 },
					{ type: 'inside', yAxisIndex: 0 }
				],
				series: [
					{
						type: 'scatter',
						symbol: 'rect',
						symbolSize: cellSize,
						data,
						animation: false
					}
				]
			},
			true
		);

		chart.off('click');
		chart.on('click', (p: any) => {
			if (p?.data?.cellId) {
				openPair(p.data.cellId);
			}
		});
	}

	function escapeHtml(s: string) {
		return s
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;');
	}

	async function openPair(pairId: string) {
		selectedPairId = pairId;
		// Try cache
		const cached = pairs.find((p) => p.id === pairId);
		if (cached) {
			selectedPair = cached;
		} else {
			const res = await fetch(`/experimental/crosswalks/${crosswalk.id}/pairs/${pairId}`).catch(
				() => null
			);
			if (res?.ok) selectedPair = await res.json();
		}
		if (selectedPair) {
			editRelationship = selectedPair.relationship;
			editStrength = selectedPair.strength_of_relationship ?? 5;
			editAnnotation = selectedPair.annotation ?? '';
		}
	}

	function closePair() {
		selectedPairId = null;
		selectedPair = null;
	}

	async function savePair() {
		if (!selectedPair) return;
		saving = true;
		try {
			const res = await fetch(`/experimental/crosswalks/${crosswalk.id}/pairs/${selectedPair.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					mapping_set: crosswalk.id,
					source_requirement: selectedPair.source_requirement?.id,
					target_requirement: selectedPair.target_requirement?.id,
					relationship: editRelationship,
					strength_of_relationship: editStrength,
					annotation: editAnnotation,
					reviewed: true
				})
			});
			if (res.ok) {
				const updated = await res.json();
				selectedPair = updated;
				// Update matrix cell color in-place
				const idx = matrixPayload?.cells.findIndex((c) => c.id === updated.id) ?? -1;
				if (idx >= 0 && matrixPayload) {
					matrixPayload.cells[idx] = {
						...matrixPayload.cells[idx],
						relationship: updated.relationship,
						strength: updated.strength_of_relationship ?? 0,
						reviewed: true
					};
					matrixPayload = { ...matrixPayload };
					await renderChart();
				}
				// Update pairs table row
				const pIdx = pairs.findIndex((p) => p.id === updated.id);
				if (pIdx >= 0) {
					pairs[pIdx] = updated;
					pairs = [...pairs];
				}
				statusMessage = 'Saved.';
				setTimeout(() => (statusMessage = ''), 1500);
			} else {
				const err = await res.json().catch(() => ({}));
				statusMessage = `Save failed: ${err.detail || JSON.stringify(err)}`;
			}
		} finally {
			saving = false;
		}
	}

	function handleKey(e: KeyboardEvent) {
		if (!selectedPair) return;
		const tag = (e.target as HTMLElement)?.tagName;
		if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
		const map: Record<string, string> = {
			e: 'equal',
			u: 'superset',
			b: 'subset',
			i: 'intersect',
			n: 'not_related'
		};
		const r = map[e.key.toLowerCase()];
		if (r) {
			editRelationship = r;
			e.preventDefault();
		} else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
			savePair();
			e.preventDefault();
		} else if (e.key === 'Escape') {
			closePair();
		}
	}

	let summary = $derived(
		(() => {
			if (!matrixPayload) return null;
			const counts: Record<string, number> = {
				equal: 0,
				superset: 0,
				subset: 0,
				intersect: 0,
				not_related: 0
			};
			let reviewed = 0;
			for (const c of matrixPayload.cells) {
				counts[c.relationship] = (counts[c.relationship] ?? 0) + 1;
				if (c.reviewed) reviewed += 1;
			}
			return {
				total: matrixPayload.cells.length,
				reviewed,
				counts,
				sourceCount: matrixPayload.source_nodes.length,
				targetCount: matrixPayload.target_nodes.length
			};
		})()
	);
</script>

<svelte:window on:keydown={handleKey} />

<div class="flex h-[calc(100vh-80px)]">
	<div class="flex-1 flex flex-col overflow-hidden">
		<!-- Header -->
		<header class="p-4 border-b space-y-2">
			<div class="flex items-start justify-between gap-4">
				<div>
					<a href="/experimental/crosswalks" class="text-xs text-gray-500 hover:underline"
						>← All crosswalks</a
					>
					<h1 class="text-xl font-semibold">{crosswalk.name}</h1>
					<p class="text-xs text-gray-500">
						{crosswalk.source_framework?.name ?? '—'} → {crosswalk.target_framework?.name ?? '—'}
					</p>
				</div>
				<div class="flex items-center gap-2">
					<span
						class="text-xs px-2 py-0.5 rounded-full {crosswalk.status === 'ready'
							? 'bg-green-100 text-green-700'
							: crosswalk.status === 'generating'
								? 'bg-blue-100 text-blue-700'
								: crosswalk.status === 'failed'
									? 'bg-red-100 text-red-700'
									: 'bg-gray-100 text-gray-700'}"
					>
						{crosswalk.status}
					</span>
					<button
						type="button"
						class="btn btn-sm bg-gray-100 text-gray-700 hover:bg-gray-200"
						onclick={regenerate}
						disabled={crosswalk.status === 'generating'}
					>
						<i class="fa-solid fa-rotate mr-1"></i> Regenerate
					</button>
				</div>
			</div>

			{#if summary}
				<div class="flex flex-wrap gap-4 text-xs text-gray-600">
					<div>
						<b>{summary.total}</b> pairs · <b>{summary.reviewed}</b> reviewed
					</div>
					<div>
						<b>{summary.sourceCount}</b> source · <b>{summary.targetCount}</b> target
					</div>
					{#each RELATIONSHIPS as r}
						<div class="flex items-center gap-1">
							<span class="inline-block w-3 h-3 rounded-sm" style="background:{r.color}"></span>
							{r.label}: <b>{summary.counts[r.key] ?? 0}</b>
						</div>
					{/each}
				</div>
			{/if}
			{#if statusMessage}
				<p class="text-xs text-gray-600">{statusMessage}</p>
			{/if}
		</header>

		<!-- Tabs -->
		<div class="border-b px-4 flex gap-1 pt-2">
			<button
				type="button"
				class="px-3 py-2 text-sm rounded-t {activeTab === 'matrix'
					? 'bg-primary-500 text-white'
					: 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
				onclick={() => (activeTab = 'matrix')}
			>
				<i class="fa-solid fa-table-cells mr-1"></i> Matrix
			</button>
			<button
				type="button"
				class="px-3 py-2 text-sm rounded-t {activeTab === 'pairs'
					? 'bg-primary-500 text-white'
					: 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
				onclick={() => {
					activeTab = 'pairs';
					if (pairs.length === 0) loadPairs();
				}}
			>
				<i class="fa-solid fa-list mr-1"></i> Pairs
			</button>
		</div>

		<!-- Tab content -->
		<div class="flex-1 overflow-auto">
			{#if activeTab === 'matrix'}
				{#if matrixLoading}
					<div class="p-8 text-center text-gray-500">Loading matrix…</div>
				{:else if !matrixPayload || matrixPayload.cells.length === 0}
					<div class="p-8 text-center text-gray-500">
						{crosswalk.status === 'generating'
							? 'Generating suggestions… this may take a minute for large frameworks.'
							: 'No suggestions yet.'}
					</div>
				{:else}
					<div class="p-4">
						<div bind:this={chartEl} class="w-full" style="height: calc(100vh - 260px);"></div>
						<p class="text-xs text-gray-400 mt-2">
							Hover for pair details · scroll to zoom · click a cell to review it.
						</p>
					</div>
				{/if}
			{:else}
				<div class="p-4">
					<div class="flex items-end gap-3 mb-3 flex-wrap">
						<div>
							<label class="label text-xs" for="f-rel">Relationship</label>
							<select
								id="f-rel"
								class="select select-sm"
								bind:value={filterRelationship}
								onchange={() => loadPairs()}
							>
								<option value="">All</option>
								{#each RELATIONSHIPS as r}
									<option value={r.key}>{r.label}</option>
								{/each}
							</select>
						</div>
						<div>
							<label class="label text-xs" for="f-rev">Reviewed</label>
							<select
								id="f-rev"
								class="select select-sm"
								bind:value={filterReviewed}
								onchange={() => loadPairs()}
							>
								<option value="">All</option>
								<option value="true">Reviewed</option>
								<option value="false">Unreviewed</option>
							</select>
						</div>
					</div>
					{#if pairsLoading && pairs.length === 0}
						<div class="text-gray-500">Loading pairs…</div>
					{:else}
						<table class="table table-compact w-full text-sm">
							<thead>
								<tr>
									<th>Source</th>
									<th>Target</th>
									<th>Suggested</th>
									<th>Strength</th>
									<th>Reviewed</th>
									<th></th>
								</tr>
							</thead>
							<tbody>
								{#each pairs as p}
									<tr class="hover:bg-gray-50 cursor-pointer" onclick={() => openPair(p.id)}>
										<td title={p.source_requirement?.description}>
											<b>{p.source_requirement?.ref_id || ''}</b> —
											{p.source_requirement?.name || ''}
										</td>
										<td title={p.target_requirement?.description}>
											<b>{p.target_requirement?.ref_id || ''}</b> —
											{p.target_requirement?.name || ''}
										</td>
										<td>
											<span
												class="px-2 py-0.5 text-xs rounded"
												style="background:{RELATION_COLOR[p.relationship]};color:white;"
											>
												{p.relationship}
											</span>
										</td>
										<td>{p.strength_of_relationship ?? '—'}</td>
										<td>
											{p.reviewed ? '✓' : ''}
										</td>
										<td>
											<button
												type="button"
												class="btn btn-sm variant-ghost-primary"
												onclick={(e) => {
													e.stopPropagation();
													openPair(p.id);
												}}>Review</button
											>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
						{#if pairsNext}
							<p class="text-center mt-3">
								<button class="btn btn-sm variant-ghost-surface" onclick={() => loadPairs(false)}
									>Load more</button
								>
							</p>
						{/if}
					{/if}
				</div>
			{/if}
		</div>
	</div>

	<!-- Side panel -->
	{#if selectedPair}
		<aside
			class="w-[420px] border-l bg-white overflow-y-auto flex flex-col"
			aria-label="Pair detail"
		>
			<div class="p-4 border-b flex items-start justify-between gap-2">
				<div>
					<div class="text-xs text-gray-500">Reviewing pair</div>
					<div class="font-semibold text-sm">
						{selectedPair.source_requirement?.ref_id} → {selectedPair.target_requirement?.ref_id}
					</div>
				</div>
				<button type="button" class="btn btn-sm" onclick={closePair} aria-label="Close">
					<i class="fa-solid fa-xmark"></i>
				</button>
			</div>

			<div class="p-4 space-y-4 flex-1 overflow-y-auto">
				<section>
					<h4 class="text-xs font-semibold uppercase text-gray-500 mb-1">Source</h4>
					<div class="text-sm">
						<b>{selectedPair.source_requirement?.ref_id}</b> —
						{selectedPair.source_requirement?.name}
					</div>
					{#if selectedPair.source_requirement?.description}
						<p class="text-xs text-gray-600 mt-1">
							{selectedPair.source_requirement.description}
						</p>
					{/if}
				</section>
				<section>
					<h4 class="text-xs font-semibold uppercase text-gray-500 mb-1">Target</h4>
					<div class="text-sm">
						<b>{selectedPair.target_requirement?.ref_id}</b> —
						{selectedPair.target_requirement?.name}
					</div>
					{#if selectedPair.target_requirement?.description}
						<p class="text-xs text-gray-600 mt-1">
							{selectedPair.target_requirement.description}
						</p>
					{/if}
				</section>

				{#if selectedPair.suggestion_metadata}
					<section class="bg-gray-50 rounded p-3 text-xs space-y-1">
						<h4 class="font-semibold uppercase text-gray-500">Engine signals</h4>
						<div class="grid grid-cols-2 gap-1">
							<div>Cosine: <b>{selectedPair.suggestion_metadata.cosine}</b></div>
							<div>Lexical: <b>{selectedPair.suggestion_metadata.lexical}</b></div>
							<div>Length ratio: <b>{selectedPair.suggestion_metadata.length_ratio}</b></div>
							<div>Rank: <b>{selectedPair.suggestion_metadata.rank}</b></div>
							<div>
								Bi-dir:
								<b>{selectedPair.suggestion_metadata.bidirectional ? 'yes' : 'no'}</b>
							</div>
						</div>
					</section>
				{/if}

				<section class="space-y-2">
					<div>
						<label class="label text-xs" for="edit-rel">
							Relationship
							<span class="text-gray-400">(E / U / B / I / N)</span>
						</label>
						<select id="edit-rel" class="select" bind:value={editRelationship}>
							{#each RELATIONSHIPS as r}
								<option value={r.key}>{r.label}</option>
							{/each}
						</select>
					</div>
					<div>
						<label class="label text-xs" for="edit-str">Strength ({editStrength}/10)</label>
						<input
							id="edit-str"
							class="w-full"
							type="range"
							min="0"
							max="10"
							bind:value={editStrength}
						/>
					</div>
					<div>
						<label class="label text-xs" for="edit-ann">Annotation</label>
						<textarea id="edit-ann" class="textarea" rows="3" bind:value={editAnnotation}
						></textarea>
					</div>
				</section>
			</div>

			<div class="p-4 border-t flex justify-between items-center">
				<p class="text-xs text-gray-500">⌘+Enter to save</p>
				<button
					type="button"
					class="btn bg-primary-500 text-white hover:bg-primary-600 disabled:opacity-50"
					onclick={savePair}
					disabled={saving}
				>
					{#if saving}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
					{:else}
						<i class="fa-solid fa-floppy-disk mr-1"></i>
					{/if}
					Save & mark reviewed
				</button>
			</div>
		</aside>
	{/if}
</div>
