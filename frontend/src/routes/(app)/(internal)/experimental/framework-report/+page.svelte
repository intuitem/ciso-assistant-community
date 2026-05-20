<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';

	$pageTitle = 'Framework report (prototype)';

	// -----------------------------------------------------------------------------
	// Types — mirror the proposed backend response for GET /api/frameworks/{id}/report/
	// -----------------------------------------------------------------------------

	type Result =
		| 'not_assessed'
		| 'partially_compliant'
		| 'non_compliant'
		| 'compliant'
		| 'not_applicable';

	type Status = 'to_do' | 'in_progress' | 'in_review' | 'done';

	type ReportRow = {
		requirement_urn: string;
		requirement_parent_urn: string | null;
		requirement_ref_id: string;
		requirement_name: string;
		assessable: boolean;
		implementation_groups: string[];

		result: Result | null;
		status: Status;
		score: number | null;
		documentation_score: number | null;
		is_scored: boolean;

		compliance_assessment_id: string;
		compliance_assessment_name: string;
		folder_id: string;
		folder_path: string[];
		folder_path_str: string;

		applied_controls_count: number;
		evidences_count: number;
	};

	type FrameworkMeta = {
		id: string;
		name: string;
		min_score: number;
		max_score: number;
		scores_definition: { scale: { value: number; name: string; color?: string }[] };
		implementation_groups_definition: { id: string; name: string }[];
	};

	// -----------------------------------------------------------------------------
	// Fake data — looks like a realistic ISO 27001:2022-shaped framework
	// -----------------------------------------------------------------------------

	const framework: FrameworkMeta = {
		id: 'fw-iso27001-2022',
		name: 'ISO/IEC 27001:2022 (Annex A)',
		min_score: 0,
		max_score: 100,
		scores_definition: {
			scale: [
				{ value: 0, name: 'Initial' },
				{ value: 25, name: 'Repeatable' },
				{ value: 50, name: 'Defined' },
				{ value: 75, name: 'Managed' },
				{ value: 100, name: 'Optimized' }
			]
		},
		implementation_groups_definition: [
			{ id: 'core', name: 'Core controls' },
			{ id: 'advanced', name: 'Advanced controls' },
			{ id: 'extended', name: 'Extended controls' }
		]
	};

	const sections = [
		{ urn: 'urn:iso27k:a5', ref: 'A.5', name: 'Organizational controls' },
		{ urn: 'urn:iso27k:a6', ref: 'A.6', name: 'People controls' },
		{ urn: 'urn:iso27k:a7', ref: 'A.7', name: 'Physical controls' },
		{ urn: 'urn:iso27k:a8', ref: 'A.8', name: 'Technological controls' }
	];

	const reqCatalog: {
		urn: string;
		parent: string;
		ref: string;
		name: string;
		igs: string[];
	}[] = [
		{ urn: 'urn:iso27k:a5.1', parent: 'urn:iso27k:a5', ref: 'A.5.1', name: 'Policies for information security', igs: ['core'] },
		{ urn: 'urn:iso27k:a5.2', parent: 'urn:iso27k:a5', ref: 'A.5.2', name: 'Information security roles and responsibilities', igs: ['core'] },
		{ urn: 'urn:iso27k:a5.7', parent: 'urn:iso27k:a5', ref: 'A.5.7', name: 'Threat intelligence', igs: ['advanced'] },
		{ urn: 'urn:iso27k:a5.23', parent: 'urn:iso27k:a5', ref: 'A.5.23', name: 'Information security for cloud services', igs: ['advanced', 'extended'] },
		{ urn: 'urn:iso27k:a6.1', parent: 'urn:iso27k:a6', ref: 'A.6.1', name: 'Screening', igs: ['core'] },
		{ urn: 'urn:iso27k:a6.3', parent: 'urn:iso27k:a6', ref: 'A.6.3', name: 'Information security awareness, education and training', igs: ['core'] },
		{ urn: 'urn:iso27k:a6.7', parent: 'urn:iso27k:a6', ref: 'A.6.7', name: 'Remote working', igs: ['advanced'] },
		{ urn: 'urn:iso27k:a7.1', parent: 'urn:iso27k:a7', ref: 'A.7.1', name: 'Physical security perimeters', igs: ['core'] },
		{ urn: 'urn:iso27k:a7.4', parent: 'urn:iso27k:a7', ref: 'A.7.4', name: 'Physical security monitoring', igs: ['advanced'] },
		{ urn: 'urn:iso27k:a8.1', parent: 'urn:iso27k:a8', ref: 'A.8.1', name: 'User endpoint devices', igs: ['core'] },
		{ urn: 'urn:iso27k:a8.2', parent: 'urn:iso27k:a8', ref: 'A.8.2', name: 'Privileged access rights', igs: ['core', 'advanced'] },
		{ urn: 'urn:iso27k:a8.7', parent: 'urn:iso27k:a8', ref: 'A.8.7', name: 'Protection against malware', igs: ['core'] },
		{ urn: 'urn:iso27k:a8.15', parent: 'urn:iso27k:a8', ref: 'A.8.15', name: 'Logging', igs: ['advanced'] },
		{ urn: 'urn:iso27k:a8.23', parent: 'urn:iso27k:a8', ref: 'A.8.23', name: 'Web filtering', igs: ['advanced', 'extended'] },
		{ urn: 'urn:iso27k:a8.28', parent: 'urn:iso27k:a8', ref: 'A.8.28', name: 'Secure coding', igs: ['extended'] }
	];

	const assessments = [
		{
			id: 'ca-lyon',
			name: 'Plant-Lyon — 2026 Q1',
			folder_id: 'f-lyon',
			folder_path: ['Acme', 'EMEA', 'Plant-Lyon'],
			selected_igs: ['core', 'advanced']
		},
		{
			id: 'ca-paris',
			name: 'Plant-Paris — 2026 Q1',
			folder_id: 'f-paris',
			folder_path: ['Acme', 'EMEA', 'Plant-Paris'],
			selected_igs: ['core', 'advanced', 'extended']
		},
		{
			id: 'ca-nyc',
			name: 'Plant-NYC — 2026 Q1',
			folder_id: 'f-nyc',
			folder_path: ['Acme', 'Americas', 'Plant-NYC'],
			selected_igs: ['core']
		}
	];

	// deterministic-ish pseudo-randomizer so the mockup looks stable across reloads
	function pickResult(urn: string, caId: string): { result: Result; score: number | null; status: Status } {
		const seed = (urn + caId).split('').reduce((a, c) => a + c.charCodeAt(0), 0);
		const r = seed % 11;
		if (r === 0) return { result: 'not_assessed', score: null, status: 'to_do' };
		if (r <= 2) return { result: 'non_compliant', score: 15 + (seed % 10), status: 'done' };
		if (r <= 5) return { result: 'partially_compliant', score: 45 + (seed % 20), status: 'done' };
		if (r === 6) return { result: 'not_applicable', score: null, status: 'done' };
		return { result: 'compliant', score: 80 + (seed % 20), status: 'done' };
	}

	const rows: ReportRow[] = assessments.flatMap((ca) =>
		reqCatalog
			.filter((r) => r.igs.some((ig) => ca.selected_igs.includes(ig)))
			.map((r): ReportRow => {
				const { result, score, status } = pickResult(r.urn, ca.id);
				return {
					requirement_urn: r.urn,
					requirement_parent_urn: r.parent,
					requirement_ref_id: r.ref,
					requirement_name: r.name,
					assessable: true,
					implementation_groups: r.igs,
					result,
					status,
					score,
					documentation_score: score !== null ? Math.min(100, score + 5) : null,
					is_scored: score !== null,
					compliance_assessment_id: ca.id,
					compliance_assessment_name: ca.name,
					folder_id: ca.folder_id,
					folder_path: ca.folder_path,
					folder_path_str: ca.folder_path.join(' / '),
					applied_controls_count: (r.ref.length + ca.id.length) % 5,
					evidences_count: (r.ref.length + ca.id.length) % 4
				};
			})
	);

	// -----------------------------------------------------------------------------
	// Filter / view state
	// -----------------------------------------------------------------------------

	let igFilter = $state<string>('all');
	let view = $state<'requirement' | 'domain'>('requirement');
	let domainDepth = $state<number>(2);
	let expandedRow = $state<string | null>(null);
	let expandedSections = $state<Set<string>>(new Set());

	function toggleSection(urn: string) {
		const next = new Set(expandedSections);
		if (next.has(urn)) next.delete(urn);
		else next.add(urn);
		expandedSections = next;
	}

	function expandAllSections() {
		expandedSections = new Set(sections.map((s) => s.urn));
	}

	function collapseAllSections() {
		expandedSections = new Set();
	}

	const RESULT_COLORS: Record<Result, string> = {
		compliant: '#91CC75',
		partially_compliant: '#74C0DE',
		non_compliant: '#E66',
		not_applicable: '#EAE2D7',
		not_assessed: '#d7dfea'
	};

	const RESULT_LABELS: Record<Result, string> = {
		compliant: 'Compliant',
		partially_compliant: 'Partially compliant',
		non_compliant: 'Non-compliant',
		not_applicable: 'N/A',
		not_assessed: 'Not assessed'
	};

	const RESULT_ORDER: Result[] = [
		'compliant',
		'partially_compliant',
		'non_compliant',
		'not_applicable',
		'not_assessed'
	];

	let filteredRows = $derived(
		igFilter === 'all'
			? rows
			: rows.filter((r) => r.implementation_groups.includes(igFilter))
	);

	function distribution(rs: ReportRow[]): Record<Result, number> {
		const d: Record<Result, number> = {
			compliant: 0,
			partially_compliant: 0,
			non_compliant: 0,
			not_applicable: 0,
			not_assessed: 0
		};
		for (const r of rs) if (r.result) d[r.result]++;
		return d;
	}

	function avgScore(rs: ReportRow[]): number | null {
		const scored = rs.filter((r) => r.is_scored && r.score !== null);
		if (scored.length === 0) return null;
		return scored.reduce((a, r) => a + (r.score ?? 0), 0) / scored.length;
	}

	function compliancePct(d: Record<Result, number>): number {
		const total = d.compliant + d.partially_compliant + d.non_compliant + d.not_applicable + d.not_assessed;
		if (total === 0) return 0;
		// match CISO Assistant's usual compliance % logic: compliant + 0.5*partial, excluding NA + not assessed
		const denom = total - d.not_applicable - d.not_assessed;
		if (denom === 0) return 0;
		return ((d.compliant + 0.5 * d.partially_compliant) / denom) * 100;
	}

	// hierarchical rollup: sections at the top, each carrying its child requirement rollups
	let hierarchical = $derived.by(() =>
		sections
			.map((s) => {
				const sectionRows = filteredRows.filter((r) => r.requirement_parent_urn === s.urn);
				const reqMap = new Map<string, ReportRow[]>();
				for (const r of sectionRows) {
					if (!reqMap.has(r.requirement_urn)) reqMap.set(r.requirement_urn, []);
					reqMap.get(r.requirement_urn)!.push(r);
				}
				const requirements = [...reqMap.entries()]
					.map(([urn, rs]) => ({
						urn,
						ref_id: rs[0].requirement_ref_id,
						name: rs[0].requirement_name,
						ca_count: rs.length,
						dist: distribution(rs),
						avg_score: avgScore(rs),
						rows: rs
					}))
					.sort((a, b) => a.ref_id.localeCompare(b.ref_id, undefined, { numeric: true }));
				return {
					urn: s.urn,
					ref: s.ref,
					name: s.name,
					row_count: sectionRows.length,
					requirement_count: requirements.length,
					dist: distribution(sectionRows),
					avg_score: avgScore(sectionRows),
					requirements
				};
			})
			.filter((s) => s.row_count > 0 || s.requirement_count > 0)
	);

	// per-domain rollup at chosen ancestry depth (1 = top-level, 2 = mid, 3 = leaf folder)
	let perDomain = $derived.by(() => {
		const map = new Map<string, ReportRow[]>();
		for (const r of filteredRows) {
			const key = r.folder_path.slice(0, domainDepth).join(' / ');
			if (!map.has(key)) map.set(key, []);
			map.get(key)!.push(r);
		}
		return [...map.entries()]
			.map(([key, rs]) => ({
				key,
				ca_count: new Set(rs.map((r) => r.compliance_assessment_id)).size,
				row_count: rs.length,
				dist: distribution(rs),
				avg_score: avgScore(rs)
			}))
			.sort((a, b) => a.key.localeCompare(b.key));
	});

	let overallDist = $derived(distribution(filteredRows));
	let overallScore = $derived(avgScore(filteredRows));
	let overallCompliance = $derived(compliancePct(overallDist));
	let totalCAs = $derived(new Set(filteredRows.map((r) => r.compliance_assessment_id)).size);
	let totalAssessments = $derived(filteredRows.length);

	function distTotal(d: Record<Result, number>): number {
		return RESULT_ORDER.reduce((s, k) => s + d[k], 0);
	}

	function exportFlatJSON() {
		const blob = new Blob([JSON.stringify({ framework, rows: filteredRows, generated_at: new Date().toISOString() }, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `framework-report-${framework.id}.json`;
		a.click();
		URL.revokeObjectURL(url);
	}
</script>

<div class="space-y-4 p-2">
	<!-- Header card -->
	<div class="card p-4 bg-white">
		<div class="flex items-start justify-between gap-4 flex-wrap">
			<div>
				<div class="text-xs uppercase tracking-wide text-gray-500">Framework report (prototype)</div>
				<h1 class="text-xl font-semibold">{framework.name}</h1>
				<div class="text-sm text-gray-600 mt-1">
					Scoring scale {framework.min_score}–{framework.max_score} · {framework.implementation_groups_definition.length} implementation groups · aggregated across {assessments.length} compliance assessments
				</div>
			</div>
			<div class="flex gap-2 items-center">
				<button class="btn variant-ghost-surface text-sm" onclick={exportFlatJSON}>Export JSON</button>
				<button class="btn variant-ghost-surface text-sm" disabled title="not wired in the mockup">Export CSV</button>
			</div>
		</div>

		<!-- KPI row -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
			<div class="rounded border p-3">
				<div class="text-xs text-gray-500">Compliance %</div>
				<div class="text-2xl font-semibold">{overallCompliance.toFixed(1)}%</div>
				<div class="text-xs text-gray-500">compliant + ½·partial, excl. N/A &amp; not-assessed</div>
			</div>
			<div class="rounded border p-3">
				<div class="text-xs text-gray-500">Average implementation score</div>
				<div class="text-2xl font-semibold">{overallScore === null ? '—' : overallScore.toFixed(1)}</div>
				<div class="text-xs text-gray-500">over scored requirements only</div>
			</div>
			<div class="rounded border p-3">
				<div class="text-xs text-gray-500">Compliance assessments</div>
				<div class="text-2xl font-semibold">{totalCAs}</div>
				<div class="text-xs text-gray-500">visible to current user</div>
			</div>
			<div class="rounded border p-3">
				<div class="text-xs text-gray-500">Requirement assessments</div>
				<div class="text-2xl font-semibold">{totalAssessments}</div>
				<div class="text-xs text-gray-500">in scope after IG filter</div>
			</div>
		</div>

		<!-- Overall distribution -->
		<div class="mt-4">
			<div class="text-xs text-gray-500 mb-1">Overall result distribution</div>
			<div class="flex h-6 w-full rounded overflow-hidden border">
				{#each RESULT_ORDER as r}
					{@const w = distTotal(overallDist) === 0 ? 0 : (overallDist[r] / distTotal(overallDist)) * 100}
					{#if w > 0}
						<div
							class="h-full flex items-center justify-center text-[10px] text-gray-800"
							style="width:{w}%; background:{RESULT_COLORS[r]};"
							title="{RESULT_LABELS[r]}: {overallDist[r]}"
						>
							{overallDist[r] > 0 && w > 6 ? overallDist[r] : ''}
						</div>
					{/if}
				{/each}
			</div>
			<div class="flex gap-3 flex-wrap mt-2 text-xs">
				{#each RESULT_ORDER as r}
					<span class="inline-flex items-center gap-1">
						<span class="inline-block w-3 h-3 rounded-sm border" style="background:{RESULT_COLORS[r]};"></span>
						{RESULT_LABELS[r]} ({overallDist[r]})
					</span>
				{/each}
			</div>
		</div>
	</div>

	<!-- Filter + view bar -->
	<div class="card p-3 bg-white flex flex-wrap items-end gap-4">
		<div>
			<label class="text-xs text-gray-500 block">Implementation group</label>
			<select bind:value={igFilter} class="select select-sm">
				<option value="all">All groups (honor each CA's selection)</option>
				{#each framework.implementation_groups_definition as ig}
					<option value={ig.id}>{ig.name}</option>
				{/each}
			</select>
		</div>

		<div>
			<label class="text-xs text-gray-500 block">View</label>
			<div class="inline-flex rounded border overflow-hidden">
				{#each [['requirement', 'Requirements tree'], ['domain', 'Per domain']] as [k, label]}
					<button
						type="button"
						class="px-3 py-1 text-sm {view === k ? 'bg-primary-500 text-white' : 'bg-white hover:bg-gray-50'}"
						onclick={() => (view = k as typeof view)}
					>
						{label}
					</button>
				{/each}
			</div>
		</div>

		{#if view === 'requirement'}
			<div>
				<label class="text-xs text-gray-500 block">Sections</label>
				<div class="inline-flex gap-2">
					<button class="btn btn-sm variant-ghost-surface text-xs" onclick={expandAllSections}>Expand all</button>
					<button class="btn btn-sm variant-ghost-surface text-xs" onclick={collapseAllSections}>Collapse all</button>
				</div>
			</div>
		{/if}

		{#if view === 'domain'}
			<div>
				<label class="text-xs text-gray-500 block">Group by folder depth</label>
				<select bind:value={domainDepth} class="select select-sm">
					<option value={1}>1 — top organization</option>
					<option value={2}>2 — region / BU</option>
					<option value={3}>3 — leaf folder</option>
				</select>
			</div>
		{/if}

		<div class="ml-auto text-xs text-gray-500">
			{filteredRows.length} rows · click a row to drill down
		</div>
	</div>

	<!-- Main view -->
	<div class="card bg-white">
		{#if view === 'requirement'}
			<table class="w-full text-sm">
				<thead class="bg-gray-50 text-left">
					<tr>
						<th class="px-3 py-2 w-32">Ref</th>
						<th class="px-3 py-2">Section / requirement</th>
						<th class="px-3 py-2 w-24 text-center">Coverage</th>
						<th class="px-3 py-2 w-[28%]">Result distribution</th>
						<th class="px-3 py-2 w-28 text-right">Avg score</th>
					</tr>
				</thead>
				<tbody>
					{#each hierarchical as section}
						<tr
							class="border-t bg-gray-100 font-medium hover:bg-gray-200 cursor-pointer"
							onclick={() => toggleSection(section.urn)}
						>
							<td class="px-3 py-2 font-mono text-xs">
								<span class="inline-block w-3 text-gray-500">{expandedSections.has(section.urn) ? '▾' : '▸'}</span>
								{section.ref}
							</td>
							<td class="px-3 py-2">
								{section.name}
								<span class="text-xs text-gray-500 ml-2 font-normal">({section.requirement_count} reqs · {section.row_count} rows)</span>
							</td>
							<td class="px-3 py-2 text-center text-xs text-gray-500">—</td>
							<td class="px-3 py-2">
								{#if section.row_count > 0}
									<div class="flex h-5 w-full rounded overflow-hidden border">
										{#each RESULT_ORDER as r}
											{@const w = distTotal(section.dist) === 0 ? 0 : (section.dist[r] / distTotal(section.dist)) * 100}
											{#if w > 0}
												<div style="width:{w}%; background:{RESULT_COLORS[r]};" title="{RESULT_LABELS[r]}: {section.dist[r]}"></div>
											{/if}
										{/each}
									</div>
								{:else}
									<span class="text-xs text-gray-400">no rows in scope</span>
								{/if}
							</td>
							<td class="px-3 py-2 text-right font-mono">{section.avg_score === null ? '—' : section.avg_score.toFixed(0)}</td>
						</tr>

						{#if expandedSections.has(section.urn)}
							{#each section.requirements as req}
								<tr
									class="border-t hover:bg-gray-50 cursor-pointer"
									onclick={() => (expandedRow = expandedRow === req.urn ? null : req.urn)}
								>
									<td class="px-3 py-2 font-mono text-xs pl-8">
										<span class="inline-block w-3 text-gray-400">{expandedRow === req.urn ? '▾' : '▸'}</span>
										{req.ref_id}
									</td>
									<td class="px-3 py-2 pl-6">{req.name}</td>
									<td class="px-3 py-2 text-center">{req.ca_count}</td>
									<td class="px-3 py-2">
										<div class="flex h-4 w-full rounded overflow-hidden border">
											{#each RESULT_ORDER as r}
												{@const w = distTotal(req.dist) === 0 ? 0 : (req.dist[r] / distTotal(req.dist)) * 100}
												{#if w > 0}
													<div style="width:{w}%; background:{RESULT_COLORS[r]};" title="{RESULT_LABELS[r]}: {req.dist[r]}"></div>
												{/if}
											{/each}
										</div>
									</td>
									<td class="px-3 py-2 text-right font-mono">{req.avg_score === null ? '—' : req.avg_score.toFixed(0)}</td>
								</tr>
								{#if expandedRow === req.urn}
									<tr class="bg-gray-50 border-t">
										<td></td>
										<td colspan="4" class="px-3 py-2">
											<div class="text-xs text-gray-600 mb-2">Per-assessment breakdown</div>
											<table class="w-full text-xs">
												<thead>
													<tr class="text-left text-gray-500">
														<th class="py-1">Assessment</th>
														<th class="py-1">Domain</th>
														<th class="py-1">Result</th>
														<th class="py-1 text-right">Score</th>
														<th class="py-1 text-center">Controls</th>
														<th class="py-1 text-center">Evidences</th>
													</tr>
												</thead>
												<tbody>
													{#each req.rows as row}
														<tr class="border-t border-gray-200">
															<td class="py-1">{row.compliance_assessment_name}</td>
															<td class="py-1 font-mono">{row.folder_path_str}</td>
															<td class="py-1">
																<span class="inline-flex items-center gap-1">
																	<span class="inline-block w-2 h-2 rounded-full" style="background:{RESULT_COLORS[row.result ?? 'not_assessed']}"></span>
																	{row.result ? RESULT_LABELS[row.result] : '—'}
																</span>
															</td>
															<td class="py-1 text-right font-mono">{row.score ?? '—'}</td>
															<td class="py-1 text-center">{row.applied_controls_count}</td>
															<td class="py-1 text-center">{row.evidences_count}</td>
														</tr>
													{/each}
												</tbody>
											</table>
										</td>
									</tr>
								{/if}
							{/each}
						{/if}
					{/each}
				</tbody>
			</table>
		{:else if view === 'domain'}
			<table class="w-full text-sm">
				<thead class="bg-gray-50 text-left">
					<tr>
						<th class="px-3 py-2">Domain (depth {domainDepth})</th>
						<th class="px-3 py-2 w-24 text-center">CAs</th>
						<th class="px-3 py-2 w-24 text-center">Rows</th>
						<th class="px-3 py-2 w-[28%]">Result distribution</th>
						<th class="px-3 py-2 w-28 text-right">Avg score</th>
					</tr>
				</thead>
				<tbody>
					{#each perDomain as d}
						<tr class="border-t hover:bg-gray-50">
							<td class="px-3 py-2 font-mono">{d.key}</td>
							<td class="px-3 py-2 text-center">{d.ca_count}</td>
							<td class="px-3 py-2 text-center">{d.row_count}</td>
							<td class="px-3 py-2">
								<div class="flex h-4 w-full rounded overflow-hidden border">
									{#each RESULT_ORDER as r}
										{@const w = distTotal(d.dist) === 0 ? 0 : (d.dist[r] / distTotal(d.dist)) * 100}
										{#if w > 0}
											<div style="width:{w}%; background:{RESULT_COLORS[r]};" title="{RESULT_LABELS[r]}: {d.dist[r]}"></div>
										{/if}
									{/each}
								</div>
							</td>
							<td class="px-3 py-2 text-right font-mono">{d.avg_score === null ? '—' : d.avg_score.toFixed(0)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>

	<div class="text-xs text-gray-500 px-2 pb-4">
		Prototype — data is fabricated. The shape mirrors the proposed <code>GET /api/frameworks/&lbrace;id&rbrace;/report/</code> response: a <code>framework</code> block plus a flat <code>rows[]</code> array, one entry per RequirementAssessment.
	</div>
</div>
