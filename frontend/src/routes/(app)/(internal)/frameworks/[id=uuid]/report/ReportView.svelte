<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import { formatDate } from '$lib/utils/datetime';
	import { safeTranslate } from '$lib/utils/i18n';

	// -----------------------------------------------------------------------------
	// Types — match the backend response shape from GET /api/frameworks/{id}/report/
	// -----------------------------------------------------------------------------

	type Result =
		| 'not_assessed'
		| 'partially_compliant'
		| 'non_compliant'
		| 'compliant'
		| 'not_applicable';

	type ReportRow = {
		requirement_assessment_id: string;
		requirement_urn: string;
		requirement_parent_urn: string | null;
		requirement_ref_id: string | null;
		requirement_name: string | null;
		assessable: boolean;
		implementation_groups: string[] | null;

		result: Result | null;
		extended_result: string | null;
		status: string | null;
		score: number | null;
		documentation_score: number | null;
		is_scored: boolean | null;

		compliance_assessment_id: string;
		compliance_assessment_name: string;
		folder_id: string | null;
		folder_path: string[];
		folder_path_str: string;

		applied_controls_count: number;
		evidences_count: number;
		direct_evidences_count: number;
		indirect_evidences_count: number;
	};

	type ComplianceAssessmentSummary = {
		id: string;
		name: string;
		status: string | null;
		folder_id: string | null;
		folder_path: string[];
		folder_path_str: string;
		is_counted: boolean;
	};

	type Section = {
		urn: string;
		ref_id: string | null;
		name: string | null;
		parent_urn: string | null;
	};

	type IGDef = { id?: string; ref_id?: string; name: string };

	type Framework = {
		id: string;
		name: string;
		min_score: number | null;
		max_score: number | null;
		scores_definition: { scale?: { value: number; name: string }[] } | null;
		implementation_groups_definition: IGDef[] | null;
		sections: Section[];
	};

	type ReportPayload = {
		framework: Framework;
		rows: ReportRow[];
		compliance_assessments: ComplianceAssessmentSummary[];
		ca_status_counts: Record<string, number>;
		live_statuses: string[];
		generated_at: string;
	};

	interface Props {
		report: ReportPayload;
	}

	let { report }: Props = $props();
	// Reactive snapshots of the payload — the parent {#await} block does remount
	// this component on each promise resolution today, but tracking via $derived
	// is defense-in-depth and means the file stays correct if a future caller
	// passes a reactive `report` prop without remounting.
	let framework = $derived(report.framework);
	let rows = $derived<ReportRow[]>(report.rows ?? []);
	let sectionList = $derived<Section[]>(framework.sections ?? []);
	let igDefs = $derived<IGDef[]>(framework.implementation_groups_definition ?? []);
	let caStatusCounts = $derived<Record<string, number>>(report.ca_status_counts ?? {});
	let liveStatuses = $derived<string[]>(
		report.live_statuses ?? ['in_progress', 'in_review', 'done']
	);
	let complianceAssessments = $derived<ComplianceAssessmentSummary[]>(
		report.compliance_assessments ?? []
	);

	const STATUS_ORDER = ['in_progress', 'in_review', 'done', 'planned', 'deprecated', 'unknown'];
	let orderedStatusCounts = $derived(
		STATUS_ORDER.map((s) => [s, caStatusCounts[s] ?? 0] as const).filter(([, n]) => n > 0)
	);
	let totalDetectedCAs = $derived(Object.values(caStatusCounts).reduce((a, b) => a + b, 0));
	let countedCAs = $derived(liveStatuses.reduce((a, s) => a + (caStatusCounts[s] ?? 0), 0));
	let excludedCAs = $derived(totalDetectedCAs - countedCAs);

	$effect(() => {
		$pageTitle = `${framework.name} — ${m.frameworkReport()}`;
	});

	// IG id resolver: most YAMLs use ref_id as the canonical key on the requirement
	// side (implementation_groups: ["1", "2"]) while the framework header may
	// expose them as objects with either {id, name} or {ref_id, name}.
	function igKey(d: IGDef): string {
		return (d.ref_id ?? d.id ?? d.name ?? '').toString();
	}

	// -----------------------------------------------------------------------------
	// Filter / view state — IG filter is reflected in the URL so users can deeplink
	// -----------------------------------------------------------------------------

	// Drive directly from the URL so back/forward and any external URL update
	// stay in sync. The dropdown is therefore one-way: `value={igFilter}` and
	// the change handler does the goto().
	let igFilter = $derived(page.url.searchParams.get('implementation_group') ?? 'all');
	let view = $state<'requirement' | 'domain'>('requirement');
	let domainDepth = $state<number>(2);
	let expandedRow = $state<string | null>(null);
	let expandedSections = $state<Set<string>>(new Set());
	let showCAList = $state<boolean>(false);
	let domainSortKey = $state<'name' | 'compliance' | 'score'>('name');
	let domainSortDir = $state<'asc' | 'desc'>('asc');

	function setDomainSortKey(k: 'name' | 'compliance' | 'score') {
		if (k === domainSortKey) return;
		domainSortKey = k;
		// pick a sensible default direction per metric
		domainSortDir = k === 'name' ? 'asc' : 'desc';
	}

	function toggleDomainSortDir() {
		domainSortDir = domainSortDir === 'asc' ? 'desc' : 'asc';
	}

	function toggleSection(urn: string) {
		const next = new Set(expandedSections);
		if (next.has(urn)) next.delete(urn);
		else next.add(urn);
		expandedSections = next;
	}

	function expandAllSections(urns: string[]) {
		expandedSections = new Set(urns);
	}

	function collapseAllSections() {
		expandedSections = new Set();
	}

	function onIGChange(event: Event) {
		const nextIG = (event.currentTarget as HTMLSelectElement).value;
		const url = new URL(page.url);
		if (nextIG && nextIG !== 'all') url.searchParams.set('implementation_group', nextIG);
		else url.searchParams.delete('implementation_group');
		goto(url, { invalidateAll: true, keepFocus: true });
	}

	const RESULT_COLORS: Record<Result, string> = {
		compliant: '#91CC75',
		partially_compliant: '#74C0DE',
		non_compliant: '#E66',
		not_applicable: '#EAE2D7',
		not_assessed: '#d7dfea'
	};

	const resultLabel = (r: Result): string => safeTranslate(r);

	const RESULT_ORDER: Result[] = [
		'compliant',
		'partially_compliant',
		'non_compliant',
		'not_applicable',
		'not_assessed'
	];

	function distribution(rs: ReportRow[]): Record<Result, number> {
		const d: Record<Result, number> = {
			compliant: 0,
			partially_compliant: 0,
			non_compliant: 0,
			not_applicable: 0,
			not_assessed: 0
		};
		for (const r of rs) {
			const k: Result = (r.result as Result | null) ?? 'not_assessed';
			d[k]++;
		}
		return d;
	}

	function avgScore(rs: ReportRow[]): number | null {
		const scored = rs.filter((r) => r.is_scored && r.score !== null && r.score !== undefined);
		if (scored.length === 0) return null;
		return scored.reduce((a, r) => a + (r.score ?? 0), 0) / scored.length;
	}

	function compliancePct(d: Record<Result, number>): number | null {
		const total =
			d.compliant + d.partially_compliant + d.non_compliant + d.not_applicable + d.not_assessed;
		if (total === 0) return null;
		const denom = total - d.not_applicable - d.not_assessed;
		if (denom === 0) return null;
		return ((d.compliant + 0.5 * d.partially_compliant) / denom) * 100;
	}

	function distTotal(d: Record<Result, number>): number {
		return RESULT_ORDER.reduce((s, k) => s + d[k], 0);
	}

	// Backend already honors each CA's selected IGs; the dropdown narrows further.
	let filteredRows = $derived(
		igFilter === 'all'
			? rows
			: rows.filter((r) => (r.implementation_groups ?? []).includes(igFilter))
	);

	// Hierarchical rollup: sections at the top, each carrying its child requirement rollups.
	// "Section" = the immediate parent_urn of an assessable requirement, if that parent is
	// non-assessable. If the parent_urn isn't in the framework's non-assessable nodes (e.g.
	// requirement points directly to the framework root), we bucket those into a synthetic
	// "Top level" section.
	let hierarchical = $derived.by(() => {
		// group rows by parent urn
		const byParent = new Map<string, ReportRow[]>();
		for (const r of filteredRows) {
			const key = r.requirement_parent_urn ?? '__root__';
			if (!byParent.has(key)) byParent.set(key, []);
			byParent.get(key)!.push(r);
		}

		// Build section descriptors in section order, falling back to "Top level"
		// for orphan parents (rows whose parent_urn isn't a known non-assessable node).
		const result: {
			urn: string;
			ref: string;
			name: string;
			row_count: number;
			requirement_count: number;
			dist: Record<Result, number>;
			avg_score: number | null;
			requirements: {
				urn: string;
				ref_id: string;
				name: string;
				ca_count: number;
				dist: Record<Result, number>;
				avg_score: number | null;
				rows: ReportRow[];
			}[];
		}[] = [];

		const seen = new Set<string>();

		const pushSection = (urn: string, ref: string, name: string, rs: ReportRow[]) => {
			const reqMap = new Map<string, ReportRow[]>();
			for (const r of rs) {
				if (!reqMap.has(r.requirement_urn)) reqMap.set(r.requirement_urn, []);
				reqMap.get(r.requirement_urn)!.push(r);
			}
			const requirements = [...reqMap.entries()]
				.map(([reqUrn, rs2]) => ({
					urn: reqUrn,
					ref_id: rs2[0].requirement_ref_id ?? '',
					name: rs2[0].requirement_name ?? '',
					ca_count: rs2.length,
					dist: distribution(rs2),
					avg_score: avgScore(rs2),
					rows: rs2
				}))
				.sort((a, b) => a.ref_id.localeCompare(b.ref_id, undefined, { numeric: true }));

			result.push({
				urn,
				ref,
				name,
				row_count: rs.length,
				requirement_count: requirements.length,
				dist: distribution(rs),
				avg_score: avgScore(rs),
				requirements
			});
		};

		// First, sections that are known non-assessable nodes (in framework section order)
		for (const s of sectionList) {
			const rs = byParent.get(s.urn);
			if (!rs || rs.length === 0) continue;
			pushSection(s.urn, s.ref_id ?? '', s.name ?? s.urn, rs);
			seen.add(s.urn);
		}

		// Then, orphan parents (rows whose parent_urn isn't a known section)
		const orphans: ReportRow[] = [];
		for (const [key, rs] of byParent) {
			if (key === '__root__') {
				orphans.push(...rs);
				continue;
			}
			if (seen.has(key)) continue;
			orphans.push(...rs);
		}
		if (orphans.length > 0) {
			pushSection('__top__', '—', m.topLevel(), orphans);
		}

		return result;
	});

	// True when the framework has no real (non-assessable) section nodes, so
	// every requirement lands in the synthetic "__top__" bucket. We then skip
	// the wrapper section row and the Expand/Collapse-all controls — they'd
	// just add a redundant click and noise.
	let isFlat = $derived(hierarchical.length === 1 && hierarchical[0]?.urn === '__top__');

	// Per-domain rollup at chosen ancestry depth
	let perDomain = $derived.by(() => {
		const map = new Map<string, ReportRow[]>();
		for (const r of filteredRows) {
			const path = r.folder_path ?? [];
			const key = path.slice(0, domainDepth).join(' / ') || '(no folder)';
			if (!map.has(key)) map.set(key, []);
			map.get(key)!.push(r);
		}

		const entries = [...map.entries()].map(([key, rs]) => {
			const dist = distribution(rs);
			return {
				key,
				ca_count: new Set(rs.map((r) => r.compliance_assessment_id)).size,
				row_count: rs.length,
				dist,
				avg_score: avgScore(rs),
				compliance: compliancePct(dist)
			};
		});

		// Null metrics always sort to the bottom regardless of direction —
		// they represent "no measurable data" and shouldn't move with toggles.
		const compareNumeric = (a: number | null, b: number | null) => {
			if (a === null && b === null) return 0;
			if (a === null) return 1;
			if (b === null) return -1;
			return domainSortDir === 'asc' ? a - b : b - a;
		};

		entries.sort((a, b) => {
			if (domainSortKey === 'name') {
				const cmp = a.key.localeCompare(b.key);
				return domainSortDir === 'asc' ? cmp : -cmp;
			}
			if (domainSortKey === 'compliance') return compareNumeric(a.compliance, b.compliance);
			return compareNumeric(a.avg_score, b.avg_score);
		});

		return entries;
	});

	let overallDist = $derived(distribution(filteredRows));
	let overallScore = $derived(avgScore(filteredRows));
	let overallCompliance = $derived(compliancePct(overallDist));
	let totalCAs = $derived(new Set(filteredRows.map((r) => r.compliance_assessment_id)).size);
	let totalAssessments = $derived(filteredRows.length);
	let maxFolderDepth = $derived.by(() => {
		let m = 1;
		for (const r of filteredRows) m = Math.max(m, r.folder_path?.length ?? 0);
		return Math.max(m, 1);
	});
</script>

<div class="space-y-4 p-2">
	<!-- Header card -->
	<div class="card p-4 bg-white">
		<div class="flex items-start justify-between gap-4 flex-wrap">
			<div>
				<div class="text-xs uppercase tracking-wide text-gray-500">{m.frameworkReport()}</div>
				<h1 class="text-xl font-semibold">{framework.name}</h1>
				<div class="text-sm text-gray-600 mt-1">
					{m.frameworkReportSubtitle({
						min: framework.min_score ?? '—',
						max: framework.max_score ?? '—',
						nIGs: igDefs.length
					})}
				</div>
				<div class="text-xs text-gray-500 mt-1">
					{m.onlyLiveStatusesCounted({
						statuses: liveStatuses.map((s) => safeTranslate(s)).join(', '),
						deprecated: m.deprecated()
					})}
				</div>
				{#if totalDetectedCAs > 0}
					<div class="text-xs text-gray-600 mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
						<span>
							{m.detectedComplianceAssessments({
								total: totalDetectedCAs,
								counted: countedCAs,
								excluded: excludedCAs
							})}
						</span>
						{#each orderedStatusCounts as [s, n]}
							{@const isLive = liveStatuses.includes(s)}
							<span
								class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 border text-[11px] {isLive
									? 'border-emerald-300 bg-emerald-50 text-emerald-800'
									: 'border-gray-300 bg-gray-50 text-gray-500'}"
								title={isLive ? m.countedInReport() : m.excludedFromReport()}
							>
								<span>{safeTranslate(s)}</span>
								<span class="font-semibold">{n}</span>
							</span>
						{/each}
						<button
							type="button"
							class="text-[11px] underline text-gray-600 hover:text-gray-900"
							onclick={() => (showCAList = !showCAList)}
							aria-expanded={showCAList}
						>
							{showCAList ? m.hideList() : m.showList()}
						</button>
					</div>

					{#if showCAList}
						<div class="mt-2 border rounded bg-gray-50 max-h-72 overflow-auto">
							<table class="w-full text-xs">
								<thead class="bg-gray-100 sticky top-0">
									<tr class="text-left">
										<th class="px-3 py-1.5 w-6"></th>
										<th class="px-3 py-1.5">{m.assessment()}</th>
										<th class="px-3 py-1.5 w-32">{m.status()}</th>
										<th class="px-3 py-1.5">{m.domain()}</th>
									</tr>
								</thead>
								<tbody>
									{#each complianceAssessments as ca}
										<tr class="border-t {ca.is_counted ? '' : 'bg-gray-100/60 text-gray-500'}">
											<td class="px-3 py-1 text-center">
												<span
													class="inline-block w-2 h-2 rounded-full {ca.is_counted
														? 'bg-emerald-500'
														: 'bg-gray-300'}"
													title={ca.is_counted ? m.countedInReport() : m.excludedFromReport()}
												></span>
											</td>
											<td class="px-3 py-1">
												<a class="anchor" href="/compliance-assessments/{ca.id}">{ca.name}</a>
											</td>
											<td class="px-3 py-1 text-[11px]">{safeTranslate(ca.status ?? 'unknown')}</td>
											<td class="px-3 py-1 font-mono text-[11px]">{ca.folder_path_str || '—'}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				{:else}
					<div class="text-xs text-gray-500 mt-1 italic">
						{m.noVisibleComplianceAssessments()}
					</div>
				{/if}
				<div class="text-xs text-gray-400 mt-1">
					{m.generatedLabel()}
					{formatDate(new Date(report.generated_at), true, getLocale())}
				</div>
			</div>
			<div class="flex gap-2 items-center">
				<a class="btn variant-ghost-surface text-sm" href="/frameworks/{framework.id}"
					>{m.backToFramework()}</a
				>
			</div>
		</div>

		<!-- KPI row -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
			<div class="rounded border p-3">
				<div class="text-xs text-gray-500">{m.compliancePercentage()}</div>
				<div class="text-2xl font-semibold">
					{overallCompliance === null ? '—' : `${overallCompliance.toFixed(1)}%`}
				</div>
				<div class="text-xs text-gray-500">{m.complianceFormulaShort()}</div>
			</div>
			<div class="rounded border p-3">
				<div class="text-xs text-gray-500">{m.averageImplementationScore()}</div>
				<div class="text-2xl font-semibold">
					{overallScore === null ? '—' : overallScore.toFixed(1)}
				</div>
				<div class="text-xs text-gray-500">{m.overScoredRequirementsOnly()}</div>
			</div>
			<div class="rounded border p-3">
				<div class="text-xs text-gray-500">{m.complianceAssessments()}</div>
				<div class="text-2xl font-semibold">{totalCAs}</div>
				<div class="text-xs text-gray-500">{m.visibleToCurrentUser()}</div>
			</div>
			<div class="rounded border p-3">
				<div class="text-xs text-gray-500">{m.requirementAssessments()}</div>
				<div class="text-2xl font-semibold">{totalAssessments}</div>
				<div class="text-xs text-gray-500">{m.inScopeAfterIGFilter()}</div>
			</div>
		</div>

		<!-- Overall distribution -->
		{#if totalAssessments > 0}
			<div class="mt-4">
				<div class="text-xs text-gray-500 mb-1">{m.overallResultDistribution()}</div>
				<div class="flex h-6 w-full rounded overflow-hidden border">
					{#each RESULT_ORDER as r}
						{@const w =
							distTotal(overallDist) === 0 ? 0 : (overallDist[r] / distTotal(overallDist)) * 100}
						{#if w > 0}
							<div
								class="h-full flex items-center justify-center text-[10px] text-gray-800"
								style="width:{w}%; background:{RESULT_COLORS[r]};"
								title="{resultLabel(r)}: {overallDist[r]}"
							>
								{overallDist[r] > 0 && w > 6 ? overallDist[r] : ''}
							</div>
						{/if}
					{/each}
				</div>
				<div class="flex gap-3 flex-wrap mt-2 text-xs">
					{#each RESULT_ORDER as r}
						<span class="inline-flex items-center gap-1">
							<span
								class="inline-block w-3 h-3 rounded-sm border"
								style="background:{RESULT_COLORS[r]};"
							></span>
							{resultLabel(r)} ({overallDist[r]})
						</span>
					{/each}
				</div>
			</div>
		{:else}
			<div class="mt-4 text-sm text-gray-500 italic">
				{m.noVisibleComplianceAssessments()}
			</div>
		{/if}
	</div>

	<!-- Filter + view bar -->
	<div class="card p-3 bg-white flex flex-wrap items-end gap-4">
		<div>
			<label class="text-xs text-gray-500 block" for="ig-filter">{m.implementationGroup()}</label>
			<select
				id="ig-filter"
				value={igFilter}
				onchange={onIGChange}
				class="rounded-lg border-gray-300 text-gray-700 text-sm bg-white"
			>
				<option value="all">{m.allGroupsHonorCASelection()}</option>
				{#each igDefs as ig}
					{@const key = igKey(ig)}
					{#if key}
						<option value={key}>{ig.name} ({key})</option>
					{/if}
				{/each}
			</select>
		</div>

		<div>
			<label class="text-xs text-gray-500 block">{m.view()}</label>
			<div class="inline-flex rounded border overflow-hidden">
				{#each [['requirement', m.requirementsTree()], ['domain', m.perDomainView()]] as [k, label]}
					<button
						type="button"
						class="px-3 py-1 text-sm {view === k
							? 'bg-primary-500 text-white'
							: 'bg-white hover:bg-gray-50'}"
						onclick={() => (view = k as typeof view)}
					>
						{label}
					</button>
				{/each}
			</div>
		</div>

		{#if view === 'requirement' && !isFlat}
			<div>
				<div class="text-xs text-gray-500 block">{m.sections()}</div>
				<div class="inline-flex gap-2">
					<button
						type="button"
						class="px-2 py-1 text-xs border rounded hover:bg-gray-50"
						onclick={() => expandAllSections(hierarchical.map((s) => s.urn))}
					>
						{m.expandAll()}
					</button>
					<button
						type="button"
						class="px-2 py-1 text-xs border rounded hover:bg-gray-50"
						onclick={collapseAllSections}
					>
						{m.collapseAll()}
					</button>
				</div>
			</div>
		{/if}

		{#if view === 'domain'}
			<div>
				<label class="text-xs text-gray-500 block" for="depth">{m.groupByFolderDepth()}</label>
				<select
					id="depth"
					bind:value={domainDepth}
					class="rounded-lg border-gray-300 text-gray-700 text-sm bg-white"
				>
					{#each Array(maxFolderDepth) as _, i}
						<option value={i + 1}
							>{i + 1}
							{i === 0
								? '— ' + m.rootDomain()
								: i === maxFolderDepth - 1
									? '— ' + m.leafFolder()
									: ''}</option
						>
					{/each}
				</select>
			</div>

			<div>
				<label class="text-xs text-gray-500 block" for="domain-sort">{m.sortBy()}</label>
				<div class="inline-flex items-center gap-1">
					<select
						id="domain-sort"
						value={domainSortKey}
						onchange={(e) =>
							setDomainSortKey(
								(e.currentTarget as HTMLSelectElement).value as typeof domainSortKey
							)}
						class="rounded-lg border-gray-300 text-gray-700 text-sm bg-white"
					>
						<option value="name">{m.domainAlphabetical()}</option>
						<option value="compliance">{m.compliancePercentage()}</option>
						<option value="score">{m.avgScore()}</option>
					</select>
					<button
						type="button"
						class="border rounded px-2 py-1 text-xs hover:bg-gray-50"
						onclick={toggleDomainSortDir}
						title={domainSortDir === 'asc' ? m.sortAscending() : m.sortDescending()}
						aria-label={m.toggleSortDirection()}
					>
						{domainSortDir === 'asc' ? '▲' : '▼'}
					</button>
				</div>
			</div>
		{/if}

		<div class="ml-auto text-xs text-gray-500">
			{filteredRows.length}
			{m.rowsLabel()}{#if view === 'requirement'}
				· {m.clickRowToDrillDown()}{/if}
		</div>
	</div>

	<!-- Main view -->
	<div class="card bg-white overflow-x-auto">
		{#if filteredRows.length === 0}
			<div class="p-6 text-sm text-gray-500 italic">{m.noRequirementAssessmentsInScope()}</div>
		{:else if view === 'requirement'}
			<table class="w-full text-sm">
				<thead class="bg-gray-50 text-left">
					<tr>
						<th class="px-3 py-2 w-32">{m.refLabel()}</th>
						<th class="px-3 py-2">{m.sectionOrRequirement()}</th>
						<th class="px-3 py-2 w-24 text-center">{m.coverage()}</th>
						<th class="px-3 py-2 w-[24%]">{m.resultDistribution()}</th>
						<th class="px-3 py-2 w-24 text-right" title={m.complianceFormulaShort()}
							>{m.compliancePercentage()}</th
						>
						<th class="px-3 py-2 w-24 text-right">{m.avgScore()}</th>
					</tr>
				</thead>
				<tbody>
					{#each hierarchical as section}
						{@const sectionCompliance = compliancePct(section.dist)}
						{#if !isFlat}
							<tr
								class="border-t bg-gray-100 font-medium hover:bg-gray-200 cursor-pointer"
								onclick={() => toggleSection(section.urn)}
							>
								<td class="px-3 py-2 font-mono text-xs">
									<span class="inline-block w-3 text-gray-500"
										>{expandedSections.has(section.urn) ? '▾' : '▸'}</span
									>
									{section.ref}
								</td>
								<td class="px-3 py-2">
									{section.name}
									<span class="text-xs text-gray-500 ml-2 font-normal"
										>({section.requirement_count}
										{m.reqsAbbr()} · {section.row_count}
										{m.rowsLabel()})</span
									>
								</td>
								<td class="px-3 py-2 text-center text-xs text-gray-500">—</td>
								<td class="px-3 py-2">
									{#if section.row_count > 0}
										<div class="flex h-5 w-full rounded overflow-hidden border">
											{#each RESULT_ORDER as r}
												{@const w =
													distTotal(section.dist) === 0
														? 0
														: (section.dist[r] / distTotal(section.dist)) * 100}
												{#if w > 0}
													<div
														style="width:{w}%; background:{RESULT_COLORS[r]};"
														title="{resultLabel(r)}: {section.dist[r]}"
													></div>
												{/if}
											{/each}
										</div>
									{:else}
										<span class="text-xs text-gray-400">{m.noRowsInScope()}</span>
									{/if}
								</td>
								<td class="px-3 py-2 text-right font-mono"
									>{sectionCompliance === null ? '—' : `${sectionCompliance.toFixed(0)}%`}</td
								>
								<td class="px-3 py-2 text-right font-mono"
									>{section.avg_score === null ? '—' : section.avg_score.toFixed(0)}</td
								>
							</tr>
						{/if}

						{#if isFlat || expandedSections.has(section.urn)}
							{#each section.requirements as req}
								{@const reqCompliance = compliancePct(req.dist)}
								<tr
									class="border-t hover:bg-gray-50 cursor-pointer"
									onclick={() => (expandedRow = expandedRow === req.urn ? null : req.urn)}
								>
									<td class="px-3 py-2 font-mono text-xs {isFlat ? '' : 'pl-8'}">
										<span class="inline-block w-3 text-gray-400"
											>{expandedRow === req.urn ? '▾' : '▸'}</span
										>
										{req.ref_id}
									</td>
									<td class="px-3 py-2 {isFlat ? '' : 'pl-6'}">{req.name}</td>
									<td class="px-3 py-2 text-center">{req.ca_count}</td>
									<td class="px-3 py-2">
										<div class="flex h-4 w-full rounded overflow-hidden border">
											{#each RESULT_ORDER as r}
												{@const w =
													distTotal(req.dist) === 0 ? 0 : (req.dist[r] / distTotal(req.dist)) * 100}
												{#if w > 0}
													<div
														style="width:{w}%; background:{RESULT_COLORS[r]};"
														title="{resultLabel(r)}: {req.dist[r]}"
													></div>
												{/if}
											{/each}
										</div>
									</td>
									<td class="px-3 py-2 text-right font-mono"
										>{reqCompliance === null ? '—' : `${reqCompliance.toFixed(0)}%`}</td
									>
									<td class="px-3 py-2 text-right font-mono"
										>{req.avg_score === null ? '—' : req.avg_score.toFixed(0)}</td
									>
								</tr>
								{#if expandedRow === req.urn}
									<tr class="bg-gray-50 border-t">
										<td></td>
										<td colspan="5" class="px-3 py-2">
											<div class="text-xs text-gray-600 mb-2">{m.perAssessmentBreakdown()}</div>
											<table class="w-full text-xs">
												<thead>
													<tr class="text-left text-gray-500">
														<th class="py-1">{m.domain()}</th>
														<th class="py-1">{m.assessment()}</th>
														<th class="py-1">{m.result()}</th>
														<th class="py-1 text-right">{m.score()}</th>
														<th class="py-1 text-center">{m.controls()}</th>
														<th class="py-1 text-center">{m.evidences()}</th>
													</tr>
												</thead>
												<tbody>
													{#each req.rows as row}
														{@const returnUrl = page.url.pathname + page.url.search}
														{@const evidencesTitle =
															row.indirect_evidences_count > 0
																? m.directPlusIndirectEvidences({
																		direct: row.direct_evidences_count,
																		indirect: row.indirect_evidences_count
																	})
																: m.directEvidencesOnly({ direct: row.direct_evidences_count })}
														<tr class="border-t border-gray-200">
															<td class="py-1 font-mono">{row.folder_path_str}</td>
															<td class="py-1">
																<a
																	class="anchor"
																	href="/requirement-assessments/{row.requirement_assessment_id}/edit?next={encodeURIComponent(
																		returnUrl
																	)}"
																	title={m.openRequirementAssessmentIn({
																		name: row.compliance_assessment_name
																	})}
																>
																	{row.compliance_assessment_name}
																</a>
															</td>
															<td class="py-1">
																<span class="inline-flex items-center gap-1">
																	<span
																		class="inline-block w-2 h-2 rounded-full"
																		style="background:{RESULT_COLORS[
																			(row.result as Result | null) ?? 'not_assessed'
																		]}"
																	></span>
																	{row.result ? resultLabel(row.result) : '—'}
																</span>
															</td>
															<td class="py-1 text-right font-mono">{row.score ?? '—'}</td>
															<td class="py-1 text-center">{row.applied_controls_count}</td>
															<td class="py-1 text-center" title={evidencesTitle}>
																{row.evidences_count}
																{#if row.indirect_evidences_count > 0}
																	<span class="text-[10px] text-gray-400"
																		>({row.direct_evidences_count}+{row.indirect_evidences_count})</span
																	>
																{/if}
															</td>
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
						<th class="px-3 py-2">{m.domain()} ({m.depthLabel()} {domainDepth})</th>
						<th class="px-3 py-2 w-32 text-center">{m.complianceAssessments()}</th>
						<th class="px-3 py-2 w-24 text-center capitalize-first">{m.rowsLabel()}</th>
						<th class="px-3 py-2 w-[24%]">{m.resultDistribution()}</th>
						<th class="px-3 py-2 w-24 text-right" title={m.complianceFormulaShort()}
							>{m.compliancePercentage()}</th
						>
						<th class="px-3 py-2 w-24 text-right">{m.avgScore()}</th>
					</tr>
				</thead>
				<tbody>
					{#each perDomain as d}
						{@const dCompliance = compliancePct(d.dist)}
						<tr class="border-t hover:bg-gray-50">
							<td class="px-3 py-2 font-mono">{d.key}</td>
							<td class="px-3 py-2 text-center">{d.ca_count}</td>
							<td class="px-3 py-2 text-center">{d.row_count}</td>
							<td class="px-3 py-2">
								<div class="flex h-4 w-full rounded overflow-hidden border">
									{#each RESULT_ORDER as r}
										{@const w = distTotal(d.dist) === 0 ? 0 : (d.dist[r] / distTotal(d.dist)) * 100}
										{#if w > 0}
											<div
												style="width:{w}%; background:{RESULT_COLORS[r]};"
												title="{resultLabel(r)}: {d.dist[r]}"
											></div>
										{/if}
									{/each}
								</div>
							</td>
							<td class="px-3 py-2 text-right font-mono"
								>{dCompliance === null ? '—' : `${dCompliance.toFixed(0)}%`}</td
							>
							<td class="px-3 py-2 text-right font-mono"
								>{d.avg_score === null ? '—' : d.avg_score.toFixed(0)}</td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</div>

<style>
	/*
	 * app.css globally paints `tbody > :not(:last-child) { border-color: surface }`
	 * to soften inter-row borders. That leaves the last row's border using the
	 * default gray-200, which reads as a footer separator. Extend the rule to the
	 * last row too so all rows share the same subtle border tone.
	 */
	table tbody > tr:last-child {
		border-color: var(--color-surface-100-900) !important;
	}
</style>
