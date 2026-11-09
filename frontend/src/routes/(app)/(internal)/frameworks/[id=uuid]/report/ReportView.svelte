<script lang="ts">
	import { pageTitle } from '#lib/utils/stores.js';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { m } from '#paraglide/messages.js';
	import { getLocale } from '#paraglide/runtime.js';
	import { formatDate } from '#lib/utils/datetime.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { roundScore } from '#lib/utils/helpers.js';
	import ScorePair from '#lib/components/ComplianceAssessment/ScorePair.svelte';
	import { complianceResultColorMap } from '#lib/utils/constants.js';
	import { downloadWorkbook, type Cell } from './reportExport';

	// -----------------------------------------------------------------------------
	// Types — match the backend response shape from GET /api/frameworks/{id}/report/
	// -----------------------------------------------------------------------------

	type Result =
		'not_assessed' | 'partially_compliant' | 'non_compliant' | 'compliant' | 'not_applicable';

	type InheritancePathEntry = {
		ca_id: string;
		ca_name: string;
		folder_id: string | null;
		folder_name: string | null;
		distance: number;
		result: Result | null;
		score: number | null;
		raw_score: number | null;
		is_scored: boolean;
		scale: { min: number | null; max: number | null };
	};

	type Inheritance = {
		strategy: string;
		inherited: boolean;
		effective_result: Result;
		effective_score: number | null;
		scale: { min: number | null; max: number | null };
		own: {
			result: Result | null;
			score: number | null;
			is_scored: boolean;
			scale: { min: number | null; max: number | null };
		} | null;
		source: InheritancePathEntry | null;
		path: InheritancePathEntry[];
	};

	// Implementation, documentation and maturity scores, as the audit counts them
	// (its calculation method, N/A at the target when it anchors N/A). A layer the
	// audit does not count, or the viewer may not read, is null.
	type ScoreLayers = {
		implementation_score: number | null;
		documentation_score: number | null;
		maturity_score: number | null;
	};

	// An audit's scores over its in-scope requirements, as on the audit's own page,
	// in total and per report section (keyed by section urn, or '__top__').
	type AuditScores = {
		total: ScoreLayers;
		sections: Record<string, ScoreLayers>;
	};

	type ReportRow = {
		requirement_assessment_id: string;
		requirement_urn: string;
		requirement_parent_urn: string | null;
		requirement_ref_id: string | null;
		requirement_name: string | null;
		requirement_description: string | null;
		assessable: boolean;
		implementation_groups: string[] | null;

		result: Result | null;
		extended_result: string | null;
		status: string | null;
		score: number | null;
		documentation_score: number | null;
		is_scored: boolean | null;
		scores: ScoreLayers;
		// Combined view's reading; null when the row inherits nothing.
		combined_scores: ScoreLayers | null;
		// Part of what the scores mean, so readable with them even when
		// compliance is hidden; null when the viewer may not read scores.
		not_applicable: boolean | null;

		compliance_assessment_id: string;
		compliance_assessment_name: string;
		folder_id: string | null;
		folder_path: string[];
		folder_path_str: string;

		applied_controls_count: number;
		evidences_count: number;
		direct_evidences_count: number;
		indirect_evidences_count: number;

		inheritance: Inheritance | null;
	};

	type ComplianceAssessmentSummary = {
		id: string;
		name: string;
		status: string | null;
		folder_id: string | null;
		folder_path: string[];
		folder_path_str: string;
		folder_path_ids: string[];
		eta: string | null;
		due_date: string | null;
		// Verdicts (met) and numbers (value) the viewer may read; null when none.
		outcomes: { ref_id: string; met?: boolean; value?: number }[] | null;
		is_counted: boolean;
		// Only counted audits carry scores.
		score_scale: { min: number | null; max: number | null; calculation_method: string } | null;
		result_visible: boolean;
		documentation_score_visible: boolean;
		scores: AuditScores | null;
		// Combined view's reading; null when the audit inherits nothing.
		combined_scores: AuditScores | null;
	};

	type Section = {
		urn: string;
		ref_id: string | null;
		name: string | null;
		description: string | null;
		parent_urn: string | null;
	};

	type IGDef = { id?: string; ref_id?: string; name: string };

	type OutcomeDef = {
		ref_id: string;
		kind: string | null;
		annotation: string | null;
		label: string | null;
		translations: Record<string, { annotation?: string; label?: string }>;
	};

	type Framework = {
		id: string;
		name: string;
		min_score: number | null;
		max_score: number | null;
		scores_definition: { scale?: { value: number; name: string }[] } | null;
		implementation_groups_definition: IGDef[] | null;
		outcomes_definition: OutcomeDef[];
		sections: Section[];
	};

	type ReportPayload = {
		framework: Framework;
		rows: ReportRow[];
		compliance_assessments: ComplianceAssessmentSummary[];
		ca_status_counts: Record<string, number>;
		live_statuses: string[];
		aggregation_strategy: string;
		campaign: { id: string; name: string } | null;
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
	let campaign = $derived(report.campaign ?? null);
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
		$pageTitle = campaign
			? `${campaign.name} — ${m.frameworkReport()}`
			: `${framework.name} — ${m.frameworkReport()}`;
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

	// Domain nodes picked in the filter; an audit matches when one is on its folder path.
	let selectedFolders = $state<Set<string>>(new Set());
	// Deadline window, in months from today on the chosen date; null bounds are open.
	let dateField = $state<'none' | 'eta' | 'due_date'>('none');
	let dateFromMonths = $state<number | null>(null);
	let dateToMonths = $state<number | null>(null);

	const PANELS = ['kpis', 'distribution', 'outcomes', 'table'] as const;
	type Panel = (typeof PANELS)[number];
	const PANELS_KEY = 'frameworkReport.panels';
	function loadPanels(): Set<Panel> {
		try {
			const saved = JSON.parse(localStorage.getItem(PANELS_KEY) ?? 'null');
			if (Array.isArray(saved)) return new Set(saved.filter((p) => PANELS.includes(p)));
		} catch {
			// Storage unavailable: show everything.
		}
		return new Set(PANELS);
	}
	let shownPanels = $state<Set<Panel>>(loadPanels());
	function togglePanel(panel: Panel) {
		const next = new Set(shownPanels);
		if (next.has(panel)) next.delete(panel);
		else next.add(panel);
		shownPanels = next;
		try {
			localStorage.setItem(PANELS_KEY, JSON.stringify([...next]));
		} catch {
			// Not persisted.
		}
	}
	const panelLabel: Record<Panel, () => string> = {
		kpis: () => m.keyIndicators(),
		distribution: () => m.overallResultDistribution(),
		outcomes: () => m.computedOutcomes(),
		table: () => m.detailTable()
	};
	type DomainSortKey = 'name' | 'compliance' | 'score' | 'documentation' | 'maturity';
	let domainSortKey = $state<DomainSortKey>('name');
	let domainSortDir = $state<'asc' | 'desc'>('asc');

	function setDomainSortKey(k: DomainSortKey) {
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
		const url = new URL(page.url.href);
		if (nextIG && nextIG !== 'all') url.searchParams.set('implementation_group', nextIG);
		else url.searchParams.delete('implementation_group');
		goto(url, { refreshAll: true, reset: false });
	}

	const RESULT_COLORS = complianceResultColorMap as Record<Result, string>;

	const resultLabel = (r: Result): string => safeTranslate(r);

	// Human-readable inheritance chain for a tooltip, nearest-first:
	// "Domain · Audit: Result  ←  Domain · Audit: Result"
	function pathTitle(inh: Inheritance): string {
		return inh.path
			.map(
				(e) => `${e.folder_name ?? '—'} · ${e.ca_name}: ${e.result ? safeTranslate(e.result) : '—'}`
			)
			.join('  ←  ');
	}

	const RESULT_ORDER: Result[] = [
		'compliant',
		'partially_compliant',
		'non_compliant',
		'not_applicable',
		'not_assessed'
	];

	// Audits whose compliance the viewer reads. A score-only audit (CyFun) hides
	// it: its rows would only add "not assessed" to the distribution.
	let resultVisibleAuditIds = $derived(
		new Set(complianceAssessments.filter((ca) => ca.result_visible).map((ca) => ca.id))
	);

	function distribution(rs: ReportRow[]): Record<Result, number> {
		const d: Record<Result, number> = {
			compliant: 0,
			partially_compliant: 0,
			non_compliant: 0,
			not_applicable: 0,
			not_assessed: 0
		};
		for (const r of rs) {
			if (!resultVisibleAuditIds.has(r.compliance_assessment_id)) continue;
			const k: Result = (r.result as Result | null) ?? 'not_assessed';
			d[k]++;
		}
		return d;
	}

	const SCORE_LAYERS = ['implementation_score', 'documentation_score', 'maturity_score'] as const;

	// Average of each layer over the entries that have it. Scores are computed
	// per audit by the backend, as on the audit's own page; across audits, the
	// report averages them, so a report over one audit shows that audit's numbers.
	function meanLayers(list: (ScoreLayers | null | undefined)[]): ScoreLayers {
		const out: ScoreLayers = {
			implementation_score: null,
			documentation_score: null,
			maturity_score: null
		};
		for (const layer of SCORE_LAYERS) {
			const values = list
				.map((s) => s?.[layer])
				.filter((v): v is number => v !== null && v !== undefined);
			out[layer] = values.length ? values.reduce((a, v) => a + v, 0) / values.length : null;
		}
		return out;
	}

	function formatScore(value: number | null): string {
		return value === null ? '—' : String(roundScore(value));
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
	// -----------------------------------------------------------------------------
	// Domain-tree inheritance overlay. When the org-wide strategy is enabled, each
	// row may carry an `inheritance` block. The "Apply domain inheritance" toggle
	// swaps each row's result/score for the effective (combined) value, so the
	// distributions, scores AND the detail cells all reflect the combined view
	// from a single transform point.
	// -----------------------------------------------------------------------------
	let aggregationStrategy = $derived<string>(report.aggregation_strategy ?? 'none');
	let inheritanceAvailable = $derived(
		aggregationStrategy !== 'none' && rows.some((r) => r.inheritance?.inherited)
	);
	let applyInheritance = $state<boolean>(true);

	function toEffective(r: ReportRow): ReportRow {
		const inh = r.inheritance;
		if (!applyInheritance || !inh || !inh.inherited) return r;
		// The inherited score as this audit counts it: none when it is on another
		// audit's scale (the overlay's own value is rescaled and rounded).
		const score = r.combined_scores ? r.combined_scores.implementation_score : inh.effective_score;
		return {
			...r,
			result: inh.effective_result,
			score,
			is_scored: score !== null,
			// Inheritance carries no documentation score.
			documentation_score: null,
			scores: r.combined_scores ?? r.scores,
			not_applicable: r.not_applicable === null ? null : inh.effective_result === 'not_applicable'
		};
	}

	let displayRows = $derived(inheritanceAvailable ? rows.map(toEffective) : rows);

	// Counted audits and the scores the current view reads for each.
	let useCombinedScores = $derived(inheritanceAvailable && applyInheritance);
	let auditScoresById = $derived(
		new Map(
			complianceAssessments
				.filter((ca) => ca.is_counted && ca.scores)
				.map((ca) => [
					ca.id,
					(useCombinedScores && ca.combined_scores) || (ca.scores as AuditScores)
				])
		)
	);
	// Documentation and maturity columns show when a counted audit has them.
	let showDocumentation = $derived(
		complianceAssessments.some((ca) => ca.is_counted && ca.documentation_score_visible)
	);
	// A lone score is just "Score"; "Implementation score" only next to a documentation score.
	let implementationLabel = $derived(showDocumentation ? m.implementationScore() : m.score());
	// Compliance distribution and percentage show when a counted audit shows
	// compliance; score-only audits (CyFun) hide it.
	let showCompliance = $derived(
		complianceAssessments.some((ca) => ca.is_counted && ca.result_visible)
	);
	// One tile per shown metric, plus the two counts (static class names for Tailwind).
	let kpiGridClass = $derived(
		{
			3: 'md:grid-cols-3',
			4: 'md:grid-cols-4',
			5: 'md:grid-cols-3 xl:grid-cols-5',
			6: 'md:grid-cols-3 xl:grid-cols-6'
		}[(showCompliance ? 1 : 0) + (showDocumentation ? 3 : 1) + 2]
	);
	// Columns of the requirement table, for the drill-down row's colspan.
	let requirementColumns = $derived(3 + (showCompliance ? 2 : 0) + (showDocumentation ? 3 : 1));

	let scaleById = $derived(
		new Map(
			complianceAssessments.filter((ca) => ca.score_scale).map((ca) => [ca.id, ca.score_scale!])
		)
	);

	// Averages scores across audits only when they mean the same thing: one
	// scale, and no sum over several audits (a sum's ceiling depends on the
	// audit's scope). Otherwise the rollup is left out (all null).
	function meanAcrossAudits(
		entries: { auditId: string; scores: ScoreLayers | null | undefined }[],
		{ sums }: { sums: boolean }
	): ScoreLayers {
		const contributing = entries.filter(
			(e) => e.scores && SCORE_LAYERS.some((layer) => e.scores![layer] !== null)
		);
		const audits = new Set(contributing.map((e) => e.auditId));
		const scales = new Set(
			[...audits].map((id) => `${scaleById.get(id)?.min}:${scaleById.get(id)?.max}`)
		);
		const summed =
			sums && [...audits].some((id) => scaleById.get(id)?.calculation_method === 'sum');
		if (scales.size > 1 || (summed && audits.size > 1)) return meanLayers([]);
		return meanLayers(contributing.map((e) => e.scores));
	}

	function auditsScores(
		auditIds: Iterable<string>,
		pick: (s: AuditScores) => ScoreLayers | undefined
	): ScoreLayers {
		return meanAcrossAudits(
			[...new Set(auditIds)].map((id) => {
				const s = auditScoresById.get(id);
				return { auditId: id, scores: s ? pick(s) : null };
			}),
			{ sums: true }
		);
	}

	type FolderNode = { id: string; name: string; depth: number; path: string };
	// Every domain on a visible audit's path, in tree order.
	let folderNodes = $derived.by(() => {
		const nodes = new Map<string, FolderNode>();
		for (const ca of complianceAssessments) {
			(ca.folder_path_ids ?? []).forEach((id, i) => {
				if (!nodes.has(id))
					nodes.set(id, {
						id,
						name: ca.folder_path[i] ?? '—',
						depth: i,
						path: ca.folder_path.slice(0, i + 1).join(' / ')
					});
			});
		}
		return [...nodes.values()].sort((a, b) => a.path.localeCompare(b.path));
	});

	function toggleFolder(id: string) {
		const next = new Set(selectedFolders);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedFolders = next;
	}

	function addMonths(months: number): Date {
		const d = new Date();
		d.setHours(0, 0, 0, 0);
		d.setMonth(d.getMonth() + months);
		return d;
	}

	function inDateWindow(ca: ComplianceAssessmentSummary): boolean {
		if (dateField === 'none' || (dateFromMonths === null && dateToMonths === null)) return true;
		const raw = ca[dateField];
		if (!raw) return false;
		const date = new Date(`${raw}T00:00:00`);
		if (dateFromMonths !== null && date < addMonths(dateFromMonths)) return false;
		if (dateToMonths !== null && date > addMonths(dateToMonths)) return false;
		return true;
	}

	let filtersActive = $derived(
		selectedFolders.size > 0 ||
			(dateField !== 'none' && (dateFromMonths !== null || dateToMonths !== null))
	);

	function resetFilters() {
		selectedFolders = new Set();
		dateField = 'none';
		dateFromMonths = null;
		dateToMonths = null;
	}

	let allowedAuditIds = $derived(
		new Set(
			complianceAssessments
				.filter(
					(ca) =>
						(selectedFolders.size === 0 ||
							(ca.folder_path_ids ?? []).some((id) => selectedFolders.has(id))) &&
						inDateWindow(ca)
				)
				.map((ca) => ca.id)
		)
	);

	let filteredRows = $derived(
		displayRows.filter(
			(r) =>
				allowedAuditIds.has(r.compliance_assessment_id) &&
				(igFilter === 'all' || (r.implementation_groups ?? []).includes(igFilter))
		)
	);

	// Hierarchical rollup: sections at the top, each carrying its child requirement rollups.
	// "Section" = the immediate parent_urn of an assessable requirement, if that parent is
	// non-assessable. If the parent_urn isn't in the framework's non-assessable nodes (e.g.
	// requirement points directly to the framework root), we bucket those into a synthetic
	// "Top level" section.
	type SectionRollup = {
		urn: string;
		ref: string;
		name: string;
		ca_count: number;
		row_count: number;
		requirement_count: number;
		dist: Record<Result, number>;
		scores: ScoreLayers;
		requirements: {
			urn: string;
			ref_id: string;
			name: string;
			ca_count: number;
			dist: Record<Result, number>;
			scores: ScoreLayers;
			rows: ReportRow[];
		}[];
	};

	function buildHierarchy(sourceRows: ReportRow[]): SectionRollup[] {
		// group rows by parent urn
		const byParent = new Map<string, ReportRow[]>();
		for (const r of sourceRows) {
			const key = r.requirement_parent_urn ?? '__root__';
			if (!byParent.has(key)) byParent.set(key, []);
			byParent.get(key)!.push(r);
		}

		// Build section descriptors in section order, falling back to "Top level"
		// for orphan parents (rows whose parent_urn isn't a known non-assessable node).
		const result: SectionRollup[] = [];

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
					name: rs2[0].requirement_name || rs2[0].requirement_description || '',
					ca_count: rs2.length,
					dist: distribution(rs2),
					// Each audit's requirement scores, N/A at the target when it anchors N/A.
					// A requirement's scores are never sums: only the scale must match.
					scores: meanAcrossAudits(
						rs2.map((r) => ({ auditId: r.compliance_assessment_id, scores: r.scores })),
						{ sums: false }
					),
					rows: rs2
				}))
				.sort((a, b) => a.ref_id.localeCompare(b.ref_id, undefined, { numeric: true }));

			result.push({
				urn,
				ref,
				name,
				ca_count: new Set(rs.map((r) => r.compliance_assessment_id)).size,
				row_count: rs.length,
				requirement_count: requirements.length,
				dist: distribution(rs),
				scores: auditsScores(
					rs.map((r) => r.compliance_assessment_id),
					(s) => s.sections[urn]
				),
				requirements
			});
		};

		// First, sections that are known non-assessable nodes (in framework section order)
		for (const s of sectionList) {
			const rs = byParent.get(s.urn);
			if (!rs || rs.length === 0) continue;
			// The ref column already identifies the section: no URN fallback.
			pushSection(s.urn, s.ref_id ?? '', s.name || s.description || '', rs);
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
	}

	let hierarchical = $derived(buildHierarchy(filteredRows));

	// True when the framework has no real (non-assessable) section nodes, so
	// every requirement lands in the synthetic "__top__" bucket. We then skip
	// the wrapper section row and the Expand/Collapse-all controls — they'd
	// just add a redundant click and noise.
	let isFlat = $derived(hierarchical.length === 1 && hierarchical[0]?.urn === '__top__');

	// Per-domain rollup at chosen ancestry depth
	function domainFolderId(row: ReportRow): string | null {
		const ids =
			complianceAssessments.find((ca) => ca.id === row.compliance_assessment_id)?.folder_path_ids ??
			[];
		return ids.length ? ids[Math.min(domainDepth, ids.length) - 1] : null;
	}

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
				scores: auditsScores(
					rs.map((r) => r.compliance_assessment_id),
					(s) => s.total
				),
				compliance: compliancePct(dist),
				rows: rs,
				folderId: domainFolderId(rs[0])
			};
		});

		const sortScore = {
			score: 'implementation_score',
			documentation: 'documentation_score',
			maturity: 'maturity_score'
		} as const;

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
			const layer = sortScore[domainSortKey];
			return compareNumeric(a.scores[layer], b.scores[layer]);
		});

		return entries;
	});

	let overallDist = $derived(distribution(filteredRows));
	let overallScores = $derived(
		auditsScores(
			filteredRows.map((r) => r.compliance_assessment_id),
			(s) => s.total
		)
	);
	let overallCompliance = $derived(compliancePct(overallDist));
	let totalCAs = $derived(new Set(filteredRows.map((r) => r.compliance_assessment_id)).size);
	let totalAssessments = $derived(filteredRows.length);
	let maxFolderDepth = $derived.by(() => {
		let m = 1;
		for (const r of filteredRows) m = Math.max(m, r.folder_path?.length ?? 0);
		return Math.max(m, 1);
	});

	// Counted audits left by the domain and deadline filters.
	let filteredAudits = $derived(
		complianceAssessments.filter((ca) => ca.is_counted && allowedAuditIds.has(ca.id))
	);

	function outcomeLabel(def: OutcomeDef): string {
		const t = def.translations?.[getLocale()];
		return t?.annotation || t?.label || def.annotation || def.label || def.ref_id;
	}

	let outcomeDefs = $derived<OutcomeDef[]>(framework.outcomes_definition ?? []);
	let outcomeRollup = $derived(
		outcomeDefs
			.map((def) => {
				const entries = filteredAudits.flatMap((ca) =>
					(ca.outcomes ?? []).filter((o) => o.ref_id === def.ref_id)
				);
				const values = entries
					.map((o) => o.value)
					.filter((v): v is number => typeof v === 'number');
				return {
					def,
					label: outcomeLabel(def),
					evaluated: entries.length,
					met: entries.filter((o) => o.met).length,
					numeric: def.kind === 'number',
					mean: values.length ? values.reduce((a, v) => a + v, 0) / values.length : null
				};
			})
			.filter((o) => o.evaluated > 0)
	);

	function metOutcomes(ca: ComplianceAssessmentSummary): string[] {
		const met = new Set((ca.outcomes ?? []).filter((o) => o.met).map((o) => o.ref_id));
		return outcomeDefs.filter((d) => met.has(d.ref_id)).map(outcomeLabel);
	}

	let showDates = $derived(complianceAssessments.some((ca) => ca.eta || ca.due_date));

	function focusDomain(folderId: string | null) {
		if (!folderId) return;
		selectedFolders = new Set([folderId]);
		view = 'requirement';
	}

	// Requirement assessments left out of a requirement's evidence export.
	let evidenceExcluded = $state<Set<string>>(new Set());
	function toggleEvidenceRow(id: string) {
		const next = new Set(evidenceExcluded);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		evidenceExcluded = next;
	}
	function evidenceAuditIds(rs: ReportRow[]): string[] {
		return [
			...new Set(
				rs
					.filter((r) => !evidenceExcluded.has(r.requirement_assessment_id))
					.map((r) => r.compliance_assessment_id)
			)
		];
	}
	function evidenceExportUrl(urn: string, rs: ReportRow[]): string {
		const params = new URLSearchParams({
			requirement: urn,
			compliance_assessments: evidenceAuditIds(rs).join(',')
		});
		return `/frameworks/${framework.id}/report/requirement-evidences?${params}`;
	}

	let exporting = $state(false);

	function onActivate(event: KeyboardEvent, action: () => void) {
		if (event.key !== 'Enter' && event.key !== ' ') return;
		event.preventDefault();
		action();
	}

	function scoreColumns(): string[] {
		return showDocumentation
			? [implementationLabel, m.documentationScore(), m.maturity()]
			: [implementationLabel];
	}
	function scoreValues(s: ScoreLayers | null | undefined): Cell[] {
		const round = (v: number | null | undefined) =>
			v === null || v === undefined ? null : roundScore(v);
		return showDocumentation
			? [round(s?.implementation_score), round(s?.documentation_score), round(s?.maturity_score)]
			: [round(s?.implementation_score)];
	}
	function complianceColumns(): string[] {
		return showCompliance
			? [m.compliancePercentage(), ...RESULT_ORDER.map((r) => resultLabel(r))]
			: [];
	}
	function complianceValues(d: Record<Result, number>): Cell[] {
		if (!showCompliance) return [];
		const pct = compliancePct(d);
		return [pct === null ? null : Math.round(pct * 10) / 10, ...RESULT_ORDER.map((r) => d[r])];
	}

	async function exportXlsx() {
		exporting = true;
		try {
			const auditColumns = [
				m.assessment(),
				m.domain(),
				m.status(),
				...(showDates ? [m.eta(), m.dueDate()] : []),
				...scoreColumns(),
				...(outcomeDefs.length ? [m.computedOutcomes()] : [])
			];
			const audits = filteredAudits.map((ca) => [
				ca.name,
				ca.folder_path_str,
				safeTranslate(ca.status ?? 'unknown'),
				...(showDates ? [ca.eta, ca.due_date] : []),
				...scoreValues(auditScoresById.get(ca.id)?.total),
				...(outcomeDefs.length ? [metOutcomes(ca).join('\n')] : [])
			]);
			const requirements = hierarchical.flatMap((section) => [
				[
					section.ref,
					section.name,
					section.ca_count,
					...complianceValues(section.dist),
					...scoreValues(section.scores)
				],
				...section.requirements.map((req) => [
					req.ref_id,
					req.name,
					req.ca_count,
					...complianceValues(req.dist),
					...scoreValues(req.scores)
				])
			]);
			const domains = perDomain.flatMap((d) => [
				[d.key, '', '', d.ca_count, ...complianceValues(d.dist), ...scoreValues(d.scores)],
				...buildHierarchy(d.rows).flatMap((section) =>
					section.requirements.map((req) => [
						d.key,
						req.ref_id,
						req.name,
						req.ca_count,
						...complianceValues(req.dist),
						...scoreValues(req.scores)
					])
				)
			]);
			const detail = filteredRows.map((r) => [
				r.folder_path_str,
				r.compliance_assessment_name,
				r.requirement_ref_id,
				r.requirement_name || r.requirement_description,
				...(showCompliance ? [r.result ? resultLabel(r.result) : null] : []),
				...scoreValues(r.scores),
				r.applied_controls_count,
				r.evidences_count
			]);
			await downloadWorkbook(`${framework.name} - ${m.frameworkReport()}.xlsx`, [
				{ name: m.complianceAssessments(), columns: auditColumns, rows: audits },
				{
					name: m.requirements(),
					columns: [
						m.refLabel(),
						m.sectionOrRequirement(),
						m.coverage(),
						...complianceColumns(),
						...scoreColumns()
					],
					rows: requirements
				},
				{
					name: m.perDomainView(),
					columns: [
						`${m.domain()} (${m.depthLabel()} ${domainDepth})`,
						m.refLabel(),
						m.requirement(),
						m.complianceAssessments(),
						...complianceColumns(),
						...scoreColumns()
					],
					rows: domains
				},
				{
					name: m.perAssessmentBreakdown(),
					columns: [
						m.domain(),
						m.assessment(),
						m.refLabel(),
						m.requirement(),
						...(showCompliance ? [m.result()] : []),
						...scoreColumns(),
						m.controls(),
						m.evidences()
					],
					rows: detail
				}
			]);
		} finally {
			exporting = false;
		}
	}
</script>

<!-- Score columns: implementation and documentation in the order of the general
     settings (ScorePair), then maturity. Documentation and maturity only show
     when a counted audit has a documentation score. -->
{#snippet scoreHeaders(cls: string)}
	<ScorePair>
		{#snippet implementation()}
			<th class={cls}>{implementationLabel}</th>
		{/snippet}
		{#snippet documentation()}
			{#if showDocumentation}
				<th class={cls}>{m.documentationScore()}</th>
			{/if}
		{/snippet}
	</ScorePair>
	{#if showDocumentation}
		<th class={cls}>{m.maturity()}</th>
	{/if}
{/snippet}

{#snippet scoreCells(scores: ScoreLayers, cls: string)}
	<ScorePair>
		{#snippet implementation()}
			<td class={cls}>{formatScore(scores.implementation_score)}</td>
		{/snippet}
		{#snippet documentation()}
			{#if showDocumentation}
				<td class={cls}>{formatScore(scores.documentation_score)}</td>
			{/if}
		{/snippet}
	</ScorePair>
	{#if showDocumentation}
		<td class={cls}>{formatScore(scores.maturity_score)}</td>
	{/if}
{/snippet}

<div class="space-y-4 p-2">
	<!-- Header card -->
	<div class="card p-4 bg-surface-50-950">
		<div class="flex items-start justify-between gap-4 flex-wrap">
			<div>
				<div class="text-xs uppercase tracking-wide text-surface-600-400">
					{m.frameworkReport()}
				</div>
				<h1 class="text-xl font-semibold">{framework.name}</h1>
				{#if campaign}
					<a
						href="/campaigns/{campaign.id}"
						class="badge preset-tonal-secondary text-xs mt-1 inline-block hover:preset-filled-secondary-500"
					>
						<i class="fa-solid fa-bullhorn mr-1"></i>{campaign.name}
					</a>
				{/if}
				<div class="text-sm text-surface-600-400 mt-1">
					{m.frameworkReportSubtitle({
						min: framework.min_score ?? '—',
						max: framework.max_score ?? '—',
						nIGs: igDefs.length
					})}
				</div>
				<div class="text-xs text-surface-600-400 mt-1">
					{m.onlyLiveStatusesCounted({
						statuses: liveStatuses.map((s) => safeTranslate(s)).join(', '),
						deprecated: m.deprecated()
					})}
				</div>
				{#if totalDetectedCAs > 0}
					<div
						class="text-xs text-surface-600-400 mt-1 flex flex-wrap items-center gap-x-2 gap-y-1"
					>
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
									: 'border-surface-300-700 bg-surface-50-950 text-surface-600-400'}"
								title={isLive ? m.countedInReport() : m.excludedFromReport()}
							>
								<span>{safeTranslate(s)}</span>
								<span class="font-semibold">{n}</span>
							</span>
						{/each}
						<button
							type="button"
							class="text-[11px] underline text-surface-600-400 hover:text-surface-900-100"
							onclick={() => (showCAList = !showCAList)}
							aria-expanded={showCAList}
						>
							{showCAList ? m.hideList() : m.showList()}
						</button>
					</div>

					{#if showCAList}
						<div class="mt-2 border rounded bg-surface-50-950 max-h-72 overflow-auto">
							<table class="w-full text-xs">
								<thead class="bg-surface-100-900 sticky top-0">
									<tr class="text-left">
										<th class="px-3 py-1.5 w-6"></th>
										<th class="px-3 py-1.5">{m.assessment()}</th>
										<th class="px-3 py-1.5 w-32">{m.status()}</th>
										<th class="px-3 py-1.5">{m.domain()}</th>
										{#if showDates}
											<th class="px-3 py-1.5 w-28">{m.eta()}</th>
											<th class="px-3 py-1.5 w-28">{m.dueDate()}</th>
										{/if}
										{#if outcomeDefs.length}
											<th class="px-3 py-1.5">{m.computedOutcomes()}</th>
										{/if}
									</tr>
								</thead>
								<tbody>
									{#each complianceAssessments as ca}
										<tr
											class="border-t {ca.is_counted && allowedAuditIds.has(ca.id)
												? ''
												: 'bg-surface-100-900/60 text-surface-600-400'}"
										>
											<td class="px-3 py-1 text-center">
												<span
													class="inline-block w-2 h-2 rounded-full {ca.is_counted
														? 'bg-emerald-500'
														: 'bg-surface-300-700'}"
													title={ca.is_counted ? m.countedInReport() : m.excludedFromReport()}
												></span>
											</td>
											<td class="px-3 py-1">
												<a class="anchor" href="/compliance-assessments/{ca.id}">{ca.name}</a>
											</td>
											<td class="px-3 py-1 text-[11px]">{safeTranslate(ca.status ?? 'unknown')}</td>
											<td class="px-3 py-1 font-mono text-[11px]">{ca.folder_path_str || '—'}</td>
											{#if showDates}
												<td class="px-3 py-1 text-[11px]"
													>{ca.eta
														? formatDate(new Date(`${ca.eta}T00:00:00`), false, getLocale())
														: '—'}</td
												>
												<td class="px-3 py-1 text-[11px]"
													>{ca.due_date
														? formatDate(new Date(`${ca.due_date}T00:00:00`), false, getLocale())
														: '—'}</td
												>
											{/if}
											{#if outcomeDefs.length}
												<td class="px-3 py-1 text-[11px]">
													{#each metOutcomes(ca) as label}
														<span class="badge preset-tonal-success text-[10px] mr-1">{label}</span>
													{:else}
														—
													{/each}
												</td>
											{/if}
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				{:else}
					<div class="text-xs text-surface-600-400 mt-1 italic">
						{m.noVisibleComplianceAssessments()}
					</div>
				{/if}
				<div class="text-xs text-surface-500 mt-1">
					{m.generatedLabel()}
					{formatDate(new Date(report.generated_at), true, getLocale())}
				</div>
			</div>
			<div class="flex gap-2 items-center">
				<button
					type="button"
					class="btn preset-filled-primary-500 text-sm"
					onclick={exportXlsx}
					disabled={exporting || filteredRows.length === 0}
				>
					<i class="fa-solid {exporting ? 'fa-spinner fa-spin' : 'fa-file-excel'} mr-2"
					></i>{m.exportReportXlsx()}
				</button>
				<a class="btn preset-outlined-surface-500 text-sm" href="/frameworks/{framework.id}"
					>{m.backToFramework()}</a
				>
			</div>
		</div>

		<!-- KPI row -->
		{#snippet scoreTile(label: string, value: number | null)}
			<div class="rounded border p-3">
				<div class="text-xs text-surface-600-400">{label}</div>
				<div class="text-2xl font-semibold">{formatScore(value)}</div>
				<div class="text-xs text-surface-600-400">{m.frameworkReportScoreCaption()}</div>
			</div>
		{/snippet}
		{#if shownPanels.has('kpis')}
			<div class="grid grid-cols-2 gap-3 mt-4 {kpiGridClass}">
				{#if showCompliance}
					<div class="rounded border p-3">
						<div class="text-xs text-surface-600-400">{m.compliancePercentage()}</div>
						<div class="text-2xl font-semibold">
							{overallCompliance === null ? '—' : `${overallCompliance.toFixed(1)}%`}
						</div>
						<div class="text-xs text-surface-600-400">{m.complianceFormulaShort()}</div>
					</div>
				{/if}
				<ScorePair>
					{#snippet implementation()}
						{@render scoreTile(implementationLabel, overallScores.implementation_score)}
					{/snippet}
					{#snippet documentation()}
						{#if showDocumentation}
							{@render scoreTile(m.documentationScore(), overallScores.documentation_score)}
						{/if}
					{/snippet}
				</ScorePair>
				{#if showDocumentation}
					{@render scoreTile(m.maturity(), overallScores.maturity_score)}
				{/if}
				<div class="rounded border p-3">
					<div class="text-xs text-surface-600-400">{m.complianceAssessments()}</div>
					<div class="text-2xl font-semibold">{totalCAs}</div>
					<div class="text-xs text-surface-600-400">{m.visibleToCurrentUser()}</div>
				</div>
				<div class="rounded border p-3">
					<div class="text-xs text-surface-600-400">{m.requirementAssessments()}</div>
					<div class="text-2xl font-semibold">{totalAssessments}</div>
					<div class="text-xs text-surface-600-400">{m.inScopeAfterIGFilter()}</div>
				</div>
			</div>
		{/if}

		<!-- Overall distribution -->
		{#if totalAssessments > 0 && showCompliance && shownPanels.has('distribution')}
			<div class="mt-4">
				<div class="text-xs text-surface-600-400 mb-1">{m.overallResultDistribution()}</div>
				<div class="flex h-6 w-full rounded overflow-hidden border">
					{#each RESULT_ORDER as r}
						{@const w =
							distTotal(overallDist) === 0 ? 0 : (overallDist[r] / distTotal(overallDist)) * 100}
						{#if w > 0}
							<div
								class="h-full flex items-center justify-center text-[10px] {r === 'not_applicable'
									? 'text-white'
									: 'text-gray-800'}"
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
		{:else if totalAssessments === 0}
			<div class="mt-4 text-sm text-surface-600-400 italic">
				{m.noVisibleComplianceAssessments()}
			</div>
		{/if}
	</div>

	{#if shownPanels.has('outcomes') && outcomeRollup.length > 0}
		<div class="card p-4 bg-surface-50-950">
			<h2 class="text-sm font-semibold mb-2">{m.computedOutcomes()}</h2>
			<ul class="space-y-2">
				{#each outcomeRollup as o (o.def.ref_id)}
					<li
						class="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_16rem] gap-1 md:gap-4 items-center"
					>
						<span class="text-sm">{o.label}</span>
						{#if o.numeric}
							<span class="text-sm font-mono text-right">
								{o.mean === null ? '—' : roundScore(o.mean)}
								<span class="text-xs text-surface-600-400"
									>({m.averageOverAudits({ count: o.evaluated })})</span
								>
							</span>
						{:else}
							<div class="flex items-center gap-2">
								<div
									class="flex-1 h-3 rounded overflow-hidden border bg-surface-100-900"
									role="img"
									aria-label={m.outcomeMetCount({ met: o.met, total: o.evaluated })}
								>
									<div
										class="h-full bg-success-500"
										style="width:{(o.met / o.evaluated) * 100}%"
									></div>
								</div>
								<span class="text-xs font-mono w-16 text-right">{o.met} / {o.evaluated}</span>
							</div>
						{/if}
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<!-- Domain and deadline filters, shown panels -->
	<div class="card p-3 bg-surface-50-950 flex flex-wrap items-end gap-4">
		<details class="relative">
			<summary
				class="cursor-pointer list-none rounded-lg border border-surface-300-700 px-3 py-1.5 text-sm"
			>
				<i class="fa-solid fa-sitemap mr-1"></i>{m.domains()}
				{#if selectedFolders.size > 0}
					<span class="badge preset-filled-primary-500 ml-1">{selectedFolders.size}</span>
				{/if}
			</summary>
			<fieldset
				class="absolute z-20 mt-1 w-96 max-w-[90vw] max-h-80 overflow-auto rounded border bg-surface-50-950 p-2 shadow-lg"
			>
				<legend class="sr-only">{m.domains()}</legend>
				{#each folderNodes as node (node.id)}
					<label
						class="flex items-center gap-2 py-0.5 text-sm cursor-pointer"
						style="padding-left:{node.depth}rem"
					>
						<input
							type="checkbox"
							class="checkbox"
							checked={selectedFolders.has(node.id)}
							onchange={() => toggleFolder(node.id)}
						/>
						<span class="truncate" title={node.path}>{node.name}</span>
					</label>
				{/each}
			</fieldset>
		</details>

		<div>
			<label class="text-xs text-surface-600-400 block" for="date-field">{m.deadline()}</label>
			<select
				id="date-field"
				bind:value={dateField}
				class="rounded-lg border-surface-300-700 text-surface-700-300 text-sm bg-surface-50-950"
			>
				<option value="none">{m.noDeadlineFilter()}</option>
				<option value="eta">{m.eta()}</option>
				<option value="due_date">{m.dueDate()}</option>
			</select>
		</div>
		{#if dateField !== 'none'}
			<div>
				<span class="text-xs text-surface-600-400 block" id="date-window-label"
					>{m.deadlineWindowMonths()}</span
				>
				<div
					class="inline-flex items-center gap-1 text-sm"
					role="group"
					aria-labelledby="date-window-label"
				>
					<label class="sr-only" for="date-from">{m.fromMonths()}</label>
					<input
						id="date-from"
						type="number"
						class="input w-20 py-1"
						placeholder={m.fromMonths()}
						value={dateFromMonths ?? ''}
						oninput={(e) => {
							const v = (e.currentTarget as HTMLInputElement).value;
							dateFromMonths = v === '' ? null : Number(v);
						}}
					/>
					<span aria-hidden="true">→</span>
					<label class="sr-only" for="date-to">{m.toMonths()}</label>
					<input
						id="date-to"
						type="number"
						class="input w-20 py-1"
						placeholder={m.toMonths()}
						value={dateToMonths ?? ''}
						oninput={(e) => {
							const v = (e.currentTarget as HTMLInputElement).value;
							dateToMonths = v === '' ? null : Number(v);
						}}
					/>
					<span class="text-xs text-surface-600-400">{m.monthsFromToday()}</span>
				</div>
			</div>
		{/if}

		{#if filtersActive}
			<button type="button" class="btn preset-outlined-surface-500 text-xs" onclick={resetFilters}>
				<i class="fa-solid fa-xmark mr-1"></i>{m.resetFilters()}
			</button>
		{/if}

		<fieldset class="ml-auto">
			<legend class="text-xs text-surface-600-400">{m.display()}</legend>
			<div class="flex flex-wrap gap-3">
				{#each PANELS as panel}
					<label class="inline-flex items-center gap-1 text-sm cursor-pointer">
						<input
							type="checkbox"
							class="checkbox"
							checked={shownPanels.has(panel)}
							onchange={() => togglePanel(panel)}
						/>
						{panelLabel[panel]()}
					</label>
				{/each}
			</div>
		</fieldset>
	</div>

	{#if shownPanels.has('table')}
		<!-- Filter + view bar -->
		<div class="card p-3 bg-surface-50-950 flex flex-wrap items-end gap-4">
			<div>
				<label class="text-xs text-surface-600-400 block" for="ig-filter"
					>{m.implementationGroup()}</label
				>
				<select
					id="ig-filter"
					value={igFilter}
					onchange={onIGChange}
					class="rounded-lg border-surface-300-700 text-surface-700-300 text-sm bg-surface-50-950"
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
				<span class="text-xs text-surface-600-400 block" id="view-label">{m.view()}</span>
				<div
					class="inline-flex rounded border overflow-hidden"
					role="group"
					aria-labelledby="view-label"
				>
					{#each [['requirement', m.requirementsTree()], ['domain', m.perDomainView()]] as [k, label]}
						<button
							type="button"
							class="px-3 py-1 text-sm {view === k
								? 'bg-primary-500 text-white'
								: 'bg-surface-50-950 hover:bg-surface-50-950'}"
							aria-pressed={view === k}
							onclick={() => (view = k as typeof view)}
						>
							{label}
						</button>
					{/each}
				</div>
			</div>

			{#if inheritanceAvailable}
				<div>
					<label class="text-xs text-surface-600-400 block" for="apply-inheritance"
						>{m.combinedView()}</label
					>
					<label class="inline-flex items-center gap-2 text-sm cursor-pointer h-[34px]">
						<input
							id="apply-inheritance"
							type="checkbox"
							class="checkbox"
							bind:checked={applyInheritance}
						/>
						{m.applyDomainInheritance()}
					</label>
				</div>
			{/if}

			{#if view === 'requirement' && !isFlat}
				<div>
					<div class="text-xs text-surface-600-400 block">{m.sections()}</div>
					<div class="inline-flex gap-2">
						<button
							type="button"
							class="px-2 py-1 text-xs border rounded hover:bg-surface-50-950"
							onclick={() => expandAllSections(hierarchical.map((s) => s.urn))}
						>
							{m.expandAll()}
						</button>
						<button
							type="button"
							class="px-2 py-1 text-xs border rounded hover:bg-surface-50-950"
							onclick={collapseAllSections}
						>
							{m.collapseAll()}
						</button>
					</div>
				</div>
			{/if}

			{#if view === 'domain'}
				<div>
					<label class="text-xs text-surface-600-400 block" for="depth"
						>{m.groupByFolderDepth()}</label
					>
					<select
						id="depth"
						bind:value={domainDepth}
						class="rounded-lg border-surface-300-700 text-surface-700-300 text-sm bg-surface-50-950"
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
					<label class="text-xs text-surface-600-400 block" for="domain-sort">{m.sortBy()}</label>
					<div class="inline-flex items-center gap-1">
						<select
							id="domain-sort"
							value={domainSortKey}
							onchange={(e) =>
								setDomainSortKey(
									(e.currentTarget as HTMLSelectElement).value as typeof domainSortKey
								)}
							class="rounded-lg border-surface-300-700 text-surface-700-300 text-sm bg-surface-50-950"
						>
							<option value="name">{m.domainAlphabetical()}</option>
							{#if showCompliance}
								<option value="compliance">{m.compliancePercentage()}</option>
							{/if}
							<ScorePair>
								{#snippet implementation()}
									<option value="score">{implementationLabel}</option>
								{/snippet}
								{#snippet documentation()}
									{#if showDocumentation}
										<option value="documentation">{m.documentationScore()}</option>
									{/if}
								{/snippet}
							</ScorePair>
							{#if showDocumentation}
								<option value="maturity">{m.maturity()}</option>
							{/if}
						</select>
						<button
							type="button"
							class="border rounded px-2 py-1 text-xs hover:bg-surface-50-950"
							onclick={toggleDomainSortDir}
							title={domainSortDir === 'asc' ? m.sortAscending() : m.sortDescending()}
							aria-label={m.toggleSortDirection()}
						>
							{domainSortDir === 'asc' ? '▲' : '▼'}
						</button>
					</div>
				</div>
			{/if}

			<div class="ml-auto text-xs text-surface-600-400">
				{filteredRows.length}
				{m.rowsLabel()}{#if view === 'requirement'}
					· {m.clickRowToDrillDown()}{/if}
			</div>
		</div>

		<!-- Main view -->
		<div class="card bg-surface-50-950 overflow-x-auto">
			{#if filteredRows.length === 0}
				<div class="p-6 text-sm text-surface-600-400 italic">
					{m.noRequirementAssessmentsInScope()}
				</div>
			{:else if view === 'requirement'}
				<table class="w-full text-sm">
					<thead class="bg-surface-50-950 text-left">
						<tr>
							<th class="px-3 py-2 w-32">{m.refLabel()}</th>
							<th class="px-3 py-2">{m.sectionOrRequirement()}</th>
							<th class="px-3 py-2 w-24 text-center">{m.coverage()}</th>
							{#if showCompliance}
								<th class="px-3 py-2 w-[24%]">{m.resultDistribution()}</th>
								<th class="px-3 py-2 w-24 text-right" title={m.complianceFormulaShort()}
									>{m.compliancePercentage()}</th
								>
							{/if}
							{@render scoreHeaders('px-3 py-2 w-24 text-right')}
						</tr>
					</thead>
					<tbody>
						{#each hierarchical as section}
							{@const sectionCompliance = compliancePct(section.dist)}
							{#if !isFlat}
								<tr
									class="border-t bg-surface-100-900 font-medium hover:bg-surface-200-800 cursor-pointer"
									tabindex="0"
									aria-expanded={expandedSections.has(section.urn)}
									onclick={() => toggleSection(section.urn)}
									onkeydown={(e) => onActivate(e, () => toggleSection(section.urn))}
								>
									<td class="px-3 py-2 font-mono text-xs whitespace-nowrap">
										<span class="inline-block w-3 text-surface-600-400"
											>{expandedSections.has(section.urn) ? '▾' : '▸'}</span
										>
										{section.ref}
									</td>
									<td class="px-3 py-2 w-full max-w-0">
										<div class="flex items-baseline gap-2 min-w-0">
											<span class="truncate" title={section.name}>{section.name}</span>
											<span class="shrink-0 text-xs text-surface-600-400 font-normal"
												>({section.requirement_count}
												{m.reqsAbbr()}{#if section.row_count !== section.requirement_count}
													· {section.row_count} {m.rowsLabel()}{/if})</span
											>
										</div>
									</td>
									<td class="px-3 py-2 text-center">{section.ca_count}</td>
									{#if showCompliance}
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
												<span class="text-xs text-surface-500">{m.noRowsInScope()}</span>
											{/if}
										</td>
										<td class="px-3 py-2 text-right font-mono"
											>{sectionCompliance === null ? '—' : `${sectionCompliance.toFixed(0)}%`}</td
										>
									{/if}
									{@render scoreCells(section.scores, 'px-3 py-2 text-right font-mono')}
								</tr>
							{/if}

							{#if isFlat || expandedSections.has(section.urn)}
								{#each section.requirements as req}
									{@const reqCompliance = compliancePct(req.dist)}
									<tr
										class="border-t hover:bg-surface-50-950 cursor-pointer"
										tabindex="0"
										aria-expanded={expandedRow === req.urn}
										onclick={() => (expandedRow = expandedRow === req.urn ? null : req.urn)}
										onkeydown={(e) =>
											onActivate(e, () => (expandedRow = expandedRow === req.urn ? null : req.urn))}
									>
										<td
											class="px-3 py-2 font-mono text-xs whitespace-nowrap {isFlat ? '' : 'pl-8'}"
										>
											<span class="inline-block w-3 text-surface-500"
												>{expandedRow === req.urn ? '▾' : '▸'}</span
											>
											{req.ref_id}
										</td>
										<td class="px-3 py-2 max-w-0 {isFlat ? '' : 'pl-6'}">
											<span class="line-clamp-2" title={req.name}>{req.name}</span>
										</td>
										<td class="px-3 py-2 text-center">{req.ca_count}</td>
										{#if showCompliance}
											<td class="px-3 py-2">
												<div class="flex h-4 w-full rounded overflow-hidden border">
													{#each RESULT_ORDER as r}
														{@const w =
															distTotal(req.dist) === 0
																? 0
																: (req.dist[r] / distTotal(req.dist)) * 100}
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
										{/if}
										{@render scoreCells(req.scores, 'px-3 py-2 text-right font-mono')}
									</tr>
									{#if expandedRow === req.urn}
										{@const exportIds = evidenceAuditIds(req.rows)}
										<tr class="bg-surface-50-950 border-t">
											<td></td>
											<td colspan={requirementColumns - 1} class="px-3 py-2">
												<div class="flex flex-wrap items-center justify-between gap-2 mb-2">
													<span class="text-xs text-surface-600-400"
														>{m.perAssessmentBreakdown()}</span
													>
													<a
														class="btn btn-sm preset-outlined-primary-500 text-xs {exportIds.length ===
														0
															? 'pointer-events-none opacity-50'
															: ''}"
														href={evidenceExportUrl(req.urn, req.rows)}
														aria-disabled={exportIds.length === 0}
														data-sveltekit-reload
														download
													>
														<i class="fa-solid fa-file-zipper mr-1"></i>
														{m.exportRequirementEvidences({ count: exportIds.length })}
													</a>
												</div>
												<table class="w-full text-xs">
													<thead>
														<tr class="text-left text-surface-600-400">
															<th class="py-1 w-6"
																><span class="sr-only">{m.includeInEvidenceExport()}</span></th
															>
															<th class="py-1">{m.domain()}</th>
															<th class="py-1">{m.assessment()}</th>
															{#if showCompliance}
																<th class="py-1">{m.result()}</th>
															{/if}
															{@render scoreHeaders('py-1 text-right')}
															<th class="py-1 text-center">{m.controls()}</th>
															<th class="py-1 text-center">{m.evidences()}</th>
														</tr>
													</thead>
													<tbody>
														{#each req.rows as row}
															{@const returnUrl = page.url.pathname + page.url.search}
															{@const inh = row.inheritance}
															{@const showInh = applyInheritance && !!inh?.inherited}
															{@const evidencesTitle =
																row.indirect_evidences_count > 0
																	? m.directPlusIndirectEvidences({
																			direct: row.direct_evidences_count,
																			indirect: row.indirect_evidences_count
																		})
																	: m.directEvidencesOnly({ direct: row.direct_evidences_count })}
															<!-- An N/A row shows, greyed, what it counts for: the
														     target when the audit counts N/A at it, else nothing. -->
															{@const naClass = row.not_applicable ? 'text-surface-400-600' : ''}
															{@const naTitle = row.not_applicable ? m.notApplicable() : undefined}
															<tr class="border-t border-surface-200-800">
																<td class="py-1">
																	<input
																		type="checkbox"
																		class="checkbox"
																		checked={!evidenceExcluded.has(row.requirement_assessment_id)}
																		onchange={() =>
																			toggleEvidenceRow(row.requirement_assessment_id)}
																		aria-label="{m.includeInEvidenceExport()}: {row.compliance_assessment_name}"
																	/>
																</td>
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
																{#if showCompliance}
																	<td class="py-1">
																		<span class="inline-flex items-center gap-1">
																			<span
																				class="inline-block w-2 h-2 rounded-full"
																				style="background:{RESULT_COLORS[
																					(row.result as Result | null) ?? 'not_assessed'
																				]}"
																			></span>
																			{row.result ? resultLabel(row.result) : '—'}
																			{#if showInh && inh}
																				<a
																					class="anchor inline-flex items-center gap-0.5 text-xs text-surface-600-400"
																					href="/compliance-assessments/{inh.source?.ca_id}"
																					title="{m.inheritedFrom()}: {inh.source?.folder_name ??
																						'—'} · {inh.source?.ca_name}&#10;{pathTitle(inh)}"
																				>
																					<i class="fa-solid fa-code-branch text-[10px]"></i>
																					{inh.source?.ca_name}
																				</a>
																			{/if}
																		</span>
																	</td>
																{/if}
																<ScorePair>
																	{#snippet implementation()}
																		<td class="py-1 text-right font-mono {naClass}" title={naTitle}>
																			{row.not_applicable
																				? formatScore(row.scores?.implementation_score ?? null)
																				: (row.score ?? '—')}
																			{#if showInh && inh && inh.own && inh.own.result !== inh.effective_result}
																				<span
																					class="text-[10px] text-surface-500"
																					title="{m.ownResult()}: {inh.own.result
																						? resultLabel(inh.own.result)
																						: '—'}{inh.own.score !== null
																						? ` (${inh.own.score}${inh.own.scale?.max != null ? ` / ${inh.own.scale.max}` : ''})`
																						: ''}"
																				>
																					<i class="fa-solid fa-circle-info"></i>
																				</span>
																			{/if}
																		</td>
																	{/snippet}
																	{#snippet documentation()}
																		{#if showDocumentation}
																			<td
																				class="py-1 text-right font-mono {naClass}"
																				title={naTitle}
																				>{formatScore(row.scores?.documentation_score ?? null)}</td
																			>
																		{/if}
																	{/snippet}
																</ScorePair>
																{#if showDocumentation}
																	<td class="py-1 text-right font-mono {naClass}" title={naTitle}
																		>{formatScore(row.scores?.maturity_score ?? null)}</td
																	>
																{/if}
																<td class="py-1 text-center">{row.applied_controls_count}</td>
																<td class="py-1 text-center" title={evidencesTitle}>
																	{row.evidences_count}
																	{#if row.indirect_evidences_count > 0}
																		<span class="text-[10px] text-surface-500"
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
					<thead class="bg-surface-50-950 text-left">
						<tr>
							<th class="px-3 py-2">{m.domain()} ({m.depthLabel()} {domainDepth})</th>
							<th class="px-3 py-2 w-32 text-center">{m.complianceAssessments()}</th>
							<th class="px-3 py-2 w-24 text-center capitalize-first">{m.rowsLabel()}</th>
							{#if showCompliance}
								<th class="px-3 py-2 w-[24%]">{m.resultDistribution()}</th>
								<th class="px-3 py-2 w-24 text-right" title={m.complianceFormulaShort()}
									>{m.compliancePercentage()}</th
								>
							{/if}
							{@render scoreHeaders('px-3 py-2 w-24 text-right')}
						</tr>
					</thead>
					<tbody>
						{#each perDomain as d (d.key)}
							{@const dCompliance = compliancePct(d.dist)}
							<tr
								class="border-t {d.folderId ? 'hover:bg-surface-100-900 cursor-pointer' : ''}"
								tabindex={d.folderId ? 0 : undefined}
								title={d.folderId ? m.showDomainRequirements() : undefined}
								onclick={() => focusDomain(d.folderId)}
								onkeydown={(e) => onActivate(e, () => focusDomain(d.folderId))}
							>
								<td class="px-3 py-2 font-mono">{d.key}</td>
								<td class="px-3 py-2 text-center">{d.ca_count}</td>
								<td class="px-3 py-2 text-center">{d.row_count}</td>
								{#if showCompliance}
									<td class="px-3 py-2">
										<div class="flex h-4 w-full rounded overflow-hidden border">
											{#each RESULT_ORDER as r}
												{@const w =
													distTotal(d.dist) === 0 ? 0 : (d.dist[r] / distTotal(d.dist)) * 100}
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
								{/if}
								{@render scoreCells(d.scores, 'px-3 py-2 text-right font-mono')}
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		</div>
	{/if}
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
