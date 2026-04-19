<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	let { data } = $props();
	let crosswalk: any = $state(data.crosswalk);
	$pageTitle = `Crosswalk — ${crosswalk.name ?? ''}`;

	type Node = {
		id: string;
		urn: string;
		ref_id: string | null;
		name: string | null;
		description: string | null;
		parent_urn: string | null;
		section_label: string | null;
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

	let showTuning = $state(false);
	let tuneTopK = $state<number>(crosswalk.generation_params?.top_k ?? 5);
	let tuneMediumThreshold = $state<number>(crosswalk.generation_params?.medium_threshold ?? 0.5);
	let tuneHighThreshold = $state<number>(crosswalk.generation_params?.high_threshold ?? 0.7);
	let tuneUseBm25 = $state<boolean>(crosswalk.generation_params?.use_bm25 ?? true);

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
		const payload: Record<string, number | boolean> = {};
		if (Number.isFinite(tuneTopK)) payload.top_k = Math.max(1, Math.min(50, tuneTopK));
		if (Number.isFinite(tuneMediumThreshold))
			payload.medium_threshold = Math.max(0, Math.min(1, tuneMediumThreshold));
		if (Number.isFinite(tuneHighThreshold))
			payload.high_threshold = Math.max(0, Math.min(1, tuneHighThreshold));
		payload.use_bm25 = tuneUseBm25;
		if (
			typeof payload.high_threshold === 'number' &&
			typeof payload.medium_threshold === 'number' &&
			payload.high_threshold < payload.medium_threshold
		) {
			statusMessage = 'High threshold must be ≥ medium threshold.';
			return;
		}
		const res = await fetch(`/experimental/crosswalks/${crosswalk.id}?action=regenerate`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});
		if (res.ok) {
			statusMessage = '';
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

		// Section-level axis labels: show only the first node per section
		// (grouped by parent_urn), blank the rest. Humans scan a short list
		// of section headers faster than a wall of IDs.
		function sectionLabels(nodes: any[]): { labels: string[]; breaks: number[] } {
			const labels: string[] = [];
			const breaks: number[] = [];
			let prev: string | null | undefined = undefined;
			nodes.forEach((n, i) => {
				const key = n.parent_urn || '';
				if (key !== prev) {
					labels.push(n.section_label || n.ref_id || '');
					if (i > 0) breaks.push(i);
					prev = key;
				} else {
					labels.push('');
				}
			});
			return { labels, breaks };
		}
		const x = sectionLabels(target_nodes);
		const y = sectionLabels(source_nodes);

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

		const dividerStyle = {
			symbol: 'none',
			lineStyle: { color: '#d1d5db', type: 'solid' as const, width: 1 },
			silent: true,
			label: { show: false }
		};

		const srcFw = crosswalk.source_framework?.name ?? 'Source';
		const tgtFw = crosswalk.target_framework?.name ?? 'Target';

		chart.setOption(
			{
				grid: { left: 140, right: 20, top: 80, bottom: 30 },
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
					name: `Target → ${tgtFw}`,
					nameLocation: 'middle',
					nameGap: 55,
					nameTextStyle: {
						fontSize: 12,
						fontWeight: 700,
						color: '#111827'
					},
					data: x.labels,
					position: 'top',
					axisLabel: {
						rotate: 45,
						fontSize: 11,
						fontWeight: 600,
						color: '#374151',
						interval: 0,
						formatter: (v: string) => (v ? v : '')
					},
					axisTick: { show: false },
					axisLine: { show: false },
					splitArea: { show: false }
				},
				yAxis: {
					type: 'category',
					name: `Source ↓ ${srcFw}`,
					nameLocation: 'middle',
					nameGap: 90,
					nameRotate: 90,
					nameTextStyle: {
						fontSize: 12,
						fontWeight: 700,
						color: '#111827'
					},
					data: y.labels,
					inverse: true,
					axisLabel: {
						fontSize: 11,
						fontWeight: 600,
						color: '#374151',
						interval: 0,
						formatter: (v: string) => (v ? v : '')
					},
					axisTick: { show: false },
					axisLine: { show: false }
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
						animation: false,
						markLine: {
							...dividerStyle,
							data: [
								...x.breaks.map((i) => ({ xAxis: i - 0.5 })),
								...y.breaks.map((i) => ({ yAxis: i - 0.5 }))
							]
						}
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
						onclick={() => (showTuning = !showTuning)}
						title="Engine tuning"
						aria-label="Engine tuning"
					>
						<i class="fa-solid fa-sliders mr-1"></i> Tune
					</button>
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

			{#if showTuning}
				<div class="bg-gray-50 border rounded p-3 flex flex-wrap items-end gap-4 text-xs">
					<div>
						<label class="block font-semibold text-gray-600 mb-0.5" for="tune-topk">
							top_k
							<span class="font-normal text-gray-400">(candidates per source)</span>
						</label>
						<input
							id="tune-topk"
							class="input input-sm w-24"
							type="number"
							min="1"
							max="50"
							step="1"
							bind:value={tuneTopK}
						/>
					</div>
					<div>
						<label class="block font-semibold text-gray-600 mb-0.5" for="tune-med">
							medium_threshold
							<span class="font-normal text-gray-400">(floor, below is discarded)</span>
						</label>
						<input
							id="tune-med"
							class="input input-sm w-24"
							type="number"
							min="0"
							max="1"
							step="0.05"
							bind:value={tuneMediumThreshold}
						/>
					</div>
					<div>
						<label class="block font-semibold text-gray-600 mb-0.5" for="tune-high">
							high_threshold
							<span class="font-normal text-gray-400">(equal/superset/subset cutoff)</span>
						</label>
						<input
							id="tune-high"
							class="input input-sm w-24"
							type="number"
							min="0"
							max="1"
							step="0.05"
							bind:value={tuneHighThreshold}
						/>
					</div>
					<label class="inline-flex items-center gap-2 cursor-pointer">
						<input type="checkbox" class="checkbox" bind:checked={tuneUseBm25} />
						<span class="font-semibold text-gray-600">
							Hybrid (BM25 + dense)
							<span class="font-normal text-gray-400 block">
								Rescues pairs where shared jargon beats semantic similarity
							</span>
						</span>
					</label>
					<p class="text-[11px] text-gray-500 max-w-md">
						Values are stored on the mapping set and reused on future regenerations. Cosine scores
						for this model (MiniLM multilingual) usually land in 0.3–0.75.
					</p>
				</div>
			{/if}

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
						{crosswalk.status === 'generating' ? m.crosswalkGeneratingWait() : 'No suggestions yet.'}
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
					{@const meta = selectedPair.suggestion_metadata}
					{@const denseOnly = meta.dense_rank !== undefined && meta.bm25_rank === undefined}
					{@const bm25Only = meta.bm25_rank !== undefined && meta.dense_rank === undefined}
					<section class="bg-gray-50 rounded p-3 text-xs space-y-2">
						<div class="flex items-center justify-between">
							<h4 class="font-semibold uppercase text-gray-500">Engine signals</h4>
							{#if bm25Only}
								<span
									class="px-1.5 py-0.5 rounded bg-purple-100 text-purple-700"
									title="BM25 surfaced this pair; dense retrieval missed it"
								>
									BM25 rescue
								</span>
							{:else if denseOnly}
								<span class="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700">Dense only</span>
							{:else if meta.bm25_rank !== undefined}
								<span
									class="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700"
									title="Both dense and BM25 agreed"
								>
									Hybrid
								</span>
							{/if}
						</div>
						<div class="grid grid-cols-2 gap-1">
							<div>Cosine: <b>{meta.cosine}</b></div>
							<div>Lexical: <b>{meta.lexical}</b></div>
							<div>Length ratio: <b>{meta.length_ratio}</b></div>
							<div>Fused rank: <b>{meta.rank}</b></div>
							<div>Bi-dir: <b>{meta.bidirectional ? 'yes' : 'no'}</b></div>
							{#if meta.dense_rank !== undefined}
								<div>Dense rank: <b>{meta.dense_rank}</b></div>
							{/if}
							{#if meta.bm25_rank !== undefined}
								<div>BM25 rank: <b>{meta.bm25_rank}</b></div>
							{/if}
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
