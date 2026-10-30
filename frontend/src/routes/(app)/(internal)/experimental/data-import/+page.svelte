<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import { translateChoiceLabel } from '#lib/utils/i18n.js';
	import { canPerformAction, canPerformActionOnObject } from '#lib/utils/access-control.js';
	import { page } from '$app/state';
	import * as m from '#paraglide/messages.js';
	import FolderTreeSelect from '#lib/components/Forms/FolderTreeSelect.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const API = '/experimental/data-import/api';
	// A value the user chose to send unchanged, as opposed to one not reviewed yet ('').
	const KEEP = '__keep__';
	// Parents first, so a later step can link to records an earlier one created.
	const STEP_ORDER = [
		'Folder',
		'Perimeter',
		'User',
		'Asset',
		'Threat',
		'ReferenceControl',
		'AppliedControl',
		'Policy',
		'Evidence',
		'Vulnerability',
		'SecurityException',
		'Incident',
		'ElementaryAction',
		'Processing',
		'RiskAssessment',
		'FindingsAssessment',
		'BusinessImpactAnalysis',
		'MetricInstance',
		'CustomMetricSample',
		// An audit before the third parties, whose assessments can link it by name.
		'ComplianceAssessment',
		// Tasks last among core objects: they link assets, controls and assessments.
		'TaskTemplate',
		'TPRM'
	];

	// The data wizard's own labels for the objects it imports.
	const MODEL_LABELS: Record<string, () => string> = {
		Asset: m.assets,
		AppliedControl: m.appliedControls,
		Policy: m.policies,
		Evidence: m.evidences,
		Perimeter: m.perimeters,
		User: m.users,
		Folder: m.domains,
		ReferenceControl: m.referenceControls,
		Threat: m.threats,
		Vulnerability: m.vulnerabilities,
		SecurityException: m.securityExceptions,
		Incident: m.incidents,
		ElementaryAction: m.elementaryActions,
		Processing: m.processings,
		FindingsAssessment: m.findingsAssessment,
		RiskAssessment: m.riskAssessment,
		BusinessImpactAnalysis: m.businessImpactAnalysis,
		MetricInstance: m.metricInstances,
		CustomMetricSample: m.customMetricSamples,
		TaskTemplate: m.taskTemplates,
		ComplianceAssessment: m.complianceAssessment,
		TPRM: m.thirdPartyCategory
	};
	const modelLabel = (type: string) => MODEL_LABELS[type]?.() ?? type;

	type Choice = { value: string | number; label: string };
	type SchemaColumn = {
		key: string;
		label: string;
		aliases: string[];
		choices: Choice[] | null;
		boolean: boolean;
	};
	type Schema = {
		model_type: string;
		sheets: { name: string; model: string; columns: SchemaColumn[] }[];
	};
	type Analysed = {
		name: string;
		empty: boolean;
		header_row?: number;
		row_count?: number;
		columns?: { header: string; samples: unknown[]; distinct: string[] | null }[];
		candidates?: { model_type: string; sheet: string; score: number }[];
		target?: { model_type: string; sheet: string } | null;
		mapping?: {
			columns: Record<string, { key: string; reason: string }>;
			values: Record<string, Record<string, { value: string | number; reason: string } | null>>;
			defaults?: Record<string, string | number | boolean>;
		} | null;
		saved_mapping?: { id: string; name: string; new_columns: string[] } | null;
	};
	type SavedMapping = {
		id: string;
		name: string;
		sheets: { source: string; model_type: string; target: string }[];
		folder: { id: string } | string | null;
		use_count: number;
		last_used_at: string | null;
		created_by: { email: string } | null;
	};
	type Plan = {
		analysed: Analysed;
		include: boolean;
		headerRow: number;
		modelType: string;
		targetSheet: string;
		columns: Record<string, string>; // source header -> template column, '' = ignore
		values: Record<string, Record<string, string>>; // header -> source value -> String(choice)
		defaults: Record<string, string>; // template column -> String(value) for every row
		open: boolean;
		busy: boolean;
	};
	type RowError = { record?: Record<string, unknown>; error: string; warning?: boolean };
	type Counts = {
		created?: number;
		successful?: number;
		updated?: number;
		skipped?: number;
		failed?: number;
		stopped?: boolean;
		errors?: RowError[];
		warnings?: RowError[];
		details?: Record<string, number>;
	};
	type StepResult = {
		model_type: string;
		status: number;
		error?: string;
		results?: Counts & Record<string, unknown>;
	};
	type ResultRow = {
		label: string;
		modelType: string;
		created: number;
		updated: number;
		skipped: number;
		failed: number;
		stopped: boolean;
		error?: string;
		errors: RowError[];
		// Records created along the way, e.g. {applied_controls_created: 4}.
		details: Record<string, number>;
	};

	const toastStore = getToastStore();

	let file = $state<File | null>(null);
	let dragging = $state(false);
	let analysing = $state(false);
	let plans = $state<Plan[]>([]);
	let schemas = $state<Record<string, Schema>>({});
	let folderId = $state('');
	// FolderTreeSelect needs a SuperForm field; the domain is plain page state.
	const scopeSchema = z.object({ folder: z.string().optional() });
	const scopeForm = superForm(defaults({ folder: '' }, zod(scopeSchema)), {
		id: 'data-import-scope',
		dataType: 'json',
		taintedMessage: false,
		validators: zod(scopeSchema),
		SPA: true
	});
	let matrixId = $state('');
	// Where audit rows go: a new audit on a framework, or an existing one.
	let auditTargetId = $state('');
	let auditFrameworkId = $state('');
	let auditName = $state('');
	let onConflict = $state<'stop' | 'skip' | 'update'>('stop');
	let running = $state(false);
	let outcome = $state<{ dryRun: boolean; rows: ResultRow[] } | null>(null);
	// What the last dry run covered: Import stays off once the mapping changes.
	let dryRunKey = $state('');
	let useSaved = $state(true);
	let savedMappings = $state<SavedMapping[]>([]);
	let saveName = $state('');
	let saving = $state(false);
	let confirmDelete = $state('');

	const globalFolderId = $derived(
		data.folders.find((f: { content_type?: string }) => f.content_type === 'GLOBAL')?.id
	);
	const mayMap = (action: 'add' | 'change') =>
		canPerformAction({
			user: page.data.user,
			action,
			model: 'importmapping',
			domain: globalFolderId
		});
	const mayDelete = (saved: SavedMapping) =>
		canPerformActionOnObject({
			user: page.data.user,
			action: 'delete',
			model: 'importmapping',
			object: saved
		});

	async function loadSavedMappings() {
		const res = await fetch(`${API}/mappings`);
		if (res.ok) savedMappings = (await res.json()).results ?? [];
	}

	onMount(loadSavedMappings);

	async function loadSchema(modelType: string): Promise<Schema | undefined> {
		if (!modelType) return undefined;
		if (!schemas[modelType]) {
			const res = await fetch(`${API}/schema/${modelType}`);
			if (res.ok) schemas[modelType] = await res.json();
		}
		return schemas[modelType];
	}

	function schemaSheet(plan: Plan) {
		return schemas[plan.modelType]?.sheets.find((s) => s.name === plan.targetSheet);
	}

	function planFrom(analysed: Analysed, open = false): Plan {
		// A sheet without data rows (a readme, a cover page) has nothing to import.
		analysed = { ...analysed, empty: analysed.empty || !analysed.row_count };
		const columns: Record<string, string> = {};
		const values: Record<string, Record<string, string>> = {};
		for (const col of analysed.columns ?? []) {
			columns[col.header] = analysed.mapping?.columns[col.header]?.key ?? '';
			const suggestions = analysed.mapping?.values[col.header] ?? {};
			values[col.header] = Object.fromEntries(
				(col.distinct ?? []).map((v) => [v, suggestions[v] ? String(suggestions[v]?.value) : ''])
			);
		}
		const plan: Plan = {
			analysed,
			include: !analysed.empty && !!analysed.target,
			headerRow: analysed.header_row ?? 1,
			modelType: analysed.target?.model_type ?? '',
			targetSheet: analysed.target?.sheet ?? '',
			columns,
			values,
			defaults: Object.fromEntries(
				Object.entries(analysed.mapping?.defaults ?? {}).map(([k, v]) => [k, String(v)])
			),
			open,
			busy: false
		};
		suggestDefaults(plan);
		return plan;
	}

	const REFUSALS: Record<string, string> = {
		HeaderRowOutOfRange: 'That header row is past the end of the sheet.',
		TooManySheets: 'This file has too many sheets to analyse (30 at most).',
		TooManyColumns: 'A sheet has too many columns to analyse (100 at most).'
	};

	function refusal(body: { detail?: string | null }, fallback: string) {
		return (body.detail && REFUSALS[body.detail]) || fallback;
	}

	function remapValues(plan: Plan, header: string) {
		const field = schemaSheet(plan)?.columns.find((c) => c.key === plan.columns[header]);
		const distinct = plan.analysed.columns?.find((c) => c.header === header)?.distinct ?? [];
		const match = (raw: string) =>
			field?.choices?.find((c) =>
				[String(c.value), c.label, translateChoiceLabel(c.label, c.value)].some(
					(name) => name.toLowerCase() === raw.trim().toLowerCase()
				)
			)?.value;
		plan.values[header] = Object.fromEntries(
			distinct.map((raw) => [raw, String(match(raw) ?? '')])
		);
	}

	async function analyse(overrides: Record<string, unknown> = {}) {
		const fd = new FormData();
		fd.append('file', file as File);
		fd.append('overrides', JSON.stringify(overrides));
		fd.append('use_saved', String(useSaved));
		const res = await fetch(`${API}/analyze`, { method: 'POST', body: fd });
		const body = await res.json();
		if (!res.ok) throw new Error(refusal(body, 'Could not read this file.'));
		return body.sheets as Analysed[];
	}

	async function pick(selected: File | undefined) {
		if (!selected) return;
		file = selected;
		outcome = null;
		dryRunKey = '';
		analysing = true;
		try {
			const sheets = await analyse();
			await Promise.all(sheets.map((s) => loadSchema(s.target?.model_type ?? '')));
			plans = sheets.map((s) => planFrom(s));
			saveName =
				sheets.find((s) => s.saved_mapping)?.saved_mapping?.name ??
				selected.name.replace(/\.[^.]+$/, '');
		} catch (e) {
			toastStore.trigger({ message: e instanceof Error ? e.message : String(e) });
			file = null;
			plans = [];
		} finally {
			analysing = false;
		}
	}

	// The user changed what a sheet becomes or where its header is: ask the
	// backend for fresh suggestions for that sheet only.
	// Returns whether the sheet was re-analysed; on failure the plan is unchanged.
	async function retarget(
		index: number,
		modelType: string,
		targetSheet?: string,
		headerRow = plans[index].headerRow
	) {
		const plan = plans[index];
		const forFile = file;
		const name = plan.analysed.name;
		const schema = await loadSchema(modelType);
		if (!schema || file !== forFile) return false;
		const sheet = targetSheet ?? schema.sheets[0].name;
		plan.busy = true;
		outcome = null;
		try {
			const sheets = await analyse({
				[name]: {
					model_type: modelType,
					sheet,
					header_row: headerRow
				}
			});
			// Another file or a reset replaced the plans while this request ran.
			if (file !== forFile) return false;
			const at = plans.findIndex((p) => p.analysed.name === name);
			const fresh = sheets.find((s) => s.name === name);
			if (fresh && at !== -1) plans[at] = { ...planFrom(fresh, plan.open), include: true };
			return true;
		} catch (e) {
			toastStore.trigger({ message: e instanceof Error ? e.message : String(e) });
			plan.busy = false;
			return false;
		}
	}

	function choiceValue(plan: Plan, header: string, raw: string): string | number {
		const column = schemaSheet(plan)?.columns.find((c) => c.key === plan.columns[header]);
		return column?.choices?.find((c) => String(c.value) === raw)?.value ?? raw;
	}

	// Values every row needs that the file does not say, offered once.
	function suggestDefaults(plan: Plan) {
		const mapped = new Set(Object.values(plan.columns));
		const free = (key: string) => !mapped.has(key) && !(key in plan.defaults);
		if (mapped.has('schedule_interval') && free('schedule_frequency')) {
			// A period with no unit ("every 90") reads as days, the schedule's finest;
			// without the flag a task never schedules its occurrences.
			plan.defaults.schedule_frequency = 'DAILY';
			if (free('is_recurrent')) plan.defaults.is_recurrent = 'true';
		} else if (mapped.has('schedule_frequency') && free('schedule_interval')) {
			// "Monthly" alone means every month.
			plan.defaults.schedule_interval = '1';
			if (free('is_recurrent')) plan.defaults.is_recurrent = 'true';
		}
	}

	// Fields no column fills: the ones a same-for-every-row value can go to.
	function unmappedFields(plan: Plan) {
		const mapped = new Set(Object.values(plan.columns));
		return (schemaSheet(plan)?.columns ?? []).filter((c) => !mapped.has(c.key));
	}

	function defaultValue(column: SchemaColumn, raw: string): string | number | boolean {
		if (column.boolean) return raw === 'true';
		return column.choices?.find((c) => String(c.value) === raw)?.value ?? raw;
	}

	function buildSteps() {
		const steps: Record<
			string,
			{ model_type: string; sheets: unknown[]; options?: Record<string, string> }
		> = {};
		for (const plan of plans) {
			if (!plan.include || !plan.modelType) continue;
			const columns = Object.fromEntries(Object.entries(plan.columns).filter(([, key]) => key));
			const values: Record<string, Record<string, string | number>> = {};
			for (const header of Object.keys(columns)) {
				const mapped = Object.entries(plan.values[header] ?? {}).filter(
					([, v]) => v !== '' && v !== KEEP
				);
				if (mapped.length)
					values[header] = Object.fromEntries(
						mapped.map(([src, v]) => [src, choiceValue(plan, header, v)])
					);
			}
			const step = (steps[plan.modelType] ??= {
				model_type: plan.modelType,
				sheets: [],
				...(plan.modelType === 'ComplianceAssessment' && {
					options: auditTargetId
						? { target_id: auditTargetId }
						: { framework_id: auditFrameworkId, container_name: auditName.trim() }
				})
			});
			const defaults = Object.fromEntries(
				unmappedFields(plan)
					.filter((c) => (plan.defaults[c.key] ?? '') !== '')
					.map((c) => [c.key, defaultValue(c, plan.defaults[c.key])])
			);
			step.sheets.push({
				source: plan.analysed.name,
				target: plan.targetSheet,
				header_row: plan.headerRow,
				columns,
				values,
				defaults
			});
		}
		return Object.values(steps).sort(
			(a, b) => STEP_ORDER.indexOf(a.model_type) - STEP_ORDER.indexOf(b.model_type)
		);
	}

	function runKey() {
		return JSON.stringify([buildSteps(), folderId, matrixId, onConflict]);
	}

	async function run(dryRun: boolean) {
		const steps = buildSteps();
		const key = runKey();
		if (!steps.length) {
			toastStore.trigger({ message: 'Include at least one sheet.' });
			return;
		}
		running = true;
		try {
			const fd = new FormData();
			fd.append('file', file as File);
			fd.append('mapping', JSON.stringify({ steps }));
			fd.append(
				'options',
				JSON.stringify({
					folder_id: folderId,
					matrix_id: matrixId,
					on_conflict: onConflict,
					saved_mapping_ids: appliedSaved.map((m) => m.id)
				})
			);
			fd.append('dry_run', String(dryRun));
			const res = await fetch(`${API}/import`, { method: 'POST', body: fd });
			const body = await res.json();
			if (!res.ok) {
				toastStore.trigger({
					message: refusal(body, 'This mapping no longer fits the file: read it again.')
				});
				return;
			}
			outcome = { dryRun: body.dry_run, rows: (body.steps as StepResult[]).flatMap(resultRows) };
			dryRunKey = dryRun ? key : '';
		} catch (e) {
			toastStore.trigger({ message: e instanceof Error ? e.message : String(e) });
		} finally {
			running = false;
		}
	}

	function reset() {
		file = null;
		plans = [];
		outcome = null;
		useSaved = true;
		saveName = '';
		loadSavedMappings();
	}

	function ignoreSaved() {
		useSaved = false;
		pick(file ?? undefined);
	}

	// What a saved mapping keeps per sheet: enough to recognise the layout and
	// replay the reviewed choices.
	function savedSheets() {
		return included.map((plan) => {
			const step = buildSteps()
				.flatMap(
					(s) => s.sheets as { source: string; columns: object; values: object; defaults: object }[]
				)
				.find((sh) => sh.source === plan.analysed.name);
			return {
				source: plan.analysed.name,
				headers: (plan.analysed.columns ?? []).map((c) => c.header),
				header_row: plan.headerRow,
				model_type: plan.modelType,
				target: plan.targetSheet,
				columns: step?.columns ?? {},
				values: step?.values ?? {},
				defaults: step?.defaults ?? {}
			};
		});
	}

	function mergedSheets(updateId?: string) {
		const current = savedSheets();
		const previous = savedMappings.find((s) => s.id === updateId)?.sheets ?? [];
		return [...previous.filter((s) => !current.some((c) => c.source === s.source)), ...current];
	}

	async function saveMapping(updateId?: string) {
		const name = saveName.trim();
		if (!name) {
			toastStore.trigger({ message: 'Give the mapping a name.' });
			return;
		}
		saving = true;
		try {
			const res = await fetch(updateId ? `${API}/mappings/${updateId}` : `${API}/mappings`, {
				method: updateId ? 'PATCH' : 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name, folder: globalFolderId, sheets: mergedSheets(updateId) })
			});
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				toastStore.trigger({
					message:
						res.status === 403
							? 'You are not allowed to save mappings.'
							: `Could not save: ${JSON.stringify(body)}`
				});
				return;
			}
			toastStore.trigger({ message: `Mapping "${name}" saved.` });
			await loadSavedMappings();
		} finally {
			saving = false;
		}
	}

	async function deleteMapping(id: string) {
		const res = await fetch(`${API}/mappings/${id}`, { method: 'DELETE' });
		confirmDelete = '';
		if (!res.ok) {
			toastStore.trigger({ message: 'Could not delete this mapping.' });
			return;
		}
		await loadSavedMappings();
	}

	function matchLabel(plan: Plan, type: string) {
		const score = plan.analysed.candidates?.find((c) => c.model_type === type)?.score;
		return score === undefined ? '' : ` (${Math.round(score * 100)}% match)`;
	}

	function mappedCount(plan: Plan) {
		return Object.values(plan.columns).filter(Boolean).length;
	}

	// Values of a choice column that match none of our choices and that the
	// user has not decided about yet.
	function columnUnmatched(plan: Plan, header: string) {
		const key = plan.columns[header];
		if (!key || !schemaSheet(plan)?.columns.find((f) => f.key === key)?.choices) return 0;
		return Object.values(plan.values[header] ?? {}).filter((v) => v === '').length;
	}

	function unmatchedValues(plan: Plan) {
		return Object.keys(plan.columns).reduce((n, h) => n + columnUnmatched(plan, h), 0);
	}

	// Open the sheet's editor on the first value still to review.
	async function reviewValues(index: number) {
		plans[index].open = true;
		await tick();
		const select = document.querySelector<HTMLSelectElement>(
			`#sheet-${index} select[data-unmatched="true"]`
		);
		select?.scrollIntoView({ block: 'center', behavior: 'smooth' });
		select?.focus();
	}

	// The audit importer reports {requirement, warning} where others say {record, error}.
	function asRowError(e: RowError & { requirement?: string; warning?: unknown }): RowError {
		return {
			record: e.record ?? (e.requirement ? { ref_id: e.requirement } : undefined),
			error: String(e.error ?? e.warning ?? '')
		};
	}

	function row(label: string, modelType: string, c: Counts, error?: string): ResultRow {
		const updated = c.updated ?? 0;
		return {
			label,
			modelType,
			// Multi-sheet importers report `successful` (created + updated) instead of `created`.
			created: c.created ?? (c.successful ?? 0) - updated,
			updated,
			skipped: c.skipped ?? 0,
			failed: c.failed ?? 0,
			stopped: !!c.stopped,
			error,
			// Warnings are rows imported with something left out, such as an unknown owner.
			errors: [
				...(c.errors ?? []).map(asRowError),
				...(c.warnings ?? []).map((w) => ({ ...asRowError(w), warning: true }))
			],
			details: c.details ?? {}
		};
	}

	function resultRows(step: StepResult): ResultRow[] {
		const results = step.results ?? {};
		// Multi-sheet importers report one entry per sheet, e.g. {entities: {...}}.
		const perSheet = Object.entries(results).filter(
			([, v]) => typeof v === 'object' && v !== null && !Array.isArray(v) && 'failed' in v
		);
		if (perSheet.length) {
			return perSheet.map(([sheet, v]) =>
				row(
					`${modelLabel(step.model_type)} · ${sheet.replaceAll('_', ' ')}`,
					step.model_type,
					v as Counts
				)
			);
		}
		const error =
			step.error === 'notAllowed' ? 'You are not allowed to import these here' : step.error;
		return [row(modelLabel(step.model_type), step.model_type, results, error)];
	}

	// {applied_controls_created: 4, assets_created: 1} -> "4 applied controls, 1 asset"
	function sideEffects(details: Record<string, number>) {
		return Object.entries(details)
			.filter(([, n]) => n > 0)
			.map(([key, n]) => {
				const noun = key.replace(/_created$/, '').replaceAll('_', ' ');
				return `${n} ${n === 1 ? noun.replace(/s$/, '') : noun}`;
			})
			.join(', ');
	}

	function totals(rows: ResultRow[]) {
		const sum = { created: 0, updated: 0, skipped: 0, failed: 0 };
		for (const r of rows) {
			for (const k of Object.keys(sum) as (keyof typeof sum)[]) sum[k] += r[k];
		}
		return sum;
	}

	// "eta: Date has wrong format" reads "Due date “Q1 2027”: Date has wrong format",
	// in the words of the user's file.
	function explain(err: RowError, modelType: string) {
		const names: Record<string, string> = {};
		for (const plan of included) {
			if (plan.modelType !== modelType) continue;
			for (const [header, key] of Object.entries(plan.columns)) if (key) names[key] = header;
		}
		return err.error
			.split('; ')
			.map((part) => {
				const match = part.match(/^([a-z_]+): ([\s\S]*)$/);
				if (!match || !names[match[1]]) return part;
				const value = err.record?.[match[1]];
				// Quote the cell only when the message does not already say it.
				const shown =
					value === undefined || value === '' || match[2].includes(String(value))
						? ''
						: ` “${value}”`;
				return `${names[match[1]]}${shown}: ${match[2]}`;
			})
			.join('; ');
	}

	function recordLabel(record: Record<string, unknown> = {}) {
		const named = record.name ?? record.ref_id ?? record.email;
		if (named) return String(named);
		// Rows without a name (metric samples): their first values, e.g. "KPI-MAT · 2026-08-31".
		return Object.values(record)
			.filter((v) => v !== null && v !== '')
			.slice(0, 2)
			.join(' · ');
	}

	const included = $derived(plans.filter((p) => p.include && p.modelType));
	// Risk levels in these imports are read on a risk matrix.
	const needsAudit = $derived(included.some((p) => p.modelType === 'ComplianceAssessment'));
	const needsMatrix = $derived(
		included.some((p) => ['RiskAssessment', 'BusinessImpactAnalysis'].includes(p.modelType))
	);
	// Users live outside domains; metric samples take their instance's.
	const UNSCOPED = ['User', 'CustomMetricSample'];
	// A sheet without a domain column puts every row in the fallback domain, and
	// conflicts are looked up there: without one the dry run is meaningless.
	const needsDomain = $derived(
		!folderId &&
			included.some(
				(p) =>
					!UNSCOPED.includes(p.modelType) &&
					!Object.values(p.columns).some((key) => key === 'domain' || key === 'folder')
			)
	);
	const rowCount = $derived(included.reduce((n, p) => n + (p.analysed.row_count ?? 0), 0));
	const outcomeTotals = $derived(outcome ? totals(outcome.rows) : null);
	const canImport = $derived(!!dryRunKey && dryRunKey === runKey());
	// Saved mappings the current plan came from, once each.
	const appliedSaved = $derived([
		...new Map(
			included
				.map((p) => p.analysed.saved_mapping)
				.filter((m) => !!m)
				.map((m) => [m.id, m])
		).values()
	] as { id: string; name: string; new_columns: string[] }[]);
</script>

<div class="p-4 space-y-4">
	<header class="space-y-1">
		<h4 class="h4 font-bold flex items-center gap-2">
			<i class="fa-solid fa-file-import text-primary-500"></i>
			Data import
		</h4>
		<p class="text-sm text-surface-600-400">
			Drop any spreadsheet. We find the header row of each tab, suggest what it should become and
			how its columns and values map. Nothing is saved until you import.
		</p>
	</header>

	{#if !file}
		<label
			for="data-import-file"
			class="flex flex-col items-center justify-center gap-3 p-12 rounded-xl border-2 border-dashed text-center cursor-pointer transition-colors
				{dragging ? 'border-primary-500 bg-primary-50-950' : 'border-surface-300-700'}"
			ondragover={(e) => {
				e.preventDefault();
				dragging = true;
			}}
			ondragleave={() => (dragging = false)}
			ondrop={(e) => {
				e.preventDefault();
				dragging = false;
				pick(e.dataTransfer?.files[0]);
			}}
		>
			{#if analysing}
				<i class="fa-solid fa-spinner fa-spin text-3xl text-primary-500"></i>
				<span class="font-semibold">Reading your file…</span>
			{:else}
				<i class="fa-solid fa-cloud-arrow-up text-3xl text-primary-500"></i>
				<span class="text-lg font-semibold">Drop a file here, or click to choose</span>
				<span class="text-sm text-surface-600-400">.xlsx, .xls or .csv, up to 10 MB</span>
			{/if}
			<input
				id="data-import-file"
				type="file"
				accept=".xlsx,.xls,.csv"
				class="sr-only"
				disabled={analysing}
				onchange={(e) => pick(e.currentTarget.files?.[0])}
			/>
		</label>

		<section class="card bg-surface-50-950 border border-surface-200-800 shadow-sm p-4 space-y-3">
			<h5 class="font-semibold text-sm">Saved mappings</h5>
			{#if savedMappings.length === 0}
				<p class="text-sm text-surface-600-400">
					None yet. After a dry run, save the mapping: the next file with the same columns is mapped
					for you.
				</p>
			{:else}
				<ul class="divide-y divide-surface-200-800">
					{#each savedMappings as saved (saved.id)}
						<li class="flex flex-wrap items-center gap-x-4 gap-y-1 py-2 text-sm">
							<span class="font-medium">{saved.name}</span>
							<span class="text-surface-600-400">
								{[...new Set(saved.sheets.map((s) => s.model_type))].join(', ')} ·
								{saved.sheets.length} sheet{saved.sheets.length === 1 ? '' : 's'} ·
								{saved.use_count
									? `used ${saved.use_count} time${saved.use_count === 1 ? '' : 's'}`
									: 'never used'}
								{#if saved.created_by}· by {saved.created_by.email}{/if}
							</span>
							<span class="grow"></span>
							{#if confirmDelete === saved.id}
								<span>Delete this mapping?</span>
								<button
									type="button"
									class="btn btn-sm preset-filled-error-500"
									onclick={() => deleteMapping(saved.id)}>Delete</button
								>
								<button type="button" class="btn btn-sm" onclick={() => (confirmDelete = '')}
									>Cancel</button
								>
							{:else if mayDelete(saved)}
								<button
									type="button"
									class="btn btn-sm preset-outlined"
									aria-label="Delete {saved.name}"
									onclick={() => (confirmDelete = saved.id)}
								>
									<i class="fa-solid fa-trash"></i>
								</button>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{:else}
		<div class="flex flex-wrap items-center justify-between gap-2">
			<p class="text-sm">
				<i class="fa-solid fa-file-excel text-success-600 mr-1"></i>
				<strong>{file.name}</strong>
				<span class="text-surface-600-400">
					{#if analysing}
						· <i class="fa-solid fa-spinner fa-spin"></i> Reading the file…
					{:else}
						· {plans.length} sheet{plans.length === 1 ? '' : 's'}
					{/if}
				</span>
			</p>
			<button type="button" class="btn btn-sm preset-outlined" onclick={reset} disabled={running}>
				<i class="fa-solid fa-rotate-left mr-1"></i>Choose another file
			</button>
		</div>

		{#if appliedSaved.length}
			<div
				class="card preset-tonal-primary p-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm"
			>
				<i class="fa-solid fa-bookmark"></i>
				<span>
					Using saved mapping
					{#each appliedSaved as saved, i (saved.id)}
						{i ? ', ' : ''}<strong>{saved.name}</strong>{#if saved.new_columns.length}
							(new columns: {saved.new_columns.join(', ')}){/if}
					{/each}
				</span>
				<span class="grow"></span>
				<button type="button" class="btn btn-sm preset-outlined" onclick={ignoreSaved}>
					Ignore saved mappings
				</button>
			</div>
		{:else if !useSaved}
			<p class="text-sm text-surface-600-400">
				Saved mappings ignored for this file.
				<button
					type="button"
					class="anchor"
					onclick={() => {
						useSaved = true;
						pick(file ?? undefined);
					}}>Use them again</button
				>
			</p>
		{/if}

		<div class="space-y-3">
			{#each plans as plan, index (plan.analysed.name)}
				<section
					id="sheet-{index}"
					class="card bg-surface-50-950 border border-surface-200-800 shadow-sm"
				>
					<div class="flex flex-wrap items-center gap-x-4 gap-y-2 p-4">
						<label class="flex items-center gap-2 min-w-48">
							<input
								type="checkbox"
								class="checkbox"
								bind:checked={plan.include}
								disabled={plan.analysed.empty || !plan.modelType || running}
							/>
							<span class="font-mono font-semibold">{plan.analysed.name}</span>
						</label>

						{#if plan.analysed.empty}
							<span class="text-sm text-surface-600-400">No data rows, skipped</span>
						{:else}
							<span class="text-sm text-surface-600-400">
								{plan.analysed.row_count}
								{plan.analysed.row_count === 1 ? 'row' : 'rows'} · header on row {plan.headerRow}
							</span>
							<label class="flex items-center gap-2 text-sm">
								becomes
								<select
									class="select w-auto text-sm"
									value={plan.modelType}
									disabled={plan.busy || running}
									onchange={(e) => retarget(index, e.currentTarget.value)}
								>
									<option value="" disabled>Choose an object…</option>
									{#each data.modelTypes as type (type)}
										<option value={type}>{modelLabel(type)}{matchLabel(plan, type)}</option>
									{/each}
								</select>
							</label>
							{#if (schemas[plan.modelType]?.sheets.length ?? 0) > 1}
								<label class="flex items-center gap-2 text-sm">
									as
									<select
										class="select w-auto text-sm"
										value={plan.targetSheet}
										disabled={plan.busy || running}
										onchange={(e) => retarget(index, plan.modelType, e.currentTarget.value)}
									>
										{#each schemas[plan.modelType].sheets as sheet (sheet.name)}
											<option value={sheet.name}>{sheet.name}</option>
										{/each}
									</select>
								</label>
							{/if}
							{#if plan.modelType}
								<span class="text-sm">
									{mappedCount(plan)} of {plan.analysed.columns?.length} columns mapped
									{#if unmatchedValues(plan)}
										·
										<button
											type="button"
											class="anchor text-warning-700-300 font-medium"
											title="Values in your file that match none of the allowed choices"
											onclick={() => reviewValues(index)}
										>
											{unmatchedValues(plan)}
											{unmatchedValues(plan) === 1 ? 'value' : 'values'} to review
										</button>
									{/if}
								</span>
							{/if}
							<span class="grow"></span>
							{#if plan.busy}
								<i class="fa-solid fa-spinner fa-spin text-primary-500"></i>
							{/if}
							{#if plan.modelType}
								<button
									type="button"
									class="btn btn-sm preset-tonal"
									aria-expanded={plan.open}
									onclick={() => (plan.open = !plan.open)}
								>
									<i class="fa-solid {plan.open ? 'fa-chevron-up' : 'fa-sliders'} mr-1"></i>
									{plan.open ? 'Close' : 'Adjust'}
								</button>
							{/if}
						{/if}
					</div>

					{#if plan.open && plan.modelType && !plan.analysed.empty}
						<div class="border-t border-surface-200-800 p-4 space-y-4">
							<label class="flex items-center gap-2 text-sm w-fit">
								Header row
								<input
									type="number"
									min="1"
									class="input w-20 text-sm"
									value={plan.headerRow}
									disabled={plan.busy || running}
									onchange={async (e) => {
										const input = e.currentTarget;
										const row = Math.max(1, Number(input.value) || 1);
										if (!(await retarget(index, plan.modelType, plan.targetSheet, row)))
											input.value = String(plan.headerRow);
									}}
								/>
							</label>
							<div class="overflow-x-auto">
								<table class="table text-sm">
									<thead>
										<tr>
											<th>Your column</th>
											<th>Sample values</th>
											<th>Field</th>
										</tr>
									</thead>
									<tbody>
										{#each plan.analysed.columns ?? [] as col (col.header)}
											{@const field = schemaSheet(plan)?.columns.find(
												(c) => c.key === plan.columns[col.header]
											)}
											<tr>
												<td class="align-top">
													<span class="font-mono font-medium">{col.header}</span>
													{#if columnUnmatched(plan, col.header)}
														<span class="block text-xs text-warning-700-300">
															{columnUnmatched(plan, col.header)}
															{columnUnmatched(plan, col.header) === 1 ? 'value' : 'values'} to review
														</span>
													{/if}
												</td>
												<td class="text-surface-600-400 align-top max-w-72 truncate">
													{col.samples.slice(0, 3).join(', ')}
												</td>
												<td class="align-top">
													<select
														class="select text-sm"
														bind:value={plan.columns[col.header]}
														onchange={() => {
															remapValues(plan, col.header);
															suggestDefaults(plan);
														}}
														disabled={running}
														aria-label="Field for {col.header}"
													>
														<option value="">Ignore</option>
														{#each schemaSheet(plan)?.columns ?? [] as target (target.key)}
															<option
																value={target.key}
																disabled={target.key !== plan.columns[col.header] &&
																	Object.values(plan.columns).includes(target.key)}
															>
																{target.label} ({target.key})
															</option>
														{/each}
													</select>
													{#if field?.choices && col.distinct}
														<div class="mt-2 space-y-1">
															{#each col.distinct as value (value)}
																<label class="grid grid-cols-2 gap-2 items-center">
																	<span class="font-mono text-xs truncate">{value}</span>
																	<select
																		class="select text-xs {plan.values[col.header][value]
																			? ''
																			: 'border-2 border-warning-500 preset-tonal-warning'}"
																		data-unmatched={plan.values[col.header][value] === ''}
																		aria-label="Value for {value}"
																		bind:value={plan.values[col.header][value]}
																		disabled={running}
																	>
																		<option value="" disabled>Not matched: choose a value</option>
																		<option value={KEEP}>Keep as is (sent unchanged)</option>
																		{#each field.choices as choice (choice.value)}
																			<option value={String(choice.value)}
																				>{translateChoiceLabel(choice.label, choice.value)}</option
																			>
																		{/each}
																	</select>
																</label>
															{/each}
														</div>
													{/if}
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
							<div class="space-y-2">
								<h3 class="text-sm font-semibold">Same value for every row</h3>
								<p class="text-xs text-surface-600-400">
									For fields no column fills. In Update mode they also replace the field on existing
									records.
								</p>
								{#each unmappedFields(plan).filter((c) => c.key in plan.defaults) as column (column.key)}
									<div class="flex items-center gap-2 text-sm">
										<span class="w-56 truncate">{column.label} ({column.key})</span>
										{#if column.boolean || column.choices}
											<select
												class="select w-auto text-sm"
												bind:value={plan.defaults[column.key]}
												disabled={running}
												aria-label="Value for every row of {column.key}"
											>
												<option value="" disabled>Choose a value</option>
												{#if column.boolean}
													<option value="true">Yes</option>
													<option value="false">No</option>
												{:else}
													{#each column.choices ?? [] as choice (choice.value)}
														<option value={String(choice.value)}
															>{translateChoiceLabel(choice.label, choice.value)}</option
														>
													{/each}
												{/if}
											</select>
										{:else}
											<input
												class="input w-64 text-sm"
												bind:value={plan.defaults[column.key]}
												disabled={running}
												aria-label="Value for every row of {column.key}"
											/>
										{/if}
										<button
											type="button"
											class="btn-icon btn-icon-sm"
											onclick={() => delete plan.defaults[column.key]}
											disabled={running}
											aria-label="Remove the value for {column.key}"
										>
											<i class="fa-solid fa-xmark"></i>
										</button>
									</div>
								{/each}
								{#if unmappedFields(plan).some((c) => !(c.key in plan.defaults))}
									<select
										class="select w-auto text-sm"
										value=""
										disabled={running}
										aria-label="Add a value for every row"
										onchange={(e) => {
											plan.defaults[e.currentTarget.value] = '';
											e.currentTarget.value = '';
										}}
									>
										<option value="" disabled>Add a field…</option>
										{#each unmappedFields(plan).filter((c) => !(c.key in plan.defaults)) as column (column.key)}
											<option value={column.key}>{column.label} ({column.key})</option>
										{/each}
									</select>
								{/if}
							</div>
						</div>
					{/if}
				</section>
			{/each}
		</div>

		<section class="card bg-surface-50-950 border border-surface-200-800 shadow-sm p-4 space-y-4">
			<div class="flex flex-wrap gap-6">
				<div class="min-w-72 text-sm">
					<FolderTreeSelect
						form={scopeForm}
						field="folder"
						nullable
						required={needsDomain}
						disabled={running}
						label={m.dataWizardSelectFallbackDomain()}
						helpText={m.dataWizardFallbackDomainHelp()}
						onChange={(v) => (folderId = v ?? '')}
					/>
				</div>
				{#if needsAudit}
					<label class="space-y-1 text-sm">
						<span class="block font-medium">Audit</span>
						<select class="select text-sm" bind:value={auditTargetId} disabled={running}>
							<option value="">Create a new audit</option>
							{#each data.audits as audit (audit.id)}
								<option value={audit.id}>Update {audit.name}</option>
							{/each}
						</select>
					</label>
					{#if !auditTargetId}
						<label class="space-y-1 text-sm">
							<span class="block font-medium">Framework</span>
							<select class="select text-sm" bind:value={auditFrameworkId} disabled={running}>
								<option value="">Choose a framework…</option>
								{#each data.frameworks as framework (framework.id)}
									<option value={framework.id}>{framework.str || framework.name}</option>
								{/each}
							</select>
						</label>
						<label class="space-y-1 text-sm">
							<span class="block font-medium">Audit name</span>
							<input
								class="input text-sm"
								bind:value={auditName}
								placeholder="Third-party assessments can link it by this name"
								disabled={running}
							/>
						</label>
					{/if}
				{/if}
				{#if needsMatrix}
					<label class="space-y-1 text-sm">
						<span class="block font-medium">Risk matrix <span class="text-error-500">*</span></span>
						<select class="select text-sm" bind:value={matrixId} disabled={running} required>
							<option value="">Choose a matrix…</option>
							{#each data.matrices as matrix (matrix.id)}
								<option value={matrix.id}>{matrix.str || matrix.name}</option>
							{/each}
						</select>
					</label>
				{/if}
				<fieldset class="space-y-1 text-sm">
					<legend class="font-medium">If a record already exists</legend>
					<div class="flex gap-4 pt-1">
						{#each [['stop', 'Stop'], ['skip', 'Skip'], ['update', 'Update']] as [value, label] (value)}
							<label class="flex items-center gap-1">
								<input
									type="radio"
									class="radio"
									bind:group={onConflict}
									{value}
									disabled={running}
								/>
								{label}
							</label>
						{/each}
					</div>
				</fieldset>
			</div>
			<div class="flex flex-wrap items-center gap-3 pt-3 border-t border-surface-200-800">
				<span class="text-sm">
					{included.length} sheet{included.length === 1 ? '' : 's'} · {rowCount} rows
				</span>
				<span class="grow"></span>
				<button
					type="button"
					class="btn preset-outlined"
					onclick={() => run(true)}
					disabled={running ||
						!included.length ||
						needsDomain ||
						(needsMatrix && !matrixId) ||
						(needsAudit && !auditTargetId && !auditFrameworkId)}
					title={needsDomain ? m.dataWizardFallbackDomainHelp() : ''}
				>
					{#if running}<i class="fa-solid fa-spinner fa-spin mr-2"></i>{/if}
					Dry run
				</button>
				<button
					type="button"
					class="btn preset-filled-primary-500"
					onclick={() => run(false)}
					disabled={running || !canImport}
					title={canImport ? '' : 'Run a dry run of this mapping first'}
				>
					Import
				</button>
			</div>
		</section>

		{#if outcome && outcomeTotals}
			<section
				class="card bg-surface-50-950 border border-surface-200-800 shadow-sm p-4 space-y-4"
				aria-live="polite"
			>
				<h5 class="font-semibold">
					{outcome.dryRun ? "Dry run: here's what would happen. Nothing was saved." : 'Import done'}
				</h5>
				<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
					<div class="card p-3 preset-tonal-success">
						<div class="text-2xl font-bold">{outcomeTotals.created}</div>
						<div class="text-xs">{outcome.dryRun ? 'would be created' : 'created'}</div>
					</div>
					<div class="card p-3 preset-tonal-secondary">
						<div class="text-2xl font-bold">{outcomeTotals.updated}</div>
						<div class="text-xs">{outcome.dryRun ? 'would be updated' : 'updated'}</div>
					</div>
					<div class="card p-3 preset-tonal">
						<div class="text-2xl font-bold">{outcomeTotals.skipped}</div>
						<div class="text-xs">skipped</div>
					</div>
					<div class="card p-3 preset-tonal-error">
						<div class="text-2xl font-bold">{outcomeTotals.failed}</div>
						<div class="text-xs">failed</div>
					</div>
				</div>
				<div class="overflow-x-auto">
					<table class="table text-sm">
						<thead>
							<tr>
								<th>Object</th>
								<th>New</th>
								<th>Updated</th>
								<th>Skipped</th>
								<th>Failed</th>
							</tr>
						</thead>
						<tbody>
							{#each outcome.rows as r (r.label)}
								<tr>
									<td>
										{r.label}
										{#if r.stopped}
											<span class="badge preset-tonal-warning ml-1">stopped</span>
										{/if}
										{#if r.error}
											<span class="text-error-600-400 ml-1">{r.error}</span>
										{/if}
									</td>
									<td>{r.created}</td>
									<td>{r.updated}</td>
									<td>{r.skipped}</td>
									<td>{r.failed}</td>
								</tr>
								{#if sideEffects(r.details)}
									<tr>
										<td colspan="5" class="text-sm text-surface-600-400 pt-0">
											<i class="fa-solid fa-link mr-1"></i>
											{outcome.dryRun ? 'Would also create' : 'Also created'}
											{sideEffects(r.details)}, linked to these rows
										</td>
									</tr>
								{/if}
							{/each}
						</tbody>
					</table>
				</div>
				{#each outcome.rows.filter((r) => r.errors.length) as r (r.label)}
					<div class="space-y-1">
						<h6 class="text-sm font-semibold">{r.label}: errors and warnings</h6>
						<ul class="text-sm space-y-1">
							{#each r.errors.slice(0, 20) as err, i (i)}
								<li>
									{#if err.warning}
										<i
											class="fa-solid fa-triangle-exclamation text-warning-600-400"
											title="Imported with a warning"
										></i>
										<span class="sr-only">Warning:</span>
									{:else}
										<i class="fa-solid fa-circle-xmark text-error-600-400" title="Not imported"></i>
										<span class="sr-only">Error:</span>
									{/if}
									{#if recordLabel(err.record)}
										<span class="font-medium">{recordLabel(err.record)}:</span>
									{/if}
									<span class="text-surface-600-400">{explain(err, r.modelType)}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/each}
				{#if outcome.dryRun && canImport && (mayMap('add') || (appliedSaved.length && mayMap('change')))}
					<div class="flex flex-wrap items-end gap-3 pt-3 border-t border-surface-200-800">
						<label class="space-y-1 text-sm grow max-w-md">
							<span class="block font-medium">Save this mapping for next time</span>
							<input class="input text-sm" bind:value={saveName} disabled={saving} />
						</label>
						{#if appliedSaved.length === 1 && mayMap('change')}
							<button
								type="button"
								class="btn preset-outlined"
								disabled={saving}
								onclick={() => saveMapping(appliedSaved[0].id)}
							>
								Update “{appliedSaved[0].name}”
							</button>
						{/if}
						{#if mayMap('add')}
							<button
								type="button"
								class="btn preset-tonal-primary"
								disabled={saving}
								onclick={() => saveMapping()}
							>
								<i class="fa-solid fa-bookmark mr-1"></i>Save as new mapping
							</button>
						{/if}
					</div>
				{/if}
			</section>
		{/if}
	{/if}
</div>
