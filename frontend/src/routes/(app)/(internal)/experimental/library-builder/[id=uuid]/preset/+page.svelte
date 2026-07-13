<script lang="ts">
	import type { PageData } from './$types';
	import { onMount, onDestroy } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import { pageTitle } from '$lib/utils/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { TYPE_TO_MODEL, MODEL_TO_TYPE, SCAFFOLD_TYPES } from '$lib/utils/modelTargets';
	import TranslationsEditor from '../../TranslationsEditor.svelte';

	let { data }: { data: PageData } = $props();
	$pageTitle = m.lbPresetPageTitle({ name: data.preset.name });

	// The _action protocol adapter serving the journey preset stored inside
	// this library draft's document.
	const apiBase = `/experimental/library-builder/${data.draft.id}/preset`;

	type Scaffold = {
		type: string;
		ref?: string;
		name?: string;
		description?: string;
		framework?: string;
		risk_matrix?: string;
		implementation_groups?: string[];
		category?: string;
		csf_function?: string;
		priority?: number;
		severity?: number;
		asset_type?: string;
		kind?: string;
		matrix_preset?: string;
		step_ref_id?: string;
		[k: string]: any;
	};
	type Step = {
		id?: string | null;
		key: string;
		title: string;
		description?: string;
		target_model?: string | null;
		target_ref?: string | null;
		target_url?: string | null;
		target_params?: Record<string, any> | null;
		translations?: Record<string, Record<string, string>>;
	};
	type Draft = {
		journey_meta: {
			name: string;
			description: string;
			translations: Record<string, Record<string, string>>;
		};
		scaffolded_objects: Scaffold[];
		steps: Step[];
	};
	type PointerMode = 'none' | 'model' | 'url';

	// Object types behind the project_management feature flag; presets scaffolding
	// these must enable that flag (the editor warns the author).
	const PROJECT_MANAGEMENT_TYPES = ['project', 'responsibility_matrix'];

	const NAV_ONLY_MODELS = [
		'accreditations',
		'actors',
		'evidences',
		'incidents',
		'metric-instances'
	];
	const ALL_MODELS = [...new Set(['', ...NAV_ONLY_MODELS, ...Object.values(TYPE_TO_MODEL)])].sort(
		(a, b) => a.localeCompare(b)
	);

	const FINDINGS_CATEGORIES = ['pentest', 'audit', 'review', 'other'];
	const ASSET_TYPES = [
		{ value: 'SP', labelKey: 'support' },
		{ value: 'PR', labelKey: 'primary' }
	];
	const APPLIED_CONTROL_CATEGORIES = ['policy', 'process', 'technical', 'physical', 'procedure'];
	const SECURITY_EXCEPTION_SEVERITIES = [
		{ value: 0, labelKey: 'info' },
		{ value: 1, labelKey: 'low' },
		{ value: 2, labelKey: 'medium' },
		{ value: 3, labelKey: 'high' },
		{ value: 4, labelKey: 'critical' }
	];
	const PROJECT_KINDS = ['portfolio', 'program', 'project'];
	const MATRIX_PRESETS = ['raci', 'rasci', 'rapid', 'custom'];

	let draft: Draft | null = $state(null);
	let initialJson = $state('');
	let loading = $state(true);
	let saving = $state(false);
	let errorMsg = $state('');
	let confirmDiscard = $state(false);
	let isReadOnly = $derived(!data.preset.is_user_authored);

	const dirty = $derived(draft != null && JSON.stringify(draft) !== initialJson);

	// Project & responsibility-matrix scaffolds only surface once the project_management
	// feature flag is on; remind the author since the flag isn't editable here.
	const needsProjectManagement = $derived(
		!!draft?.scaffolded_objects?.some((s) => PROJECT_MANAGEMENT_TYPES.includes(s.type))
	);

	beforeNavigate(({ cancel }) => {
		if (dirty && !confirm(m.lbPresetUnsavedLeaveConfirm())) cancel();
	});

	// beforeNavigate only catches in-app route changes; tab close, refresh, or
	// URL-bar navigation needs the native beforeunload prompt.
	function handleBeforeUnload(event: BeforeUnloadEvent) {
		if (!dirty) return;
		event.preventDefault();
		event.returnValue = '';
	}

	onMount(async () => {
		if (typeof window !== 'undefined') {
			window.addEventListener('beforeunload', handleBeforeUnload);
		}
		if (isReadOnly) {
			loading = false;
			return;
		}
		await loadDraft();
	});

	onDestroy(() => {
		if (typeof window !== 'undefined') {
			window.removeEventListener('beforeunload', handleBeforeUnload);
		}
	});

	async function loadDraft() {
		loading = true;
		errorMsg = '';
		try {
			const r = await fetch(apiBase, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ action: 'start-editing' })
			});
			if (!r.ok) {
				errorMsg = m.lbPresetFailedToLoadDraft({ detail: r.status });
				return;
			}
			const j = await r.json();
			draft = normalize(j.editing_draft);
			initialJson = JSON.stringify(draft);
		} catch (e) {
			errorMsg = m.lbPresetFailedToLoadDraft({ detail: (e as Error).message ?? e });
		} finally {
			loading = false;
		}
	}

	function normalize(d: any): Draft {
		const result: Draft = {
			journey_meta: {
				name: d?.journey_meta?.name ?? '',
				description: d?.journey_meta?.description ?? '',
				translations: d?.journey_meta?.translations ?? {}
			},
			scaffolded_objects: (d?.scaffolded_objects ?? []).map((s: Scaffold) => ({ ...s })),
			steps: (d?.steps ?? []).map((s: Step) => ({ ...s }))
		};
		assignScaffoldsToSteps(result);
		return result;
	}

	// One-time massage: ensure every scaffold has step_ref_id pointing at an existing step.
	// Library presets carry no step_ref_id; we infer from type/target_model match.
	function assignScaffoldsToSteps(d: Draft) {
		const stepKeys = new Set(d.steps.map((s) => s.key));
		for (const sc of d.scaffolded_objects) {
			if (sc.step_ref_id && stepKeys.has(sc.step_ref_id)) continue;
			const matched = d.steps.find((s) => s.target_model === TYPE_TO_MODEL[sc.type]);
			sc.step_ref_id = matched?.key ?? d.steps[0]?.key;
		}
	}

	async function save() {
		if (!draft) return;
		saving = true;
		errorMsg = '';
		try {
			const r = await fetch(apiBase, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(draft)
			});
			const j = await r.json().catch(() => ({}));
			if (!r.ok) {
				errorMsg =
					safeTranslate(formatError(j)) || m.lbPresetFailedToSaveDraft({ detail: r.status });
				return;
			}
			draft = normalize(j.editing_draft);
			initialJson = JSON.stringify(draft);
		} catch (e) {
			errorMsg = m.lbPresetFailedToSaveDraft({ detail: (e as Error).message ?? e });
		} finally {
			saving = false;
		}
	}

	/** Revert: throw away local edits and reload the saved document state. */
	async function discard() {
		confirmDiscard = false;
		await loadDraft();
	}

	function formatError(j: any): string {
		if (!j) return m.lbPresetUnknownError();
		if (typeof j === 'string') return j;
		if (j.detail) return j.detail;
		try {
			return JSON.stringify(j);
		} catch {
			return String(j);
		}
	}

	// --- Step ops ---
	function getPointerMode(step: Step): PointerMode {
		// Mode is signalled by which field is a string (incl. empty string) vs null/undefined.
		// Empty string means "user picked this mode but hasn't filled it in yet."
		if (typeof step.target_url === 'string') return 'url';
		if (typeof step.target_model === 'string') return 'model';
		return 'none';
	}

	function setPointerMode(i: number, mode: PointerMode) {
		if (!draft) return;
		const next = [...draft.steps];
		const s = { ...next[i] };
		if (mode === 'none') {
			s.target_url = null;
			s.target_model = null;
			s.target_ref = null;
			s.target_params = null;
		} else if (mode === 'model') {
			s.target_url = null;
			s.target_params = null;
			s.target_model = s.target_model || '';
		} else {
			s.target_model = null;
			s.target_ref = null;
			s.target_url = s.target_url ?? '';
		}
		next[i] = s;
		draft.steps = next;
	}

	// When target_model changes, convert step-owned scaffolds to the new model's type.
	// Preserves name/description/ref; resets type-specific fields (framework/matrix/category).
	function changeTargetModel(i: number, newModel: string | null) {
		if (!draft) return;
		const step = draft.steps[i];
		setStepField(i, {
			target_model: newModel,
			// Drop focus if it pointed to a scaffold whose type no longer matches the new model
			target_ref: (() => {
				if (!step.target_ref) return null;
				const sc = draft!.scaffolded_objects.find((x) => x.ref === step.target_ref);
				if (!sc) return null;
				const newType = MODEL_TO_TYPE[newModel ?? ''];
				return newType && sc.type === newType ? step.target_ref : null;
			})()
		});
		const newType = MODEL_TO_TYPE[newModel ?? ''];
		if (!newType) return;
		// Convert step-owned scaffolds whose type doesn't match
		const scaffolds = [...draft.scaffolded_objects];
		let mutated = false;
		for (let idx = 0; idx < scaffolds.length; idx++) {
			const sc = scaffolds[idx];
			if (sc.step_ref_id === step.key && sc.type !== newType) {
				const reset = defaultsForType(newType, sc.name ?? safeTranslate(newType));
				scaffolds[idx] = {
					...reset,
					ref: sc.ref,
					description: sc.description,
					step_ref_id: sc.step_ref_id
				};
				mutated = true;
			}
		}
		if (mutated) draft.scaffolded_objects = scaffolds;
	}

	function setStepField(i: number, patch: Partial<Step>) {
		if (!draft) return;
		const next = [...draft.steps];
		const oldKey = next[i].key;
		next[i] = { ...next[i], ...patch };
		draft.steps = next;
		// If key changed, reassign step_ref_id on owned scaffolds
		if (patch.key !== undefined && patch.key !== oldKey) {
			const newKey = patch.key as string;
			draft.scaffolded_objects = draft.scaffolded_objects.map((s) =>
				s.step_ref_id === oldKey ? { ...s, step_ref_id: newKey } : s
			);
		}
	}

	function nextStepKey(): string {
		if (!draft) return 'step_1';
		const taken = new Set(draft.steps.map((s) => s.key));
		let n = draft.steps.length + 1;
		while (taken.has(`step_${n}`)) n++;
		return `step_${n}`;
	}

	function addStep() {
		insertStep(draft?.steps.length ?? 0);
	}

	function insertStep(at: number) {
		if (!draft) return;
		const newStep: Step = {
			id: null,
			key: nextStepKey(),
			title: safeTranslate('newStep'),
			description: '',
			target_model: null
		};
		const next = [...draft.steps];
		next.splice(Math.max(0, Math.min(at, next.length)), 0, newStep);
		draft.steps = next;
	}

	function removeStep(i: number) {
		if (!draft) return;
		const step = draft.steps[i];
		const owned = draft.scaffolded_objects.filter((s) => s.step_ref_id === step.key);
		const msg =
			owned.length > 0
				? m.lbPresetDeleteStepWithObjectsConfirm({
						title: step.title,
						count: owned.length,
						s: owned.length === 1 ? '' : 's'
					})
				: m.lbPresetDeleteStepConfirm({ title: step.title });
		if (!confirm(msg)) return;
		// Drop owned scaffolds
		const ownedRefs = new Set(owned.map((s) => s.ref).filter(Boolean));
		draft.scaffolded_objects = draft.scaffolded_objects.filter((s) => s.step_ref_id !== step.key);
		// Clear target_ref on any step that focused on a deleted scaffold
		draft.steps = draft.steps
			.filter((_, idx) => idx !== i)
			.map((s) => (s.target_ref && ownedRefs.has(s.target_ref) ? { ...s, target_ref: null } : s));
	}

	function moveStep(i: number, dir: -1 | 1) {
		if (!draft) return;
		const next = [...draft.steps];
		const j = i + dir;
		if (j < 0 || j >= next.length) return;
		[next[i], next[j]] = [next[j], next[i]];
		draft.steps = next;
	}

	// --- Scaffold ops ---
	function generateRef(seed: string): string {
		if (!draft) return seed;
		const base = (seed || 'obj').replace(/[^A-Za-z0-9_]+/g, '_').toLowerCase() || 'obj';
		const taken = new Set(draft.scaffolded_objects.map((s) => s.ref).filter(Boolean));
		if (!taken.has(base)) return base;
		let n = 2;
		while (taken.has(`${base}_${n}`)) n++;
		return `${base}_${n}`;
	}

	function defaultsForType(type: string, name: string): Scaffold {
		const base: Scaffold = { type, ref: '', name, description: '' };
		if (type === 'compliance_assessment')
			return { ...base, framework: '', implementation_groups: [] };
		if (
			type === 'risk_assessment' ||
			type === 'business_impact_analysis' ||
			type === 'ebios_rm_study'
		)
			return { ...base, risk_matrix: '' };
		if (type === 'findings_assessment') return { ...base, category: 'pentest' };
		if (type === 'asset') return { ...base, asset_type: 'SP' };
		if (type === 'project') return { ...base, kind: 'project' };
		if (type === 'responsibility_matrix') return { ...base, matrix_preset: 'raci' };
		return base;
	}

	function updateScaffoldByIndex(idx: number, patch: Partial<Scaffold>) {
		if (!draft) return;
		const scaffolds = [...draft.scaffolded_objects];
		const oldRef = scaffolds[idx].ref;
		scaffolds[idx] = { ...scaffolds[idx], ...patch };
		draft.scaffolded_objects = scaffolds;
		// Propagate ref change to any step focused on it
		if (patch.ref !== undefined && patch.ref !== oldRef && oldRef) {
			const newRef = patch.ref;
			draft.steps = draft.steps.map((s) =>
				s.target_ref === oldRef ? { ...s, target_ref: newRef ?? null } : s
			);
		}
	}

	function removeScaffoldByIndex(idx: number) {
		if (!draft) return;
		const removed = draft.scaffolded_objects[idx];
		draft.scaffolded_objects = draft.scaffolded_objects.filter((_, i) => i !== idx);
		if (removed.ref) {
			draft.steps = draft.steps.map((s) =>
				s.target_ref === removed.ref ? { ...s, target_ref: null } : s
			);
		}
	}

	function indexOfScaffold(scaffold: Scaffold): number {
		if (!draft) return -1;
		return draft.scaffolded_objects.indexOf(scaffold);
	}

	// All scaffolds owned by this step (focused or not).
	function scaffoldsForStep(step: Step): Scaffold[] {
		if (!draft) return [];
		return draft.scaffolded_objects.filter((s) => s.step_ref_id === step.key);
	}

	// Cross-step focus candidates: scaffolds matching the step's target_model whose
	// step_ref_id is some OTHER step (or unset). The user picks from this dropdown
	// to focus on a scaffold "owned" by another step (e.g. iso27001-full's iso_audit
	// referenced by 3 different steps).
	function crossStepCandidates(step: Step): Scaffold[] {
		if (!draft) return [];
		const type = MODEL_TO_TYPE[step.target_model ?? ''];
		if (!type) return [];
		return draft.scaffolded_objects.filter(
			(s) => s.type === type && s.ref && s.step_ref_id !== step.key
		);
	}

	function addObjectToStep(stepIdx: number) {
		if (!draft) return;
		const step = draft.steps[stepIdx];
		const type = MODEL_TO_TYPE[step.target_model ?? ''];
		if (!type) return;
		const ref = generateRef(`${step.key}_${type}`);
		const sc: Scaffold = {
			...defaultsForType(type, safeTranslate(type)),
			ref,
			step_ref_id: step.key
		};
		draft.scaffolded_objects = [...draft.scaffolded_objects, sc];
		// Auto-focus the first added object if no focus is set yet (covers the
		// common "create one and open it" case in a single click).
		if (!step.target_ref) {
			setStepField(stepIdx, { target_ref: ref });
		}
	}

	// Candidate refs to focus on given a target_model — across ALL scaffolds in the preset
	function focusCandidates(targetModel: string | null | undefined): Scaffold[] {
		if (!draft) return [];
		const type = MODEL_TO_TYPE[targetModel ?? ''];
		if (!type) return [];
		return draft.scaffolded_objects.filter((s) => s.type === type && s.ref);
	}

	function selectedFramework(libraryUrn: string | undefined) {
		// scaffold.framework holds a *library* URN; look up the Framework whose
		// library has that URN to access implementation_groups_definition.
		if (!libraryUrn) return undefined;
		return data.frameworkDetails.find((f: any) => f?.library?.urn === libraryUrn);
	}

	function paramsToRows(
		p: Record<string, any> | null | undefined
	): Array<{ k: string; v: string }> {
		if (!p) return [];
		return Object.entries(p).map(([k, v]) => ({
			k,
			v: Array.isArray(v) ? v.join(',') : String(v)
		}));
	}
	function rowsToParams(rows: Array<{ k: string; v: string }>): Record<string, any> | null {
		const out: Record<string, any> = {};
		for (const { k, v } of rows) {
			if (!k) continue;
			out[k] = v.includes(',')
				? v
						.split(',')
						.map((x) => x.trim())
						.filter(Boolean)
				: v;
		}
		return Object.keys(out).length ? out : null;
	}

	// Param rows are edited in local state (keyed by step key) so an empty,
	// not-yet-filled row can exist while typing — rowsToParams drops empty
	// keys, so deriving straight from target_params made "Add param" a no-op.
	let paramRows = $state<Record<string, Array<{ k: string; v: string }>>>({});

	function displayParamRows(step: Step): Array<{ k: string; v: string }> {
		return paramRows[step.key] ?? paramsToRows(step.target_params);
	}

	function setParamRows(i: number, step: Step, rows: Array<{ k: string; v: string }>) {
		paramRows = { ...paramRows, [step.key]: rows };
		setStepField(i, { target_params: rowsToParams(rows) });
	}
</script>

{#snippet scaffoldFields(scaffold: Scaffold, idx: number)}
	{#if scaffold.type === 'compliance_assessment'}
		<label class="flex flex-col gap-1 text-sm md:col-span-2">
			<span class="text-xs text-surface-600-400">{m.framework()}</span>
			<select
				class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.framework ?? ''}
				onchange={(e) =>
					updateScaffoldByIndex(idx, { framework: (e.target as HTMLSelectElement).value })}
			>
				<option value="">{m.lbPresetSelectFramework()}</option>
				{#each data.frameworks as fw (fw.id)}
					<option value={fw.urn}>{fw.name}</option>
				{/each}
			</select>
		</label>
		{#if scaffold.framework}
			{@const fw = selectedFramework(scaffold.framework)}
			{#if fw?.implementation_groups_definition?.length}
				<div class="md:col-span-2">
					<span class="text-xs text-surface-600-400 block mb-1.5">{m.implementationGroups()}</span>
					<div class="flex flex-wrap gap-1.5">
						{#each fw.implementation_groups_definition as ig (ig.ref_id)}
							{@const checked = scaffold.implementation_groups?.includes(ig.ref_id)}
							<label
								class="inline-flex items-center gap-1.5 text-xs rounded-full px-2.5 py-1 border transition-colors cursor-pointer {checked
									? 'bg-blue-50 border-blue-300 text-blue-700'
									: 'bg-surface-50-950 border-surface-200-800 text-surface-600-400 hover:border-surface-300-700'}"
							>
								<input
									type="checkbox"
									class="sr-only"
									{checked}
									onchange={(e) => {
										const c = (e.target as HTMLInputElement).checked;
										const cur = scaffold.implementation_groups ?? [];
										const next = c
											? [...cur, ig.ref_id]
											: cur.filter((x: string) => x !== ig.ref_id);
										updateScaffoldByIndex(idx, { implementation_groups: next });
									}}
								/>
								<i class="fa-solid {checked ? 'fa-check' : 'fa-plus'} text-[9px]"></i>
								<span class="font-mono">{ig.ref_id}</span>
								<span>— {ig.name}</span>
							</label>
						{/each}
					</div>
				</div>
			{/if}
		{/if}
	{:else if scaffold.type === 'risk_assessment' || scaffold.type === 'business_impact_analysis' || scaffold.type === 'ebios_rm_study'}
		<label class="flex flex-col gap-1 text-sm md:col-span-2">
			<span class="text-xs text-surface-600-400">{m.riskMatrix()}</span>
			<select
				class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.risk_matrix ?? ''}
				onchange={(e) =>
					updateScaffoldByIndex(idx, { risk_matrix: (e.target as HTMLSelectElement).value })}
			>
				<option value="">{m.lbPresetSelectMatrix()}</option>
				{#each data.riskMatrices as rm (rm.id)}
					<option value={rm.urn}>{rm.name}</option>
				{/each}
			</select>
		</label>
	{:else if scaffold.type === 'findings_assessment'}
		<label class="flex flex-col gap-1 text-sm">
			<span class="text-xs text-surface-600-400">{m.category()}</span>
			<select
				class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.category ?? 'pentest'}
				onchange={(e) =>
					updateScaffoldByIndex(idx, { category: (e.target as HTMLSelectElement).value })}
			>
				{#each FINDINGS_CATEGORIES as c (c)}
					<option value={c}>{safeTranslate(c)}</option>
				{/each}
			</select>
		</label>
	{:else if scaffold.type === 'asset'}
		<label class="flex flex-col gap-1 text-sm">
			<span class="text-xs text-surface-600-400">{m.lbPresetAssetType()}</span>
			<select
				class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.asset_type ?? 'SP'}
				onchange={(e) =>
					updateScaffoldByIndex(idx, { asset_type: (e.target as HTMLSelectElement).value })}
			>
				{#each ASSET_TYPES as t (t.value)}
					<option value={t.value}>{safeTranslate(t.labelKey)}</option>
				{/each}
			</select>
		</label>
	{:else if scaffold.type === 'applied_control'}
		<label class="flex flex-col gap-1 text-sm">
			<span class="text-xs text-surface-600-400">{m.category()}</span>
			<select
				class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.category ?? ''}
				onchange={(e) =>
					updateScaffoldByIndex(idx, { category: (e.target as HTMLSelectElement).value })}
			>
				<option value="">{m.lbPresetAnyCategory()}</option>
				{#each APPLIED_CONTROL_CATEGORIES as c (c)}
					<option value={c}>{safeTranslate(c)}</option>
				{/each}
			</select>
		</label>
	{:else if scaffold.type === 'project'}
		<label class="flex flex-col gap-1 text-sm">
			<span class="text-xs text-surface-600-400">{m.kind()}</span>
			<select
				class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.kind ?? 'project'}
				onchange={(e) =>
					updateScaffoldByIndex(idx, { kind: (e.target as HTMLSelectElement).value })}
			>
				{#each PROJECT_KINDS as k (k)}
					<option value={k}>{safeTranslate(k)}</option>
				{/each}
			</select>
		</label>
	{:else if scaffold.type === 'responsibility_matrix'}
		<label class="flex flex-col gap-1 text-sm">
			<span class="text-xs text-surface-600-400">{m.lbPresetMatrixPreset()}</span>
			<select
				class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.matrix_preset ?? 'raci'}
				onchange={(e) =>
					updateScaffoldByIndex(idx, { matrix_preset: (e.target as HTMLSelectElement).value })}
			>
				{#each MATRIX_PRESETS as p (p)}
					<option value={p}>{p.toUpperCase()}</option>
				{/each}
			</select>
		</label>
	{:else if scaffold.type === 'security_exception'}
		<label class="flex flex-col gap-1 text-sm">
			<span class="text-xs text-surface-600-400">{m.severity()}</span>
			<select
				class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.severity === undefined ? '' : String(scaffold.severity)}
				onchange={(e) => {
					const v = (e.target as HTMLSelectElement).value;
					updateScaffoldByIndex(idx, { severity: v === '' ? undefined : Number(v) });
				}}
			>
				<option value="">{m.lbPresetUndefined()}</option>
				{#each SECURITY_EXCEPTION_SEVERITIES as s (s.value)}
					<option value={String(s.value)}>{safeTranslate(s.labelKey)}</option>
				{/each}
			</select>
		</label>
	{/if}
{/snippet}

{#if isReadOnly}
	<div class="p-6">
		<div class="bg-yellow-50 border border-yellow-300 rounded p-4">
			<p class="font-semibold">{m.lbPresetReadOnlyTitle()}</p>
			<p class="text-sm mt-1">
				{m.lbPresetReadOnlyForkPrefix()}
				<a href="/experimental/library-builder/{data.draft.id}" class="underline"
					>{m.lbPresetEditorHomeLink()}</a
				>{m.lbPresetReadOnlyForkSuffix()}
			</p>
		</div>
	</div>
{:else if loading}
	<div class="p-6">{m.lbPresetLoadingDraft()}</div>
{:else if !draft}
	<div class="p-6 text-red-700">{m.lbPresetFailedToLoadDraftShort()}</div>
{:else}
	{#if needsProjectManagement}
		<div
			class="mb-3 flex items-start gap-2.5 rounded-lg border border-amber-300 bg-amber-50 px-3.5 py-2.5 text-sm text-amber-800"
		>
			<i class="fa-solid fa-triangle-exclamation mt-0.5 text-amber-500"></i>
			<span>
				{m.lbPresetProjectMgmtWarnPart1()}
				<span class="font-medium">{m.lbPresetProjectMgmtFeatureName()}</span>
				{m.lbPresetProjectMgmtWarnPart2()}
				<span class="font-mono text-xs">feature_flags</span>
				{m.lbPresetProjectMgmtWarnPart3()}
				<span class="font-mono text-xs">project_management</span>{m.lbPresetProjectMgmtWarnPart4()}
			</span>
		</div>
	{/if}
	<div class="bg-surface-50-950 rounded-lg shadow-sm border border-surface-200-800 overflow-hidden">
		<!-- Sticky toolbar -->
		<div class="sticky top-0 z-40 bg-surface-50-950 border-b border-surface-200-800 px-4 py-2.5">
			<div class="flex items-center gap-3 flex-wrap">
				<a
					href="/experimental/library-builder/{data.draft.id}"
					class="text-sm text-surface-500 hover:text-surface-600-400 transition-colors shrink-0"
					title={m.lbPresetBackToList()}
				>
					<i class="fa-solid fa-arrow-left"></i>
				</a>
				<div class="h-4 w-px bg-surface-200-800 shrink-0"></div>

				<!-- Status pill: the library-draft document is the single draft
				     layer; publishing happens on the library page. -->
				{#if dirty}
					<span
						class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 inline-flex items-center gap-1"
						title={m.lbPresetUnsavedChangesTitle()}
					>
						<i class="fa-solid fa-pen-nib text-[10px]"></i>
						{m.lbPresetUnsavedChanges()}
					</span>
				{:else}
					<span
						class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 inline-flex items-center gap-1"
						title={m.lbPresetSavedTooltip()}
					>
						<i class="fa-solid fa-circle-check text-[10px]"></i>
						{m.lbPresetSavedToDraft()}
					</span>
				{/if}

				<!-- Spacer -->
				<div class="ml-auto"></div>

				<!-- Save -->
				<button
					type="button"
					class="shrink-0 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors inline-flex items-center gap-1.5 {saving
						? 'bg-gray-400 text-white cursor-wait'
						: dirty
							? 'bg-gray-700 text-white hover:bg-gray-800'
							: 'bg-surface-100-900 text-surface-500 cursor-not-allowed'}"
					disabled={!dirty || saving}
					onclick={save}
					title={m.lbPresetSaveTooltip()}
				>
					{#if saving}
						<i class="fa-solid fa-circle-notch fa-spin text-[10px]"></i> {m.lbPresetSaving()}
					{:else}
						<i class="fa-solid fa-floppy-disk text-[10px]"></i> {m.save()}
					{/if}
				</button>

				<!-- Revert unsaved edits (inline confirm) -->
				{#if dirty}
					{#if confirmDiscard}
						<span class="shrink-0 text-xs text-red-600 font-medium"
							>{m.lbPresetRevertConfirm()}</span
						>
						<button
							type="button"
							class="shrink-0 text-xs font-medium px-2 py-1 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition-colors"
							onclick={discard}
						>
							{m.lbPresetYesRevert()}
						</button>
						<button
							type="button"
							class="shrink-0 text-xs text-surface-600-400 px-2 py-1 hover:text-surface-700-300"
							onclick={() => (confirmDiscard = false)}
						>
							{m.cancel()}
						</button>
					{:else}
						<button
							type="button"
							class="shrink-0 text-xs font-medium px-3 py-1.5 rounded-lg text-surface-600-400 hover:text-red-600 hover:bg-red-50 transition-colors inline-flex items-center gap-1.5"
							onclick={() => (confirmDiscard = true)}
							disabled={saving}
							title={m.lbPresetRevertTooltip()}
						>
							<i class="fa-solid fa-rotate-left text-[10px]"></i>
							{m.lbPresetRevert()}
						</button>
					{/if}
				{/if}
			</div>
		</div>

		<div class="max-w-4xl mx-auto px-6 py-8 space-y-8">
			{#if errorMsg}
				<div
					class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg text-sm flex items-start gap-2"
				>
					<i class="fa-solid fa-triangle-exclamation mt-0.5 text-red-600"></i>
					<span class="flex-1">{errorMsg}</span>
				</div>
			{/if}

			<!-- Preset metadata: inline-editable title + description -->
			<div class="space-y-1">
				<input
					type="text"
					bind:value={draft.journey_meta.name}
					placeholder={m.lbPresetNamePlaceholder()}
					class="w-full text-2xl font-bold bg-transparent border-0 border-b-2 border-transparent hover:border-surface-300-700 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors py-1"
				/>
				<textarea
					bind:value={draft.journey_meta.description}
					placeholder={m.lbPresetDescriptionPlaceholder()}
					rows="2"
					class="w-full text-sm text-surface-600-400 bg-transparent border-0 border-b border-transparent hover:border-surface-300-700 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none py-1"
				></textarea>
				<details class="pt-1" open={Object.keys(draft.journey_meta.translations).length > 0}>
					<summary class="text-xs text-surface-500 cursor-pointer select-none">
						<i class="fa-solid fa-language mr-1" aria-hidden="true"></i>{m.translations()}
					</summary>
					<div class="mt-2">
						<TranslationsEditor
							bind:translations={draft.journey_meta.translations}
							fields={[
								{ key: 'name', label: m.name() },
								{ key: 'description', label: m.description(), textarea: true }
							]}
							baseLang={data.draft.locale ?? 'en'}
						/>
					</div>
				</details>
			</div>

			<!-- Steps -->
			<section class="space-y-4">
				<div class="flex items-end justify-between">
					<div>
						<h2 class="text-base font-semibold text-surface-800-200">{m.lbPresetSteps()}</h2>
						<p class="text-xs text-surface-600-400 mt-0.5">
							{m.lbPresetStepsHelp()}
						</p>
					</div>
					<button
						type="button"
						class="text-xs font-medium px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors inline-flex items-center gap-1.5"
						onclick={addStep}
					>
						<i class="fa-solid fa-plus text-[10px]"></i>
						{m.lbPresetAddStep()}
					</button>
				</div>

				{#if draft.steps.length === 0}
					<div
						class="border-2 border-dashed border-surface-200-800 rounded-lg p-10 text-center text-sm text-surface-500"
					>
						<i class="fa-solid fa-list-check text-3xl mb-3 text-gray-300 block"></i>
						{m.lbPresetNoStepsPrefix()}
						<span class="font-medium text-surface-600-400">{m.lbPresetAddStep()}</span>
						{m.lbPresetNoStepsSuffix()}
					</div>
				{/if}

				<div class="flex flex-col">
					{#snippet inserter(at: number)}
						<button
							type="button"
							class="group w-full flex items-center justify-center py-1.5 my-0.5 transition-opacity opacity-30 hover:opacity-100 focus-visible:opacity-100"
							onclick={() => insertStep(at)}
							title={m.lbPresetInsertStep()}
							aria-label={m.lbPresetInsertStepHere()}
						>
							<span class="h-px flex-1 bg-blue-200 group-hover:bg-blue-400 transition-colors"
							></span>
							<span
								class="mx-2 text-[11px] font-medium text-blue-700 px-2 py-0.5 rounded-full bg-blue-50 group-hover:bg-blue-100 transition-colors inline-flex items-center gap-1"
							>
								<i class="fa-solid fa-plus text-[9px]"></i>
								{m.lbPresetInsertStep()}
							</span>
							<span class="h-px flex-1 bg-blue-200 group-hover:bg-blue-400 transition-colors"
							></span>
						</button>
					{/snippet}

					{#if draft.steps.length > 0}
						{@render inserter(0)}
					{/if}

					{#each draft.steps as step, i (i)}
						{@const ptrMode = getPointerMode(step)}
						{@const ownedScaffolds = scaffoldsForStep(step)}
						{@const candidates = focusCandidates(step.target_model)}
						{@const stepBorders = [
							'border-l-blue-400',
							'border-l-violet-400',
							'border-l-amber-400',
							'border-l-emerald-400'
						]}
						{@const depthColor = stepBorders[i % stepBorders.length]}
						<div
							class="bg-surface-50-950 rounded-lg shadow-sm border border-surface-200-800 border-l-4 {depthColor} overflow-hidden"
						>
							<!-- Header -->
							<div class="flex items-start gap-3 p-4 border-b border-surface-100-900">
								<div class="flex flex-col items-center gap-1 shrink-0 mt-1">
									<span
										class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-surface-100-900 text-surface-700-300 text-xs font-semibold"
									>
										{i + 1}
									</span>
									<button
										type="button"
										class="w-6 h-6 inline-flex items-center justify-center rounded text-xs text-surface-500 hover:text-surface-700-300 hover:bg-surface-100-900 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
										onclick={() => moveStep(i, -1)}
										disabled={i === 0}
										title={m.lbPresetMoveUp()}
										aria-label={m.lbPresetMoveUp()}
									>
										<i class="fa-solid fa-chevron-up"></i>
									</button>
									<button
										type="button"
										class="w-6 h-6 inline-flex items-center justify-center rounded text-xs text-surface-500 hover:text-surface-700-300 hover:bg-surface-100-900 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
										onclick={() => moveStep(i, 1)}
										disabled={i === draft.steps.length - 1}
										title={m.lbPresetMoveDown()}
										aria-label={m.lbPresetMoveDown()}
									>
										<i class="fa-solid fa-chevron-down"></i>
									</button>
								</div>
								<div class="flex-1 min-w-0 space-y-2">
									<input
										type="text"
										value={step.title}
										placeholder={m.lbPresetStepNamePlaceholder()}
										class="w-full text-base font-semibold bg-transparent border-0 border-b-2 border-transparent hover:border-surface-300-700 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors py-0.5"
										oninput={(e) =>
											setStepField(i, { title: (e.target as HTMLInputElement).value })}
									/>
									<textarea
										value={step.description ?? ''}
										placeholder={m.lbPresetDescriptionOptional()}
										rows="2"
										class="w-full text-sm text-surface-600-400 bg-transparent border-0 border-b border-transparent hover:border-surface-200-800 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none py-0.5"
										oninput={(e) =>
											setStepField(i, { description: (e.target as HTMLTextAreaElement).value })}
									></textarea>
									<div class="flex items-center gap-2 text-xs">
										<span class="text-surface-500 font-mono">{m.refId()}</span>
										<input
											type="text"
											value={step.key}
											class="font-mono text-xs bg-surface-50-950 border border-surface-200-800 rounded px-2 py-0.5 focus:bg-surface-50-950 focus:border-blue-400 outline-none transition-colors min-w-0 flex-1 max-w-xs"
											oninput={(e) =>
												setStepField(i, { key: (e.target as HTMLInputElement).value })}
										/>
									</div>
									<details open={Object.keys(step.translations ?? {}).length > 0}>
										<summary class="text-xs text-surface-500 cursor-pointer select-none">
											<i class="fa-solid fa-language mr-1" aria-hidden="true"></i>{m.translations()}
										</summary>
										<div class="mt-2">
											<TranslationsEditor
												bind:translations={
													() => draft!.steps[i].translations ?? {},
													(value) => setStepField(i, { translations: value })
												}
												fields={[
													{ key: 'title', label: m.title() },
													{ key: 'description', label: m.description(), textarea: true }
												]}
												baseLang={data.draft.locale ?? 'en'}
											/>
										</div>
									</details>
								</div>
								<button
									type="button"
									class="w-8 h-8 inline-flex items-center justify-center rounded-lg text-surface-500 hover:text-red-600 hover:bg-red-50 transition-colors"
									onclick={() => removeStep(i)}
									title={m.lbPresetRemoveStep()}
									aria-label={m.lbPresetRemoveStep()}
								>
									<i class="fa-solid fa-trash text-xs"></i>
								</button>
							</div>

							<!-- Body: pointer + scaffolded objects -->
							<div class="px-4 pb-4 pt-3 flex flex-col gap-4">
								<!-- Pointer -->
								<div class="bg-surface-50-950/60 border border-surface-100-900 rounded-lg p-3">
									<div
										class="text-[11px] font-medium text-surface-600-400 uppercase tracking-wider mb-2 flex items-center gap-1.5"
									>
										<i class="fa-solid fa-arrow-right-to-bracket text-[10px]"></i>
										{m.lbPresetPointer()}<span
											class="text-surface-500 normal-case font-normal tracking-normal"
										>
											{m.lbPresetPointerHint()}</span
										>
									</div>
									<div
										class="inline-flex rounded-lg border border-surface-200-800 bg-surface-50-950 overflow-hidden text-xs mb-3"
									>
										<label
											class="px-3 py-1.5 cursor-pointer transition-colors {ptrMode === 'none'
												? 'bg-gray-700 text-white'
												: 'text-surface-600-400 hover:bg-surface-50-950'}"
										>
											<input
												type="radio"
												name={`ptr-${i}`}
												class="sr-only"
												checked={ptrMode === 'none'}
												onchange={() => setPointerMode(i, 'none')}
											/>
											{m.lbPresetNone()}
										</label>
										<label
											class="px-3 py-1.5 cursor-pointer border-l border-surface-200-800 transition-colors {ptrMode ===
											'model'
												? 'bg-gray-700 text-white'
												: 'text-surface-600-400 hover:bg-surface-50-950'}"
										>
											<input
												type="radio"
												name={`ptr-${i}`}
												class="sr-only"
												checked={ptrMode === 'model'}
												onchange={() => setPointerMode(i, 'model')}
											/>
											<i class="fa-solid fa-list-ul mr-1 text-[10px]"></i>
											{m.model()}
										</label>
										<label
											class="px-3 py-1.5 cursor-pointer border-l border-surface-200-800 transition-colors {ptrMode ===
											'url'
												? 'bg-gray-700 text-white'
												: 'text-surface-600-400 hover:bg-surface-50-950'}"
										>
											<input
												type="radio"
												name={`ptr-${i}`}
												class="sr-only"
												checked={ptrMode === 'url'}
												onchange={() => setPointerMode(i, 'url')}
											/>
											<i class="fa-solid fa-link mr-1 text-[10px]"></i>
											{m.lbPresetUrlReport()}
										</label>
									</div>
									{#if ptrMode === 'model'}
										{@const seedType = MODEL_TO_TYPE[step.target_model ?? '']}
										{@const crossCands = crossStepCandidates(step)}
										<div class="space-y-3">
											<label class="flex flex-col gap-1">
												<span class="text-xs text-surface-600-400">{m.model()}</span>
												<select
													class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
													value={step.target_model ?? ''}
													onchange={(e) =>
														changeTargetModel(i, (e.target as HTMLSelectElement).value || null)}
												>
													{#each ALL_MODELS as tm (tm)}
														<option value={tm}
															>{tm ? safeTranslate(tm) : m.lbPresetPickOne()}</option
														>
													{/each}
												</select>
											</label>

											{#if seedType}
												<div>
													<div
														class="text-[11px] font-medium text-surface-600-400 uppercase tracking-wider mb-2 flex items-center gap-1.5"
													>
														<i class="fa-solid fa-cubes text-[10px]"></i>
														{m.lbPresetObjectsToCreate()}
														<span class="text-surface-500 normal-case font-normal tracking-normal">
															{m.lbPresetObjectsToCreateHint()}
														</span>
													</div>

													<!-- "Open the list" focus option -->
													<label
														class="flex items-center gap-2 text-xs px-3 py-2 rounded-lg border {!step.target_ref
															? 'border-blue-300 bg-blue-50 text-blue-800'
															: 'border-surface-200-800 hover:bg-surface-50-950'} cursor-pointer mb-2"
													>
														<input
															type="radio"
															name={`focus-${i}`}
															checked={!step.target_ref}
															onchange={() => setStepField(i, { target_ref: null })}
														/>
														{m.lbPresetOpenList()}
													</label>

													<div class="space-y-2">
														{#each ownedScaffolds as scaffold (indexOfScaffold(scaffold))}
															{@const idx = indexOfScaffold(scaffold)}
															{@const focused = step.target_ref === scaffold.ref}
															<div
																class="bg-surface-50-950 border rounded-lg p-3 {focused
																	? 'border-blue-300 shadow-sm'
																	: 'border-surface-200-800'}"
															>
																<div class="flex items-center gap-2 mb-2">
																	<input
																		type="radio"
																		name={`focus-${i}`}
																		checked={focused}
																		onchange={() => {
																			if (!scaffold.ref) {
																				const ref = generateRef(`${step.key}_${scaffold.type}`);
																				updateScaffoldByIndex(idx, { ref });
																				setStepField(i, { target_ref: ref });
																			} else {
																				setStepField(i, { target_ref: scaffold.ref });
																			}
																		}}
																	/>
																	<span class="text-xs text-surface-600-400"
																		>{focused
																			? m.lbPresetScaffoldAndOpen()
																			: m.lbPresetScaffold()}</span
																	>
																	<span
																		class="ml-auto text-[10px] uppercase text-surface-500 tracking-wider"
																		>{safeTranslate(scaffold.type)}</span
																	>
																	<button
																		type="button"
																		class="w-7 h-7 inline-flex items-center justify-center rounded-lg text-surface-500 hover:text-red-600 hover:bg-red-50 transition-colors"
																		onclick={() => removeScaffoldByIndex(idx)}
																		title={m.lbPresetRemoveObject()}
																		aria-label={m.lbPresetRemoveObject()}
																	>
																		<i class="fa-solid fa-trash text-[11px]"></i>
																	</button>
																</div>
																<div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
																	<label class="flex flex-col gap-1">
																		<span class="text-xs text-surface-600-400">{m.name()}</span>
																		<input
																			class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
																			type="text"
																			value={scaffold.name ?? ''}
																			oninput={(e) =>
																				updateScaffoldByIndex(idx, {
																					name: (e.target as HTMLInputElement).value
																				})}
																		/>
																	</label>
																	<label class="flex flex-col gap-1">
																		<span class="text-xs text-surface-600-400">{m.refId()}</span>
																		<input
																			class="text-sm font-mono bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
																			type="text"
																			value={scaffold.ref ?? ''}
																			oninput={(e) =>
																				updateScaffoldByIndex(idx, {
																					ref: (e.target as HTMLInputElement).value || undefined
																				})}
																		/>
																	</label>
																	<label class="flex flex-col gap-1 md:col-span-2">
																		<span class="text-xs text-surface-600-400"
																			>{m.description()}</span
																		>
																		<textarea
																			class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors resize-y"
																			rows="2"
																			value={scaffold.description ?? ''}
																			oninput={(e) =>
																				updateScaffoldByIndex(idx, {
																					description: (e.target as HTMLTextAreaElement).value
																				})}
																		></textarea>
																	</label>
																	{@render scaffoldFields(scaffold, idx)}
																</div>
															</div>
														{/each}
													</div>

													<button
														type="button"
														class="mt-2 text-xs font-medium px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors inline-flex items-center gap-1.5"
														onclick={() => addObjectToStep(i)}
													>
														<i class="fa-solid fa-plus text-[10px]"></i>
														{m.lbPresetAddObject({
															type: safeTranslate(seedType)
														})}
													</button>
												</div>
											{/if}

											{#if crossCands.length > 0}
												<label class="flex flex-col gap-1">
													<span class="text-xs text-surface-600-400"
														>{m.lbPresetOpenScaffoldFromOtherStep()}</span
													>
													<select
														class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
														value={crossCands.some((c) => c.ref === step.target_ref)
															? step.target_ref
															: ''}
														onchange={(e) => {
															const v = (e.target as HTMLSelectElement).value || null;
															setStepField(i, { target_ref: v });
														}}
													>
														<option value="">{m.lbPresetNoneOption()}</option>
														{#each crossCands as c (c.ref)}
															<option value={c.ref}>{c.ref} — {c.name}</option>
														{/each}
													</select>
												</label>
											{/if}
										</div>
									{:else if ptrMode === 'url'}
										<div class="space-y-3">
											<label class="flex flex-col gap-1">
												<span class="text-xs text-surface-600-400">{m.lbPresetUrlPathLabel()}</span>
												<input
													class="text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors font-mono"
													type="text"
													value={step.target_url ?? ''}
													oninput={(e) =>
														setStepField(i, {
															target_url: (e.target as HTMLInputElement).value
														})}
												/>
											</label>
											<div>
												<div class="flex items-center justify-between mb-1.5">
													<span class="text-xs text-surface-600-400">{m.lbPresetParams()}</span>
													<button
														type="button"
														class="text-xs text-surface-600-400 hover:text-blue-600 transition-colors inline-flex items-center gap-1"
														onclick={() => {
															// Add an empty row to LOCAL state only; it persists
															// (unlike a rowsToParams round-trip) until keys are typed.
															paramRows = {
																...paramRows,
																[step.key]: [...displayParamRows(step), { k: '', v: '' }]
															};
														}}
													>
														<i class="fa-solid fa-plus text-[9px]"></i>
														{m.lbPresetAddParam()}
													</button>
												</div>
												{#each displayParamRows(step) as row, ri (ri)}
													<div class="flex gap-2 mb-1.5">
														<input
															class="flex-1 text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors font-mono"
															placeholder={m.lbPresetParamKeyPlaceholder()}
															value={row.k}
															oninput={(e) => {
																const rows = displayParamRows(step).map((r) => ({ ...r }));
																rows[ri].k = (e.target as HTMLInputElement).value;
																setParamRows(i, step, rows);
															}}
														/>
														<input
															class="flex-1 text-sm bg-surface-50-950 border border-surface-200-800 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
															placeholder={m.lbPresetParamValuePlaceholder()}
															value={row.v}
															oninput={(e) => {
																const rows = displayParamRows(step).map((r) => ({ ...r }));
																rows[ri].v = (e.target as HTMLInputElement).value;
																setParamRows(i, step, rows);
															}}
														/>
														<button
															type="button"
															class="w-8 h-8 inline-flex items-center justify-center rounded-lg text-surface-500 hover:text-red-600 hover:bg-red-50 transition-colors"
															onclick={() => {
																const rows = displayParamRows(step).filter((_, x) => x !== ri);
																setParamRows(i, step, rows);
															}}
															title={m.lbPresetRemoveParam()}
															aria-label={m.lbPresetRemoveParam()}
														>
															<i class="fa-solid fa-xmark text-xs"></i>
														</button>
													</div>
												{/each}
											</div>
										</div>
									{/if}
								</div>
							</div>
						</div>
						{@render inserter(i + 1)}
					{/each}
				</div>
			</section>
		</div>
	</div>
{/if}
