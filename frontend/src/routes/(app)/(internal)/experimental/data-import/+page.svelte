<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';
	import { prefersReducedMotion } from 'svelte/motion';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import { translateChoiceLabel } from '#lib/utils/i18n.js';
	import { canPerformAction, canPerformActionOnObject } from '#lib/utils/access-control.js';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
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
	// Where imported records of each type live.
	const LIST_PAGES: Record<string, string> = {
		Asset: 'assets',
		AppliedControl: 'applied-controls',
		Policy: 'policies',
		Evidence: 'evidences',
		Perimeter: 'perimeters',
		User: 'users',
		Folder: 'folders',
		ReferenceControl: 'reference-controls',
		Threat: 'threats',
		Vulnerability: 'vulnerabilities',
		SecurityException: 'security-exceptions',
		Incident: 'incidents',
		ElementaryAction: 'elementary-actions',
		Processing: 'processings',
		FindingsAssessment: 'findings-assessments',
		RiskAssessment: 'risk-assessments',
		BusinessImpactAnalysis: 'business-impact-analysis',
		MetricInstance: 'metric-instances',
		CustomMetricSample: 'custom-metric-samples',
		TaskTemplate: 'task-templates',
		ComplianceAssessment: 'compliance-assessments',
		TPRM: 'entities'
	};

	// The created container when the importer reports it, else the type's list page.
	function linkFor(modelType: string, results: Record<string, unknown>) {
		const study = (results.details as Record<string, unknown> | undefined)?.study;
		if (study) return { href: `ebios-rm/${study}`, label: m.dataImportOpenStudy() };
		if (results.compliance_assessment)
			return {
				href: `compliance-assessments/${results.compliance_assessment}`,
				label: m.dataImportOpenAudit()
			};
		const list = LIST_PAGES[modelType];
		return list
			? { href: list, label: m.dataImportGoTo({ model: modelLabel(modelType) }) }
			: undefined;
	}

	const modelLabel = (type: string) => MODEL_LABELS[type]?.() ?? FORMATS[type]?.label() ?? type;

	// Exports a dedicated importer reads whole, recognised by the backend.
	const FORMATS: Record<
		string,
		{ label: () => string; description: () => string; icon: string; matrix: boolean }
	> = {
		EbiosRMStudyEgerieXML: {
			label: m.ebiosRMStudyEgerieXML,
			description: m.ebiosRMStudyEgerieXMLDescription,
			icon: 'fa-file-code',
			matrix: true
		},
		EbiosRMStudyARM: {
			label: m.ebiosRMStudyARM,
			description: m.ebiosRMStudyARMDescription,
			icon: 'fa-file-zipper',
			matrix: true
		},
		EbiosRMStudyExcel: {
			label: m.ebiosRMStudyExcel,
			description: m.ebiosRMStudyExcelDescription,
			icon: 'fa-file-excel',
			matrix: true
		},
		CyFunAssessment: {
			label: m.cyFunAssessment,
			description: m.dataWizardCyFunDescription,
			icon: 'fa-file-excel',
			matrix: false
		}
	};
	const COMPANIONS: Record<string, { icon: string; text: () => string }> = {
		occurrences: { icon: 'fa-clock-rotate-left', text: m.dataImportCompanionOccurrences },
		notes: { icon: 'fa-note-sticky', text: m.dataImportCompanionNotes }
	};

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
		companion?: 'occurrences' | 'notes';
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
		link?: { href: string; label: string };
	};

	const toastStore = getToastStore();

	let file = $state<File | null>(null);
	let dragging = $state(false);
	let analysing = $state(false);
	let plans = $state<Plan[]>([]);
	// A whole-file format the backend recognised, e.g. 'EbiosRMStudyARM'.
	let format = $state('');
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
			include: !analysed.empty && !analysed.companion && !!analysed.target,
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

	const REFUSALS: Record<string, () => string> = {
		HeaderRowOutOfRange: m.dataImportRefusalHeaderRow,
		TooManySheets: m.dataImportRefusalTooManySheets,
		TooManyColumns: m.dataImportRefusalTooManyColumns,
		UnrecognisedFile: m.dataImportRefusalUnrecognised
	};

	function refusal(body: { detail?: string | null }, fallback: string) {
		return (body.detail && REFUSALS[body.detail]?.()) || fallback;
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

	async function analyse(overrides: Record<string, unknown> = {}, detectFormat = false) {
		const fd = new FormData();
		fd.append('file', file as File);
		fd.append('overrides', JSON.stringify(overrides));
		fd.append('use_saved', String(useSaved));
		fd.append('detect_format', String(detectFormat));
		const res = await fetch(`${API}/analyze`, { method: 'POST', body: fd });
		const body = await res.json();
		if (!res.ok) throw new Error(refusal(body, m.dataImportCouldNotRead()));
		if (body.format) format = body.format;
		return body.sheets as Analysed[];
	}

	// detectFormat=false reads a recognised workbook sheet by sheet instead.
	async function pick(selected: File | undefined, detectFormat = true) {
		if (!selected) return;
		file = selected;
		format = '';
		outcome = null;
		dryRunKey = '';
		analysing = true;
		try {
			const sheets = await analyse({}, detectFormat);
			await Promise.all(sheets.map((s) => loadSchema(s.target?.model_type ?? '')));
			plans = sheets.map((s) => planFrom(s));
			saveName =
				sheets.find((s) => s.saved_mapping)?.saved_mapping?.name ??
				selected.name.replace(/\.[^.]+$/, '');
		} catch (e) {
			toastStore.trigger({ message: e instanceof Error ? e.message : String(e) });
			file = null;
			format = '';
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
		if (format) return [{ model_type: format, sheets: [] as unknown[] }];
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
			toastStore.trigger({ message: m.dataImportIncludeOneSheet() });
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
					message: refusal(body, m.dataImportNoLongerFits())
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
		format = '';
		plans = [];
		outcome = null;
		useSaved = true;
		saveName = '';
		loadSavedMappings();
	}

	function ignoreSaved() {
		useSaved = false;
		pick(file ?? undefined, false);
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
			toastStore.trigger({ message: m.dataImportNameMapping() });
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
							? m.dataImportNotAllowedSave()
							: m.dataImportCouldNotSave({ detail: JSON.stringify(body) })
				});
				return;
			}
			toastStore.trigger({ message: m.dataImportMappingSaved({ name }) });
			await loadSavedMappings();
		} finally {
			saving = false;
		}
	}

	async function deleteMapping(id: string) {
		const res = await fetch(`${API}/mappings/${id}`, { method: 'DELETE' });
		confirmDelete = '';
		if (!res.ok) {
			toastStore.trigger({ message: m.dataImportCouldNotDelete() });
			return;
		}
		await loadSavedMappings();
	}

	function matchLabel(plan: Plan, type: string) {
		const score = plan.analysed.candidates?.find((c) => c.model_type === type)?.score;
		return score === undefined
			? ''
			: ` (${m.dataImportMatch({ percent: Math.round(score * 100) })})`;
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
		const link = linkFor(step.model_type, results);
		if (perSheet.length) {
			return perSheet.map(([sheet, v]) => ({
				...row(
					`${modelLabel(step.model_type)} · ${sheet.replaceAll('_', ' ')}`,
					step.model_type,
					v as Counts
				),
				link
			}));
		}
		const error = step.error === 'notAllowed' ? m.dataImportNotAllowedHere() : step.error;
		return [{ ...row(modelLabel(step.model_type), step.model_type, results, error), link }];
	}

	// {applied_controls_created: 4} -> "Applied controls (4)", in the app's own words when it has them.
	function sideEffects(details: Record<string, number>) {
		const messages = m as unknown as Record<string, (() => string) | undefined>;
		return Object.entries(details)
			.filter(([key, n]) => key.endsWith('_created') && n > 0)
			.map(([key, n]) => {
				const noun = key.replace(/_created$/, '');
				const camel = noun.replace(/_(\w)/g, (_, c: string) => c.toUpperCase());
				const plural = camel.endsWith('s') ? camel : `${camel}s`;
				return `${messages[plural]?.() ?? noun.replaceAll('_', ' ')} (${n})`;
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
		!!FORMATS[format]?.matrix ||
			included.some((p) => ['RiskAssessment', 'BusinessImpactAnalysis'].includes(p.modelType))
	);
	// Users live outside domains; metric samples take their instance's.
	const UNSCOPED = ['User', 'CustomMetricSample'];
	// A sheet without a domain column puts every row in the fallback domain, and
	// conflicts are looked up there: without one the dry run is meaningless.
	const needsDomain = $derived(
		!folderId &&
			(!!format ||
				included.some(
					(p) =>
						!UNSCOPED.includes(p.modelType) &&
						!Object.values(p.columns).some((key) => key === 'domain' || key === 'folder')
				))
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

	const STAGES = [
		m.dataImportStageChoose(),
		m.dataImportStageReview(),
		m.dataImportDryRun(),
		m.dataImportImport()
	];
	const stage = $derived(!file ? 0 : !outcome ? 1 : outcome.dryRun ? 2 : 3);

	function sheetStatus(plan: Plan): 'off' | 'review' | 'ready' {
		if (!plan.include || !plan.modelType) return 'off';
		return unmatchedValues(plan) ? 'review' : 'ready';
	}

	function fileIcon(name: string) {
		if (/\.zip$/i.test(name)) return 'fa-file-zipper';
		if (/\.xml$/i.test(name)) return 'fa-file-code';
		if (/\.csv$/i.test(name)) return 'fa-file-csv';
		return 'fa-file-excel';
	}
</script>

<div class="p-4 space-y-5">
	<header class="flex flex-wrap items-start justify-between gap-4">
		<div class="flex items-start gap-3">
			<span
				class="flex items-center justify-center size-11 shrink-0 rounded-xl preset-tonal-primary"
				aria-hidden="true"
			>
				<i class="fa-solid fa-file-import text-lg"></i>
			</span>
			<div class="space-y-1">
				<h4 class="h4 font-bold">{m.dataImportTitle()}</h4>
				<p class="text-sm text-surface-600-400">
					{m.dataImportIntro()}
				</p>
			</div>
		</div>
		<ol class="flex items-center gap-2 text-xs font-medium" aria-label={m.dataImportProgress()}>
			{#each STAGES as label, i (label)}
				<li class="flex items-center gap-2" aria-current={i === stage ? 'step' : undefined}>
					{#if i}<span
							class="w-6 h-px transition-colors duration-300 {i <= stage
								? 'bg-primary-500'
								: 'bg-surface-300-700'}"
							aria-hidden="true"
						></span>{/if}
					<span
						class="flex items-center justify-center size-6 rounded-full transition-colors duration-300
							{i < stage || (i === stage && i === STAGES.length - 1)
							? 'preset-filled-success-500'
							: i === stage
								? 'preset-filled-primary-500'
								: 'preset-tonal-surface'}"
					>
						{#if i < stage || (i === stage && i === STAGES.length - 1)}
							<i class="fa-solid fa-check text-[10px]"></i>
						{:else}
							{i + 1}
						{/if}
					</span>
					<span class={i === stage ? '' : 'text-surface-600-400 hidden md:inline'}>{label}</span>
				</li>
			{/each}
		</ol>
	</header>

	{#if !file}
		<label
			for="data-import-file"
			class="group flex flex-col items-center justify-center gap-4 px-6 py-14 rounded-2xl border-2 border-dashed text-center cursor-pointer transition-colors
				{dragging
				? 'border-primary-500 bg-primary-50-950'
				: 'border-surface-300-700 bg-surface-50-950 hover:border-primary-400 hover:bg-primary-50-950/50'}"
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
			<span
				class="flex items-center justify-center size-16 rounded-full preset-tonal-primary transition-transform group-hover:scale-105"
				aria-hidden="true"
			>
				<i class="fa-solid {analysing ? 'fa-spinner fa-spin' : 'fa-cloud-arrow-up'} text-2xl"></i>
			</span>
			{#if analysing}
				<span class="text-lg font-semibold">{m.dataImportReading()}</span>
			{:else}
				<span class="space-y-1">
					<span class="block text-lg font-semibold">{m.dataImportDropHere()}</span>
					<span class="block text-sm text-surface-600-400">{m.dataImportMaxSize()}</span>
				</span>
				<span class="flex flex-wrap justify-center gap-2 text-xs">
					<span class="badge preset-tonal-success"
						><i class="fa-solid fa-file-excel mr-1"></i>Excel (.xlsx, .xls)</span
					>
					<span class="badge preset-tonal-secondary"
						><i class="fa-solid fa-file-csv mr-1"></i>CSV</span
					>
					{#each ['EBIOS RM (Egerie, ARM, CISO Assistant)', 'CyFun'] as label (label)}
						<span class="badge preset-tonal-primary" title={m.dataImportFormatHint()}
							><i class="fa-solid fa-wand-magic-sparkles mr-1"></i>{label}</span
						>
					{/each}
				</span>
			{/if}
			<input
				id="data-import-file"
				type="file"
				accept=".xlsx,.xls,.csv,.xml,.zip"
				class="sr-only"
				disabled={analysing}
				onchange={(e) => pick(e.currentTarget.files?.[0])}
			/>
		</label>

		<details class="group card bg-surface-50-950 border border-surface-200-800 shadow-sm">
			<summary
				class="flex flex-wrap items-center justify-between gap-2 px-4 py-3 cursor-pointer list-none group-open:border-b border-surface-200-800"
			>
				<h5 class="flex items-center gap-2 font-semibold text-sm">
					<i
						class="fa-solid fa-chevron-right text-xs text-surface-500 transition-transform group-open:rotate-90"
					></i>
					<i class="fa-solid fa-table-list text-primary-500"></i>
					{m.dataImportTemplatesTitle()}
				</h5>
				<a
					class="text-sm text-primary-600-400 hover:underline"
					href="https://intuitem.gitbook.io/ciso-assistant/configuration/data-import"
					target="_blank"
					rel="noopener noreferrer"
					><i class="fa-solid fa-book mr-1"></i>{m.dataWizardTemplatesAndGuidelines()}<i
						class="fa-solid fa-arrow-up-right-from-square ml-1 text-xs"
					></i></a
				>
			</summary>
			<div class="p-4 space-y-3">
				<p class="text-sm text-surface-600-400">
					{m.dataImportTemplatesHint()}
				</p>
				<div class="flex flex-wrap gap-2">
					<!-- eslint-disable svelte/no-navigation-without-resolve -- file downloads through the page's API proxy -->
					{#each data.templates as type (type)}
						<a
							href={`/experimental/data-import/api/templates/${type}`}
							download
							class="btn btn-sm preset-tonal-surface border border-surface-200-800"
							><i class="fa-solid fa-download mr-1 text-xs"></i>{modelLabel(type)}</a
						>
					{/each}
					<!-- eslint-enable svelte/no-navigation-without-resolve -->
				</div>
			</div>
		</details>
		<p class="flex items-center gap-2 px-1 text-sm text-surface-600-400">
			<i class="fa-solid fa-circle-info"></i>
			<span>
				{m.dataImportLibrariesHint()}
				<a href={resolve('/libraries')} class="text-primary-600-400 hover:underline"
					>{m.libraries()}<i class="fa-solid fa-arrow-right ml-1 text-xs"></i></a
				>.
			</span>
		</p>

		<section class="card bg-surface-50-950 border border-surface-200-800 shadow-sm">
			<h5
				class="flex items-center gap-2 px-4 py-3 font-semibold text-sm border-b border-surface-200-800"
			>
				<i class="fa-solid fa-bookmark text-primary-500"></i>
				{m.dataImportSavedMappings()}
				{#if savedMappings.length}
					<span class="badge preset-tonal-surface">{savedMappings.length}</span>
				{/if}
			</h5>
			<p class="px-4 pt-3 text-sm text-surface-600-400">{m.dataImportSavedMappingsHint()}</p>
			{#if savedMappings.length === 0}
				<p class="px-4 py-4 text-sm text-surface-500 italic">
					{m.dataImportNoSavedMappings()}
				</p>
			{:else}
				<ul class="divide-y divide-surface-200-800">
					{#each savedMappings as saved (saved.id)}
						<li
							class="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm hover:bg-surface-100-900 transition-colors"
						>
							<span class="flex flex-col">
								<span class="font-medium">{saved.name}</span>
								<span class="text-xs text-surface-600-400">
									{m.dataImportSheetCount({ count: saved.sheets.length })} ·
									{saved.use_count
										? m.dataImportUsedTimes({ count: saved.use_count })
										: m.dataImportNeverUsed()}
									{#if saved.created_by}· {m.dataImportBy({ email: saved.created_by.email })}{/if}
								</span>
							</span>
							<span class="flex flex-wrap gap-1">
								{#each [...new Set(saved.sheets.map((s) => s.model_type))] as type (type)}
									<span class="badge preset-tonal-primary text-xs">{modelLabel(type)}</span>
								{/each}
							</span>
							<span class="grow"></span>
							{#if confirmDelete === saved.id}
								<span>{m.dataImportDeleteMappingConfirm()}</span>
								<button
									type="button"
									class="btn btn-sm preset-filled-error-500"
									onclick={() => deleteMapping(saved.id)}>{m.delete()}</button
								>
								<button type="button" class="btn btn-sm" onclick={() => (confirmDelete = '')}
									>{m.cancel()}</button
								>
							{:else if mayDelete(saved)}
								<button
									type="button"
									class="btn-icon btn-icon-sm hover:preset-tonal-error"
									aria-label={m.dataImportDeleteNamed({ name: saved.name })}
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
		<div
			class="card bg-surface-50-950 border border-surface-200-800 shadow-sm p-3 flex flex-wrap items-center gap-3"
		>
			<span
				class="flex items-center justify-center size-10 rounded-lg preset-tonal-success"
				aria-hidden="true"
			>
				<i class="fa-solid {fileIcon(file.name)} text-lg"></i>
			</span>
			<div class="flex flex-col min-w-0">
				<strong class="truncate">{file.name}</strong>
				<span class="text-xs text-surface-600-400">
					{#if analysing}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>{m.dataImportReading()}
					{:else if format}
						{m.dataImportRecognisedAs({ format: FORMATS[format]?.label() ?? format })}
					{:else}
						{m.dataImportSheetCount({ count: plans.length })} ·
						{m.dataImportToImport({ count: included.length })} ·
						{m.dataImportRowCount({ count: rowCount })}
					{/if}
				</span>
			</div>
			<span class="grow"></span>
			<button
				type="button"
				class="btn btn-sm preset-tonal"
				onclick={reset}
				disabled={running || analysing}
			>
				<i class="fa-solid fa-rotate-left mr-1"></i>{m.dataImportChooseAnother()}
			</button>
		</div>

		{#if appliedSaved.length}
			<div
				class="card preset-tonal-primary p-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm"
			>
				<i class="fa-solid fa-bookmark"></i>
				<span>
					{m.dataImportUsingSaved()}
					{#each appliedSaved as saved, i (saved.id)}
						{i ? ', ' : ''}<strong>{saved.name}</strong>{#if saved.new_columns.length}
							({m.dataImportNewColumns({ columns: saved.new_columns.join(', ') })}){/if}
					{/each}
				</span>
				<span class="grow"></span>
				<button type="button" class="btn btn-sm preset-outlined" onclick={ignoreSaved}>
					{m.dataImportIgnoreSaved()}
				</button>
			</div>
		{:else if !useSaved}
			<p class="text-sm text-surface-600-400">
				{m.dataImportSavedIgnored()}
				<button
					type="button"
					class="anchor"
					onclick={() => {
						useSaved = true;
						pick(file ?? undefined, false);
					}}>{m.dataImportUseAgain()}</button
				>
			</p>
		{/if}

		{#if format}
			<section
				class="card bg-surface-50-950 border border-surface-200-800 border-l-4 border-l-primary-500 shadow-sm p-5 flex flex-wrap gap-4"
			>
				<span
					class="flex items-center justify-center size-12 shrink-0 rounded-xl preset-tonal-primary"
					aria-hidden="true"
				>
					<i class="fa-solid {FORMATS[format]?.icon ?? 'fa-file'} text-xl"></i>
				</span>
				<div class="space-y-2 grow basis-96">
					<div class="flex flex-wrap items-center gap-2">
						<h5 class="font-semibold">{FORMATS[format]?.label() ?? format}</h5>
						<span class="badge preset-tonal-primary text-xs">
							<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>{m.dataImportRecognised()}
						</span>
					</div>
					<p class="text-sm text-surface-600-400 whitespace-pre-line">
						{FORMATS[format]?.description()}
					</p>
					<p class="text-sm">
						{m.dataImportWholeFileNote()}
					</p>
				</div>
				{#if !/\.(xml|zip)$/i.test(file.name)}
					<button
						type="button"
						class="btn btn-sm preset-outlined self-start"
						disabled={running || analysing}
						onclick={() => pick(file ?? undefined, false)}
					>
						<i class="fa-solid fa-table-columns mr-1"></i>{m.dataImportMapMyself()}
					</button>
				{/if}
			</section>
		{/if}

		<div class="space-y-3">
			{#each plans as plan, index (plan.analysed.name)}
				<div
					in:fly|global={{
						y: 4,
						delay: Math.min(index, 10) * 40,
						duration: prefersReducedMotion.current ? 0 : 200
					}}
				>
					{#if plan.analysed.companion}
						<div
							class="flex items-center gap-3 px-4 py-2 rounded-lg border border-dashed border-surface-300-700 text-sm text-surface-600-400"
						>
							<i class="fa-solid {COMPANIONS[plan.analysed.companion].icon} w-4 text-center"></i>
							<span class="font-mono font-medium text-surface-800-200">{plan.analysed.name}</span>
							<span>{COMPANIONS[plan.analysed.companion].text()}</span>
							<span class="grow"></span>
							{#if plan.analysed.row_count}
								<span class="text-xs"
									>{m.dataImportRowCount({ count: plan.analysed.row_count })}</span
								>
							{/if}
						</div>
					{:else}
						{@const status = sheetStatus(plan)}
						<section
							id="sheet-{index}"
							class="card bg-surface-50-950 border border-surface-200-800 border-l-4 shadow-sm transition-shadow hover:shadow-md
							{status === 'ready'
								? 'border-l-success-500'
								: status === 'review'
									? 'border-l-warning-500'
									: 'border-l-surface-300-700'}"
						>
							<div class="flex flex-wrap items-center gap-x-4 gap-y-3 p-4">
								<label class="flex items-center gap-3 min-w-56">
									<input
										type="checkbox"
										class="checkbox"
										bind:checked={plan.include}
										disabled={plan.analysed.empty || !plan.modelType || running}
									/>
									<span class="flex flex-col">
										<span
											class="font-mono font-semibold {plan.include ? '' : 'text-surface-600-400'}"
											><i class="fa-solid fa-table text-xs text-surface-500 mr-1"></i>{plan.analysed
												.name}</span
										>
										<span class="text-xs text-surface-600-400">
											{#if plan.analysed.empty}
												{m.dataImportNoDataRows()}
											{:else}
												{m.dataImportRowCount({ count: plan.analysed.row_count ?? 0 })} ·
												{m.dataImportHeaderOnRow({ row: plan.headerRow })}
											{/if}
										</span>
									</span>
								</label>

								{#if !plan.analysed.empty}
									<i
										class="fa-solid fa-arrow-right text-surface-400 hidden sm:block"
										aria-hidden="true"
									></i>
									<div class="flex flex-wrap items-center gap-2">
										<select
											class="select w-auto text-sm"
											value={plan.modelType}
											disabled={plan.busy || running}
											aria-label={m.dataImportWhatBecomes({ sheet: plan.analysed.name })}
											onchange={(e) => retarget(index, e.currentTarget.value)}
										>
											<option value="" disabled>{m.dataImportChooseObject()}</option>
											{#each data.modelTypes as type (type)}
												<option value={type}>{modelLabel(type)}{matchLabel(plan, type)}</option>
											{/each}
										</select>
										{#if (schemas[plan.modelType]?.sheets.length ?? 0) > 1}
											<select
												class="select w-auto text-sm"
												value={plan.targetSheet}
												disabled={plan.busy || running}
												aria-label={m.dataImportTemplateSheetFor({ sheet: plan.analysed.name })}
												onchange={(e) => retarget(index, plan.modelType, e.currentTarget.value)}
											>
												{#each schemas[plan.modelType].sheets as sheet (sheet.name)}
													<option value={sheet.name}>{sheet.name}</option>
												{/each}
											</select>
										{/if}
									</div>
									{#if plan.modelType}
										{@const total = plan.analysed.columns?.length ?? 0}
										<div class="flex flex-col gap-1 min-w-40 text-xs">
											<span class="text-surface-600-400">
												{m.dataImportColumnsMapped({ mapped: mappedCount(plan), total })}
											</span>
											<span class="h-1.5 rounded-full bg-surface-200-800 overflow-hidden">
												<span
													class="block h-full rounded-full bg-primary-500 transition-all"
													style="width: {total ? (100 * mappedCount(plan)) / total : 0}%"
												></span>
											</span>
										</div>
										{#if unmatchedValues(plan)}
											<button
												type="button"
												class="badge preset-tonal-warning hover:preset-filled-warning-500 transition-colors"
												title={m.dataImportUnmatchedHint()}
												onclick={() => reviewValues(index)}
											>
												<i class="fa-solid fa-triangle-exclamation mr-1"></i>
												{m.dataImportValuesToReview({ count: unmatchedValues(plan) })}
											</button>
										{/if}
									{/if}
									<span class="grow"></span>
									{#if plan.busy}
										<i class="fa-solid fa-spinner fa-spin text-primary-500"></i>
									{/if}
									{#if plan.modelType}
										<button
											type="button"
											class="btn btn-sm {plan.open
												? 'preset-filled-surface-900-100'
												: 'preset-tonal'}"
											aria-expanded={plan.open}
											onclick={() => (plan.open = !plan.open)}
										>
											<i class="fa-solid {plan.open ? 'fa-chevron-up' : 'fa-sliders'} mr-1"></i>
											{plan.open ? m.close() : m.dataImportAdjust()}
										</button>
									{/if}
								{/if}
							</div>

							{#if plan.open && plan.modelType && !plan.analysed.empty}
								<div class="border-t border-surface-200-800 bg-surface-100-900/40 p-4 space-y-5">
									<label class="flex items-center gap-2 text-sm w-fit">
										{m.dataImportHeaderRow()}
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
									<div
										class="overflow-x-auto rounded-lg border border-surface-200-800 bg-surface-50-950"
									>
										<table class="table text-sm">
											<thead class="bg-surface-100-900">
												<tr>
													<th>{m.dataImportYourColumn()}</th>
													<th>{m.dataImportSampleValues()}</th>
													<th>{m.dataImportField()}</th>
												</tr>
											</thead>
											<tbody>
												{#each plan.analysed.columns ?? [] as col (col.header)}
													{@const field = schemaSheet(plan)?.columns.find(
														(c) => c.key === plan.columns[col.header]
													)}
													<tr class={plan.columns[col.header] ? '' : 'opacity-70'}>
														<td class="align-top">
															<span class="font-mono font-medium">{col.header}</span>
															{#if columnUnmatched(plan, col.header)}
																<span class="block text-xs text-warning-700-300">
																	{m.dataImportValuesToReview({
																		count: columnUnmatched(plan, col.header)
																	})}
																</span>
															{/if}
														</td>
														<td class="align-top max-w-72">
															<span class="flex flex-wrap gap-1">
																{#each col.samples.slice(0, 3) as sample, i (i)}
																	<span
																		class="px-1.5 py-0.5 rounded bg-surface-100-900 text-xs text-surface-700-300 truncate max-w-40"
																		>{sample}</span
																	>
																{/each}
															</span>
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
																aria-label={m.dataImportFieldFor({ column: col.header })}
															>
																<option value="">{m.ignore()}</option>
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
																				aria-label={m.dataImportValueFor({ value })}
																				bind:value={plan.values[col.header][value]}
																				disabled={running}
																			>
																				<option value="" disabled>{m.dataImportNotMatched()}</option
																				>
																				<option value={KEEP}>{m.dataImportKeepAsIs()}</option>
																				{#each field.choices as choice (choice.value)}
																					<option value={String(choice.value)}
																						>{translateChoiceLabel(
																							choice.label,
																							choice.value
																						)}</option
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
										<h3 class="text-sm font-semibold">{m.dataImportSameValue()}</h3>
										<p class="text-xs text-surface-600-400">
											{m.dataImportSameValueHint()}
										</p>
										{#each unmappedFields(plan).filter((c) => c.key in plan.defaults) as column (column.key)}
											<div class="flex items-center gap-2 text-sm">
												<span class="w-56 truncate">{column.label} ({column.key})</span>
												{#if column.boolean || column.choices}
													<select
														class="select w-auto text-sm"
														bind:value={plan.defaults[column.key]}
														disabled={running}
														aria-label={m.dataImportValueForEveryRow({ field: column.key })}
													>
														<option value="" disabled>{m.dataImportChooseValue()}</option>
														{#if column.boolean}
															<option value="true">{m.yes()}</option>
															<option value="false">{m.no()}</option>
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
														aria-label={m.dataImportValueForEveryRow({ field: column.key })}
													/>
												{/if}
												<button
													type="button"
													class="btn-icon btn-icon-sm"
													onclick={() => delete plan.defaults[column.key]}
													disabled={running}
													aria-label={m.dataImportRemoveValueFor({ field: column.key })}
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
												aria-label={m.dataImportAddValueForEveryRow()}
												onchange={(e) => {
													plan.defaults[e.currentTarget.value] = '';
													e.currentTarget.value = '';
												}}
											>
												<option value="" disabled>{m.dataImportAddField()}</option>
												{#each unmappedFields(plan).filter((c) => !(c.key in plan.defaults)) as column (column.key)}
													<option value={column.key}>{column.label} ({column.key})</option>
												{/each}
											</select>
										{/if}
									</div>
								</div>
							{/if}
						</section>
					{/if}
				</div>
			{/each}
		</div>

		<section
			class="card bg-surface-50-950 border border-surface-200-800 shadow-lg sticky bottom-3 z-10"
		>
			<div class="flex flex-wrap items-start gap-6 p-4">
				<div class="min-w-72 text-sm">
					<FolderTreeSelect
						form={scopeForm}
						field="folder"
						nullable
						required={needsDomain}
						disabled={running}
						label={format ? m.domain() : m.dataWizardSelectFallbackDomain()}
						helpText={format ? '' : m.dataWizardFallbackDomainHelp()}
						onChange={(v) => (folderId = v ?? '')}
					/>
				</div>
				{#if needsAudit}
					<label class="space-y-1 text-sm">
						<span class="block font-medium">{m.audit()}</span>
						<select class="select text-sm" bind:value={auditTargetId} disabled={running}>
							<option value="">{m.dataImportCreateNewAudit()}</option>
							{#each data.audits as audit (audit.id)}
								<option value={audit.id}>{m.dataImportUpdateAudit({ name: audit.name })}</option>
							{/each}
						</select>
					</label>
					{#if !auditTargetId}
						<label class="space-y-1 text-sm">
							<span class="block font-medium">{m.framework()}</span>
							<select class="select text-sm" bind:value={auditFrameworkId} disabled={running}>
								<option value="">{m.dataImportChooseFramework()}</option>
								{#each data.frameworks as framework (framework.id)}
									<option value={framework.id}>{framework.str || framework.name}</option>
								{/each}
							</select>
						</label>
						<label class="space-y-1 text-sm">
							<span class="block font-medium">{m.dataImportAuditName()}</span>
							<input
								class="input text-sm"
								bind:value={auditName}
								placeholder={m.dataImportAuditNamePlaceholder()}
								disabled={running}
							/>
						</label>
					{/if}
				{/if}
				{#if needsMatrix}
					<label class="space-y-1 text-sm">
						<span class="block font-medium"
							>{m.riskMatrix()} <span class="text-error-500">*</span></span
						>
						<select class="select text-sm" bind:value={matrixId} disabled={running} required>
							<option value="">{m.dataImportChooseMatrix()}</option>
							{#each data.matrices as matrix (matrix.id)}
								<option value={matrix.id}>{matrix.str || matrix.name}</option>
							{/each}
						</select>
					</label>
				{/if}
				<fieldset class="space-y-1 text-sm">
					<legend class="font-medium">{m.dataWizardOnConflict()}</legend>
					<div class="flex gap-1 p-1 rounded-lg bg-surface-100-900 w-fit">
						{#each [['stop', m.dataWizardOnConflictStop(), m.dataWizardOnConflictStopDescription()], ['skip', m.dataWizardOnConflictSkip(), m.dataWizardOnConflictSkipDescription()], ['update', m.dataWizardOnConflictUpdate(), m.dataWizardOnConflictUpdateDescription()]] as [value, label, hint] (value)}
							<label
								class="px-3 py-1 rounded-md cursor-pointer transition-colors has-checked:preset-filled-primary-500 has-focus-visible:ring-2 ring-primary-500"
								title={hint}
							>
								<input
									type="radio"
									class="sr-only"
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
			<div
				class="flex flex-wrap items-center gap-3 px-4 py-3 border-t border-surface-200-800 bg-surface-100-900/50 rounded-b-container"
			>
				<span class="text-sm text-surface-600-400">
					{#if format}
						{m.dataImportWholeFile({ format: FORMATS[format]?.label() ?? format })}
					{:else}
						{m.dataImportSheetCount({ count: included.length })} ·
						{m.dataImportRowCount({ count: rowCount })}
					{/if}
				</span>
				<span class="grow"></span>
				<button
					type="button"
					class="btn preset-tonal-primary"
					onclick={() => run(true)}
					disabled={running ||
						(!format && !included.length) ||
						needsDomain ||
						(needsMatrix && !matrixId) ||
						(needsAudit && !auditTargetId && !auditFrameworkId)}
					title={needsDomain ? m.dataWizardFallbackDomainHelp() : ''}
				>
					<i class="fa-solid {running ? 'fa-spinner fa-spin' : 'fa-flask'} mr-2"></i>
					{m.dataImportDryRun()}
				</button>
				<button
					type="button"
					class="btn preset-filled-primary-500"
					onclick={() => run(false)}
					disabled={running || !canImport}
					title={canImport ? '' : m.dataImportDryRunFirst()}
				>
					<i class="fa-solid fa-file-import mr-2"></i>{m.dataImportImport()}
				</button>
			</div>
		</section>

		{#if outcome && outcomeTotals}
			<section
				class="card bg-surface-50-950 border border-surface-200-800 shadow-sm overflow-hidden"
				aria-live="polite"
			>
				<div
					class="flex items-center gap-3 px-4 py-3 border-b border-surface-200-800
						{outcome.dryRun
						? 'preset-tonal-primary'
						: outcomeTotals.failed
							? 'preset-tonal-warning'
							: 'preset-tonal-success'}"
				>
					<i
						class="fa-solid {outcome.dryRun
							? 'fa-flask'
							: outcomeTotals.failed
								? 'fa-triangle-exclamation'
								: 'fa-circle-check'} text-lg"
					></i>
					<h5 class="font-semibold">
						{outcome.dryRun ? m.dataImportDryRunDone() : m.dataImportDone()}
					</h5>
					{#if !outcome.dryRun}
						<div class="ml-auto flex flex-wrap justify-end gap-2">
							{#each [...new Map(outcome.rows
										.filter((r) => r.link && r.created + r.updated > 0)
										.map((r) => [r.link!.href, r.link!])).values()] as link (link.href)}
								<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- internal paths built from LIST_PAGES or a returned id -->
								<a href={`/${link.href}`} class="btn btn-sm preset-filled-primary-500">
									{link.label}<i class="fa-solid fa-arrow-right ml-2"></i>
								</a>
							{/each}
						</div>
					{/if}
				</div>
				<div class="p-4 space-y-4">
					<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
						{#each [{ n: outcomeTotals.created, label: outcome.dryRun ? m.dataImportWouldBeCreated() : m.created(), icon: 'fa-plus', tone: 'preset-tonal-success' }, { n: outcomeTotals.updated, label: outcome.dryRun ? m.dataImportWouldBeUpdated() : m.updated(), icon: 'fa-pen', tone: 'preset-tonal-secondary' }, { n: outcomeTotals.skipped, label: m.skipped(), icon: 'fa-forward', tone: 'preset-tonal-surface' }, { n: outcomeTotals.failed, label: m.failed(), icon: 'fa-xmark', tone: 'preset-tonal-error' }] as tile (tile.label)}
							<div class="card p-3 flex items-center gap-3 {tile.tone}">
								<span
									class="flex items-center justify-center size-9 rounded-full bg-surface-50-950/60"
									aria-hidden="true"
								>
									<i class="fa-solid {tile.icon}"></i>
								</span>
								<div>
									<div class="text-2xl font-bold leading-none">{tile.n}</div>
									<div class="text-xs mt-1">{tile.label}</div>
								</div>
							</div>
						{/each}
					</div>
					<div class="overflow-x-auto rounded-lg border border-surface-200-800">
						<table class="table text-sm">
							<thead class="bg-surface-100-900">
								<tr>
									<th>{m.object()}</th>
									<th class="text-right">{m.dataImportNew()}</th>
									<th class="text-right">{m.updated()}</th>
									<th class="text-right">{m.skipped()}</th>
									<th class="text-right">{m.failed()}</th>
								</tr>
							</thead>
							<tbody>
								{#each outcome.rows as r (r.label)}
									<tr>
										<td>
											<span class="font-medium">{r.label}</span>
											{#if r.stopped}
												<span class="badge preset-tonal-warning ml-1">{m.dataImportStopped()}</span>
											{/if}
											{#if r.error}
												<span class="text-error-600-400 ml-1">{r.error}</span>
											{/if}
											{#if sideEffects(r.details)}
												<span class="block text-xs text-surface-600-400 mt-0.5">
													<i class="fa-solid fa-link mr-1"></i>
													{outcome.dryRun
														? m.dataImportWouldAlsoCreate({ items: sideEffects(r.details) })
														: m.dataImportAlsoCreated({ items: sideEffects(r.details) })}
												</span>
											{/if}
										</td>
										<td class="text-right tabular-nums">{r.created}</td>
										<td class="text-right tabular-nums">{r.updated}</td>
										<td class="text-right tabular-nums">{r.skipped}</td>
										<td
											class="text-right tabular-nums {r.failed
												? 'text-error-600-400 font-semibold'
												: ''}">{r.failed}</td
										>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
					{#each outcome.rows.filter((r) => r.errors.length) as r (r.label)}
						<details
							class="rounded-lg border border-surface-200-800"
							open={outcome.rows.length === 1}
						>
							<summary class="cursor-pointer px-3 py-2 text-sm font-semibold">
								{r.label}: {m.dataImportErrorsAndWarnings({ count: r.errors.length })}
							</summary>
							<ul class="text-sm space-y-1 px-3 pb-3">
								{#each r.errors.slice(0, 20) as err, i (i)}
									<li class="flex gap-2">
										{#if err.warning}
											<i
												class="fa-solid fa-triangle-exclamation text-warning-600-400 mt-0.5"
												title={m.dataImportImportedWithWarning()}
											></i>
											<span class="sr-only">{m.warning()}:</span>
										{:else}
											<i
												class="fa-solid fa-circle-xmark text-error-600-400 mt-0.5"
												title={m.dataImportNotImported()}
											></i>
											<span class="sr-only">{m.error()}:</span>
										{/if}
										<span>
											{#if recordLabel(err.record)}
												<span class="font-medium">{recordLabel(err.record)}:</span>
											{/if}
											<span class="text-surface-600-400">{explain(err, r.modelType)}</span>
										</span>
									</li>
								{/each}
							</ul>
						</details>
					{/each}
					{#if !format && outcome.dryRun && canImport && (mayMap('add') || (appliedSaved.length && mayMap('change')))}
						<div class="flex flex-wrap items-end gap-3 pt-4 border-t border-surface-200-800">
							<label class="space-y-1 text-sm grow max-w-md">
								<span class="block font-medium">{m.dataImportSaveForNextTime()}</span>
								<input class="input text-sm" bind:value={saveName} disabled={saving} />
							</label>
							{#if appliedSaved.length === 1 && mayMap('change')}
								<button
									type="button"
									class="btn preset-outlined"
									disabled={saving}
									onclick={() => saveMapping(appliedSaved[0].id)}
								>
									{m.dataImportUpdateNamed({ name: appliedSaved[0].name })}
								</button>
							{/if}
							{#if mayMap('add')}
								<button
									type="button"
									class="btn preset-tonal-primary"
									disabled={saving}
									onclick={() => saveMapping()}
								>
									<i class="fa-solid fa-bookmark mr-1"></i>{m.dataImportSaveAsNew()}
								</button>
							{/if}
						</div>
					{/if}
				</div>
			</section>
		{/if}
	{/if}
</div>
