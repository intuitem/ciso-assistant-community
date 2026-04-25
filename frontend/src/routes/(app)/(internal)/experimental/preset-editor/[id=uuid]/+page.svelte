<script lang="ts">
	import type { PageData } from './$types';
	import { onMount } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import { pageTitle } from '$lib/utils/stores';
	import { safeTranslate } from '$lib/utils/i18n';

	let { data }: { data: PageData } = $props();
	$pageTitle = `Preset Editor — ${data.preset.name}`;

	type Scaffold = {
		type: string;
		ref?: string;
		name?: string;
		description?: string;
		framework?: string;
		risk_matrix?: string;
		implementation_groups?: string[];
		category?: string;
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
		translations?: Record<string, any>;
	};
	type Draft = {
		journey_meta: { name: string; description: string };
		scaffolded_objects: Scaffold[];
		steps: Step[];
	};
	type PointerMode = 'none' | 'model' | 'url';

	const TYPE_TO_MODEL: Record<string, string> = {
		compliance_assessment: 'compliance-assessments',
		risk_assessment: 'risk-assessments',
		business_impact_analysis: 'business-impact-analysis',
		findings_assessment: 'findings-assessments',
		ebios_rm_study: 'ebios-rm',
		processing: 'processings',
		entity: 'entities',
		task_template: 'task-templates',
		organisation_objective: 'organisation-objectives',
		organisation_issue: 'organisation-issues',
		perimeter: 'perimeters'
	};
	const MODEL_TO_TYPE: Record<string, string> = Object.fromEntries(
		Object.entries(TYPE_TO_MODEL).map(([t, m]) => [m, t])
	);
	const SCAFFOLD_TYPES = Object.keys(TYPE_TO_MODEL);

	const NAV_ONLY_MODELS = [
		'accreditations',
		'actors',
		'applied-controls',
		'assets',
		'evidences',
		'incidents',
		'metric-instances',
		'policies'
	];
	const ALL_MODELS = ['', ...NAV_ONLY_MODELS, ...Object.values(TYPE_TO_MODEL)].sort((a, b) =>
		a.localeCompare(b)
	);

	const FINDINGS_CATEGORIES = ['pentest', 'audit', 'review', 'other'];

	let draft: Draft | null = $state(null);
	let initialJson = $state('');
	let loading = $state(true);
	let saving = $state(false);
	let publishing = $state(false);
	let errorMsg = $state('');
	let previewDeletions: any[] = $state([]);
	let showPreview = $state(false);
	let confirmDiscard = $state(false);
	let publishSuccess = $state(false);
	let isReadOnly = $derived(!data.preset.is_user_authored);

	// Per-step "type to add" selection (key = step index)
	let addTypeByStep: Record<number, string> = $state({});

	const dirty = $derived(draft != null && JSON.stringify(draft) !== initialJson);

	beforeNavigate(({ cancel }) => {
		if (dirty && !confirm('You have unsaved changes. Leave anyway?')) cancel();
	});

	onMount(async () => {
		if (isReadOnly) {
			loading = false;
			return;
		}
		await loadDraft();
	});

	async function loadDraft() {
		loading = true;
		errorMsg = '';
		const r = await fetch(`/experimental/preset-editor/${data.preset.id}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ action: 'start-editing' })
		});
		if (!r.ok) {
			errorMsg = `Failed to load draft: ${r.status}`;
			loading = false;
			return;
		}
		const j = await r.json();
		draft = normalize(j.editing_draft);
		initialJson = JSON.stringify(draft);
		loading = false;
	}

	function normalize(d: any): Draft {
		const result: Draft = {
			journey_meta: {
				name: d?.journey_meta?.name ?? '',
				description: d?.journey_meta?.description ?? ''
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
		const r = await fetch(`/experimental/preset-editor/${data.preset.id}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(draft)
		});
		const j = await r.json();
		if (!r.ok) {
			errorMsg = formatError(j);
			saving = false;
			return;
		}
		draft = normalize(j.editing_draft);
		initialJson = JSON.stringify(draft);
		saving = false;
	}

	async function discard() {
		await fetch(`/experimental/preset-editor/${data.preset.id}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ action: 'discard-draft' })
		});
		confirmDiscard = false;
		await loadDraft();
	}

	async function publishPreview() {
		errorMsg = '';
		const r = await fetch(`/experimental/preset-editor/${data.preset.id}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ action: 'publish-preview' })
		});
		const j = await r.json();
		if (!r.ok) {
			errorMsg = formatError(j);
			return;
		}
		previewDeletions = j.deleted_steps ?? [];
		if (previewDeletions.length === 0) {
			await publishConfirmed();
		} else {
			showPreview = true;
		}
	}

	async function publishConfirmed() {
		showPreview = false;
		publishing = true;
		errorMsg = '';
		const r = await fetch(`/experimental/preset-editor/${data.preset.id}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ action: 'publish' })
		});
		const j = await r.json();
		publishing = false;
		if (!r.ok) {
			errorMsg = formatError(j);
			return;
		}
		publishSuccess = true;
		setTimeout(() => (publishSuccess = false), 3000);
		await loadDraft();
	}

	function formatError(j: any): string {
		if (!j) return 'Unknown error';
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

	function addStep() {
		if (!draft) return;
		const key = `step_${draft.steps.length + 1}`;
		draft.steps = [
			...draft.steps,
			{ id: null, key, title: safeTranslate('newStep'), description: '', target_model: null }
		];
	}

	function removeStep(i: number) {
		if (!draft) return;
		const step = draft.steps[i];
		const owned = draft.scaffolded_objects.filter((s) => s.step_ref_id === step.key);
		const msg =
			owned.length > 0
				? `Delete step "${step.title}"? Its ${owned.length} scaffolded object${owned.length === 1 ? '' : 's'} will also be removed.`
				: `Delete step "${step.title}"?`;
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
		return base;
	}

	function addScaffoldToStep(stepIdx: number, type: string) {
		if (!draft) return;
		const step = draft.steps[stepIdx];
		const ref = generateRef(`${step.key}_${type}`);
		const sc: Scaffold = {
			...defaultsForType(type, `New ${safeTranslate(type)}`),
			ref,
			step_ref_id: step.key
		};
		draft.scaffolded_objects = [...draft.scaffolded_objects, sc];
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

	// Scaffolds whose step_ref_id matches this step
	function scaffoldsForStep(step: Step): Scaffold[] {
		if (!draft) return [];
		return draft.scaffolded_objects.filter((s) => s.step_ref_id === step.key);
	}

	// Candidate refs to focus on given a target_model — across ALL scaffolds in the preset
	function focusCandidates(targetModel: string | null | undefined): Scaffold[] {
		if (!draft) return [];
		const type = MODEL_TO_TYPE[targetModel ?? ''];
		if (!type) return [];
		return draft.scaffolded_objects.filter((s) => s.type === type && s.ref);
	}

	function selectedFramework(urn: string | undefined) {
		if (!urn) return undefined;
		return data.frameworks.find((f: any) => f.urn === urn);
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
</script>

{#snippet scaffoldFields(scaffold: Scaffold, idx: number)}
	{#if scaffold.type === 'compliance_assessment'}
		<label class="flex flex-col gap-1 text-sm md:col-span-2">
			<span class="text-xs text-gray-600">Framework</span>
			<select
				class="text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.framework ?? ''}
				onchange={(e) =>
					updateScaffoldByIndex(idx, { framework: (e.target as HTMLSelectElement).value })}
			>
				<option value="">Select a framework…</option>
				{#each data.frameworks as fw (fw.id)}
					<option value={fw.urn}>{fw.name}</option>
				{/each}
			</select>
		</label>
		{#if scaffold.framework}
			{@const fw = selectedFramework(scaffold.framework)}
			{#if fw?.implementation_groups_definition?.length}
				<div class="md:col-span-2">
					<span class="text-xs text-gray-600 block mb-1.5">Implementation groups</span>
					<div class="flex flex-wrap gap-1.5">
						{#each fw.implementation_groups_definition as ig (ig.ref_id)}
							{@const checked = scaffold.implementation_groups?.includes(ig.ref_id)}
							<label
								class="inline-flex items-center gap-1.5 text-xs rounded-full px-2.5 py-1 border transition-colors cursor-pointer {checked
									? 'bg-blue-50 border-blue-300 text-blue-700'
									: 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'}"
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
			<span class="text-xs text-gray-600">Risk matrix</span>
			<select
				class="text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.risk_matrix ?? ''}
				onchange={(e) =>
					updateScaffoldByIndex(idx, { risk_matrix: (e.target as HTMLSelectElement).value })}
			>
				<option value="">Select a matrix…</option>
				{#each data.riskMatrices as rm (rm.id)}
					<option value={rm.urn}>{rm.name}</option>
				{/each}
			</select>
		</label>
	{:else if scaffold.type === 'findings_assessment'}
		<label class="flex flex-col gap-1 text-sm">
			<span class="text-xs text-gray-600">Category</span>
			<select
				class="text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
				value={scaffold.category ?? 'pentest'}
				onchange={(e) =>
					updateScaffoldByIndex(idx, { category: (e.target as HTMLSelectElement).value })}
			>
				{#each FINDINGS_CATEGORIES as c (c)}
					<option value={c}>{safeTranslate(c)}</option>
				{/each}
			</select>
		</label>
	{/if}
{/snippet}

{#if isReadOnly}
	<div class="p-6">
		<div class="bg-yellow-50 border border-yellow-300 rounded p-4">
			<p class="font-semibold">Library-backed presets are read-only.</p>
			<p class="text-sm mt-1">
				Fork this preset (from <a href="/experimental/preset-editor" class="underline"
					>the editor home</a
				>) to create an editable copy.
			</p>
		</div>
	</div>
{:else if loading}
	<div class="p-6">Loading draft…</div>
{:else if !draft}
	<div class="p-6 text-red-700">Failed to load draft.</div>
{:else}
	<div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
		<!-- Sticky toolbar -->
		<div class="sticky top-0 z-40 bg-white border-b border-gray-200 px-4 py-2.5">
			<div class="flex items-center gap-3 flex-wrap">
				<a
					href="/experimental/preset-editor"
					class="text-sm text-gray-400 hover:text-gray-600 transition-colors shrink-0"
					title="Back to preset list"
				>
					<i class="fa-solid fa-arrow-left"></i>
				</a>
				<div class="h-4 w-px bg-gray-200 shrink-0"></div>

				<!-- Status pill -->
				{#if dirty}
					<span
						class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 inline-flex items-center gap-1"
						title="You have unsaved changes."
					>
						<i class="fa-solid fa-pen-nib text-[10px]"></i>
						Unsaved changes
					</span>
				{:else if (data.preset.editing_version ?? 1) > 1}
					<span
						class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 inline-flex items-center gap-1"
						title="Draft matches the published version."
					>
						<i class="fa-solid fa-circle-check text-[10px]"></i>
						Published v{data.preset.editing_version}
					</span>
				{:else}
					<span
						class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 inline-flex items-center gap-1"
						title="Nothing has been published yet."
					>
						<i class="fa-solid fa-file-lines text-[10px]"></i>
						Draft
					</span>
				{/if}

				{#if publishSuccess}
					<span class="shrink-0 text-xs text-green-600 inline-flex items-center gap-1">
						<i class="fa-solid fa-check text-[10px]"></i> Published!
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
							: 'bg-gray-100 text-gray-400 cursor-not-allowed'}"
					disabled={!dirty || saving || publishing}
					onclick={save}
					title="Save draft"
				>
					{#if saving}
						<i class="fa-solid fa-circle-notch fa-spin text-[10px]"></i> Saving…
					{:else}
						<i class="fa-solid fa-floppy-disk text-[10px]"></i> Save
					{/if}
				</button>

				<!-- Discard (inline confirm) -->
				{#if confirmDiscard}
					<span class="shrink-0 text-xs text-red-600 font-medium">Discard draft?</span>
					<button
						type="button"
						class="shrink-0 text-xs font-medium px-2 py-1 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition-colors"
						onclick={discard}
					>
						Yes, discard
					</button>
					<button
						type="button"
						class="shrink-0 text-xs text-gray-500 px-2 py-1 hover:text-gray-700"
						onclick={() => (confirmDiscard = false)}
					>
						Cancel
					</button>
				{:else}
					<button
						type="button"
						class="shrink-0 text-xs font-medium px-3 py-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors inline-flex items-center gap-1.5"
						onclick={() => (confirmDiscard = true)}
						disabled={saving || publishing}
						title="Discard the current draft"
					>
						<i class="fa-solid fa-rotate-left text-[10px]"></i>
						Discard
					</button>
				{/if}

				<!-- Publish -->
				<button
					type="button"
					class="shrink-0 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors inline-flex items-center gap-1.5 {dirty ||
					publishing
						? 'bg-violet-300 text-white cursor-not-allowed'
						: 'bg-violet-600 text-white hover:bg-violet-700'}"
					disabled={dirty || publishing}
					onclick={publishPreview}
					title={dirty ? 'Save the draft first' : 'Publish the draft'}
				>
					{#if publishing}
						<i class="fa-solid fa-circle-notch fa-spin text-[10px]"></i> Publishing…
					{:else}
						<i class="fa-solid fa-rocket text-[10px]"></i> Publish
					{/if}
				</button>
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
					placeholder="Preset name"
					class="w-full text-2xl font-bold bg-transparent border-0 border-b-2 border-transparent hover:border-gray-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors py-1"
				/>
				<textarea
					bind:value={draft.journey_meta.description}
					placeholder="Preset description (optional)"
					rows="2"
					class="w-full text-sm text-gray-500 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none py-1"
				></textarea>
			</div>

			<!-- Steps -->
			<section class="space-y-4">
				<div class="flex items-end justify-between">
					<div>
						<h2 class="text-base font-semibold text-gray-800">Steps</h2>
						<p class="text-xs text-gray-500 mt-0.5">
							A preset is a sequence of steps. Each step can scaffold objects, point to a model or
							URL, or both.
						</p>
					</div>
					<button
						type="button"
						class="text-xs font-medium px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors inline-flex items-center gap-1.5"
						onclick={addStep}
					>
						<i class="fa-solid fa-plus text-[10px]"></i> Add step
					</button>
				</div>

				{#if draft.steps.length === 0}
					<div
						class="border-2 border-dashed border-gray-200 rounded-lg p-10 text-center text-sm text-gray-400"
					>
						<i class="fa-solid fa-list-check text-3xl mb-3 text-gray-300 block"></i>
						No steps yet. Click <span class="font-medium text-gray-600">Add step</span> to begin.
					</div>
				{/if}

				<div class="flex flex-col gap-4">
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
							class="bg-white rounded-lg shadow-sm border border-gray-200 border-l-4 {depthColor} overflow-hidden"
						>
							<!-- Header -->
							<div class="flex items-start gap-3 p-4 border-b border-gray-100">
								<div class="flex flex-col items-center gap-1 shrink-0 mt-1">
									<span
										class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-700 text-xs font-semibold"
									>
										{i + 1}
									</span>
									<button
										type="button"
										class="w-6 h-6 inline-flex items-center justify-center rounded text-xs text-gray-400 hover:text-gray-700 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
										onclick={() => moveStep(i, -1)}
										disabled={i === 0}
										title="Move up"
										aria-label="Move up"
									>
										<i class="fa-solid fa-chevron-up"></i>
									</button>
									<button
										type="button"
										class="w-6 h-6 inline-flex items-center justify-center rounded text-xs text-gray-400 hover:text-gray-700 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
										onclick={() => moveStep(i, 1)}
										disabled={i === draft.steps.length - 1}
										title="Move down"
										aria-label="Move down"
									>
										<i class="fa-solid fa-chevron-down"></i>
									</button>
								</div>
								<div class="flex-1 min-w-0 space-y-2">
									<input
										type="text"
										value={step.title}
										placeholder="Step name"
										class="w-full text-base font-semibold bg-transparent border-0 border-b-2 border-transparent hover:border-gray-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors py-0.5"
										oninput={(e) =>
											setStepField(i, { title: (e.target as HTMLInputElement).value })}
									/>
									<textarea
										value={step.description ?? ''}
										placeholder="Description (optional)"
										rows="2"
										class="w-full text-sm text-gray-600 bg-transparent border-0 border-b border-transparent hover:border-gray-200 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none py-0.5"
										oninput={(e) =>
											setStepField(i, { description: (e.target as HTMLTextAreaElement).value })}
									></textarea>
									<div class="flex items-center gap-2 text-xs">
										<span class="text-gray-400 font-mono">ref_id</span>
										<input
											type="text"
											value={step.key}
											class="font-mono text-xs bg-gray-50 border border-gray-200 rounded px-2 py-0.5 focus:bg-white focus:border-blue-400 outline-none transition-colors min-w-0 flex-1 max-w-xs"
											oninput={(e) =>
												setStepField(i, { key: (e.target as HTMLInputElement).value })}
										/>
									</div>
								</div>
								<button
									type="button"
									class="w-8 h-8 inline-flex items-center justify-center rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
									onclick={() => removeStep(i)}
									title="Remove step"
									aria-label="Remove step"
								>
									<i class="fa-solid fa-trash text-xs"></i>
								</button>
							</div>

							<!-- Body: pointer + scaffolded objects -->
							<div class="px-4 pb-4 pt-3 flex flex-col gap-4">
								<!-- Pointer -->
								<div class="bg-gray-50/60 border border-gray-100 rounded-lg p-3">
									<div
										class="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5"
									>
										<i class="fa-solid fa-arrow-right-to-bracket text-[10px]"></i>
										Pointer<span class="text-gray-400 normal-case font-normal tracking-normal">
											— where the step takes the user</span
										>
									</div>
									<div
										class="inline-flex rounded-lg border border-gray-200 bg-white overflow-hidden text-xs mb-3"
									>
										<label
											class="px-3 py-1.5 cursor-pointer transition-colors {ptrMode === 'none'
												? 'bg-gray-700 text-white'
												: 'text-gray-600 hover:bg-gray-50'}"
										>
											<input
												type="radio"
												name={`ptr-${i}`}
												class="sr-only"
												checked={ptrMode === 'none'}
												onchange={() => setPointerMode(i, 'none')}
											/>
											None
										</label>
										<label
											class="px-3 py-1.5 cursor-pointer border-l border-gray-200 transition-colors {ptrMode ===
											'model'
												? 'bg-gray-700 text-white'
												: 'text-gray-600 hover:bg-gray-50'}"
										>
											<input
												type="radio"
												name={`ptr-${i}`}
												class="sr-only"
												checked={ptrMode === 'model'}
												onchange={() => setPointerMode(i, 'model')}
											/>
											<i class="fa-solid fa-list-ul mr-1 text-[10px]"></i> Model
										</label>
										<label
											class="px-3 py-1.5 cursor-pointer border-l border-gray-200 transition-colors {ptrMode ===
											'url'
												? 'bg-gray-700 text-white'
												: 'text-gray-600 hover:bg-gray-50'}"
										>
											<input
												type="radio"
												name={`ptr-${i}`}
												class="sr-only"
												checked={ptrMode === 'url'}
												onchange={() => setPointerMode(i, 'url')}
											/>
											<i class="fa-solid fa-link mr-1 text-[10px]"></i> URL / report
										</label>
									</div>
									{#if ptrMode === 'model'}
										<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
											<label class="flex flex-col gap-1">
												<span class="text-xs text-gray-600">Model</span>
												<select
													class="text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
													value={step.target_model ?? ''}
													onchange={(e) =>
														setStepField(i, {
															target_model: (e.target as HTMLSelectElement).value || null,
															target_ref: null
														})}
												>
													{#each ALL_MODELS as tm (tm)}
														<option value={tm}>{tm ? safeTranslate(tm) : '— pick one —'}</option>
													{/each}
												</select>
											</label>
											{#if candidates.length > 0}
												<label class="flex flex-col gap-1">
													<span class="text-xs text-gray-600">Focus on (optional)</span>
													<select
														class="text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
														value={step.target_ref ?? ''}
														onchange={(e) =>
															setStepField(i, {
																target_ref: (e.target as HTMLSelectElement).value || null
															})}
													>
														<option value="">— open the list —</option>
														{#each candidates as c (c.ref)}
															<option value={c.ref}>{c.ref} — {c.name}</option>
														{/each}
													</select>
												</label>
											{/if}
										</div>
									{:else if ptrMode === 'url'}
										<div class="space-y-3">
											<label class="flex flex-col gap-1">
												<span class="text-xs text-gray-600"
													>URL (path, e.g. /reports/soa/results)</span
												>
												<input
													class="text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors font-mono"
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
													<span class="text-xs text-gray-600">Params</span>
													<button
														type="button"
														class="text-xs text-gray-500 hover:text-blue-600 transition-colors inline-flex items-center gap-1"
														onclick={() => {
															const rows = paramsToRows(step.target_params);
															rows.push({ k: '', v: '' });
															setStepField(i, { target_params: rowsToParams(rows) });
														}}
													>
														<i class="fa-solid fa-plus text-[9px]"></i> Add param
													</button>
												</div>
												{#each paramsToRows(step.target_params) as row, ri (ri)}
													<div class="flex gap-2 mb-1.5">
														<input
															class="flex-1 text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors font-mono"
															placeholder="key"
															value={row.k}
															oninput={(e) => {
																const rows = paramsToRows(step.target_params);
																rows[ri].k = (e.target as HTMLInputElement).value;
																setStepField(i, { target_params: rowsToParams(rows) });
															}}
														/>
														<input
															class="flex-1 text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
															placeholder="value (comma-separated for lists)"
															value={row.v}
															oninput={(e) => {
																const rows = paramsToRows(step.target_params);
																rows[ri].v = (e.target as HTMLInputElement).value;
																setStepField(i, { target_params: rowsToParams(rows) });
															}}
														/>
														<button
															type="button"
															class="w-8 h-8 inline-flex items-center justify-center rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
															onclick={() => {
																const rows = paramsToRows(step.target_params).filter(
																	(_, x) => x !== ri
																);
																setStepField(i, { target_params: rowsToParams(rows) });
															}}
															title="Remove param"
															aria-label="Remove param"
														>
															<i class="fa-solid fa-xmark text-xs"></i>
														</button>
													</div>
												{/each}
											</div>
										</div>
									{/if}
								</div>

								<!-- Scaffolded objects -->
								<div class="bg-gray-50/60 border border-gray-100 rounded-lg p-3">
									<div
										class="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1.5"
									>
										<i class="fa-solid fa-cubes text-[10px]"></i>
										Scaffolded objects
										<span
											class="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-gray-200 text-gray-700 text-[10px] font-semibold normal-case tracking-normal"
										>
											{ownedScaffolds.length}
										</span>
										<span class="text-gray-400 normal-case font-normal tracking-normal"
											>— created when this preset is applied</span
										>
									</div>
									<div class="flex flex-col gap-3">
										{#each ownedScaffolds as scaffold (indexOfScaffold(scaffold))}
											{@const idx = indexOfScaffold(scaffold)}
											<div class="bg-white border border-gray-200 rounded-lg p-3">
												<div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
													<label class="flex flex-col gap-1">
														<span class="text-xs text-gray-600">Type</span>
														<select
															class="text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
															value={scaffold.type}
															onchange={(e) => {
																const newType = (e.target as HTMLSelectElement).value;
																const prevName = scaffold.name;
																const prevDesc = scaffold.description;
																const prevRef = scaffold.ref;
																const reset = defaultsForType(newType, prevName ?? '');
																updateScaffoldByIndex(idx, {
																	...reset,
																	ref: prevRef,
																	description: prevDesc,
																	step_ref_id: scaffold.step_ref_id
																});
															}}
														>
															{#each SCAFFOLD_TYPES as t (t)}
																<option value={t}>{safeTranslate(t)}</option>
															{/each}
														</select>
													</label>
													<label class="flex flex-col gap-1">
														<span class="text-xs text-gray-600">Name</span>
														<input
															class="text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
															type="text"
															value={scaffold.name ?? ''}
															oninput={(e) =>
																updateScaffoldByIndex(idx, {
																	name: (e.target as HTMLInputElement).value
																})}
														/>
													</label>
													<label class="flex flex-col gap-1 md:col-span-2">
														<span class="text-xs text-gray-600">Description</span>
														<textarea
															class="text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors resize-y"
															rows="2"
															value={scaffold.description ?? ''}
															oninput={(e) =>
																updateScaffoldByIndex(idx, {
																	description: (e.target as HTMLTextAreaElement).value
																})}
														></textarea>
													</label>
													<label class="flex flex-col gap-1">
														<span class="text-xs text-gray-600">ref_id</span>
														<input
															class="text-sm font-mono bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors"
															type="text"
															value={scaffold.ref ?? ''}
															oninput={(e) =>
																updateScaffoldByIndex(idx, {
																	ref: (e.target as HTMLInputElement).value || undefined
																})}
														/>
													</label>
													<div></div>
													{@render scaffoldFields(scaffold, idx)}
													<div class="md:col-span-2 flex justify-end">
														<button
															type="button"
															class="text-xs text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg px-2.5 py-1.5 transition-colors inline-flex items-center gap-1.5"
															onclick={() => removeScaffoldByIndex(idx)}
														>
															<i class="fa-solid fa-trash text-[10px]"></i>
															Remove object
														</button>
													</div>
												</div>
											</div>
										{/each}
										<div class="flex items-center gap-2 pt-1">
											<select
												class="text-sm bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 transition-colors max-w-xs"
												value={addTypeByStep[i] ?? SCAFFOLD_TYPES[0]}
												onchange={(e) => {
													addTypeByStep = {
														...addTypeByStep,
														[i]: (e.target as HTMLSelectElement).value
													};
												}}
											>
												{#each SCAFFOLD_TYPES as t (t)}
													<option value={t}>{safeTranslate(t)}</option>
												{/each}
											</select>
											<button
												type="button"
												class="text-xs font-medium px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors inline-flex items-center gap-1.5"
												onclick={() => addScaffoldToStep(i, addTypeByStep[i] ?? SCAFFOLD_TYPES[0])}
											>
												<i class="fa-solid fa-plus text-[10px]"></i> Add object
											</button>
										</div>
									</div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</section>
		</div>
	</div>

	{#if showPreview}
		<div class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" role="dialog">
			<div class="bg-white rounded-lg shadow-xl max-w-lg w-full overflow-hidden">
				<div class="px-5 py-4 border-b border-gray-100 flex items-center gap-3">
					<div
						class="w-9 h-9 rounded-full bg-amber-100 inline-flex items-center justify-center shrink-0"
					>
						<i class="fa-solid fa-triangle-exclamation text-amber-600"></i>
					</div>
					<div>
						<h3 class="font-semibold text-gray-800">Confirm publish</h3>
						<p class="text-xs text-gray-500 mt-0.5">
							The following step ref_ids will be removed. Existing journeys with state on these
							steps will lose that state on next upgrade.
						</p>
					</div>
				</div>
				<ul class="text-sm max-h-64 overflow-auto divide-y divide-gray-100">
					{#each previewDeletions as d (d.key)}
						<li class="px-5 py-2.5 flex items-center justify-between gap-3">
							<span class="font-mono text-xs bg-gray-100 rounded px-1.5 py-0.5">{d.key}</span>
							<span class="text-xs text-gray-500">
								used in {d.journey_step_count} journey step(s),
								<span class={d.with_user_state ? 'text-amber-600 font-medium' : ''}>
									{d.with_user_state} with user state
								</span>
							</span>
						</li>
					{/each}
				</ul>
				<div class="px-5 py-3 bg-gray-50 flex justify-end gap-2 border-t border-gray-100">
					<button
						type="button"
						class="text-xs font-medium px-3 py-1.5 rounded-lg text-gray-600 hover:bg-gray-200 transition-colors"
						onclick={() => (showPreview = false)}
					>
						Cancel
					</button>
					<button
						type="button"
						class="text-xs font-medium px-3 py-1.5 rounded-lg bg-violet-600 text-white hover:bg-violet-700 transition-colors inline-flex items-center gap-1.5"
						onclick={publishConfirmed}
					>
						<i class="fa-solid fa-rocket text-[10px]"></i> Confirm publish
					</button>
				</div>
			</div>
		</div>
	{/if}
{/if}
