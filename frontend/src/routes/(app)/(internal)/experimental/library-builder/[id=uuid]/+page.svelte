<script lang="ts">
	import { onMount } from 'svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { defaultMatrixObject } from '../builder-helpers';
	import TranslationsEditor from '../TranslationsEditor.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	let { data } = $props();
	let draft: any = $state(data.draft);
	let storedLibraries: any[] = $state(data.storedLibraries ?? []);
	let otherDrafts: any[] = $state(data.otherDrafts ?? []);

	$pageTitle = m.lbDraftPageTitle();

	const OBJECT_TYPES = [
		'frameworks',
		'threats',
		'reference_controls',
		'risk_matrices',
		'requirement_mapping_sets',
		'metric_definitions',
		'preset'
	];

	// Count-aware, localized label per object kind (singular/plural handled
	// by the message). Unknown keys fall back to the raw key.
	const OBJECT_LABELS: Record<string, (args: { count: number }) => string> = {
		frameworks: m.lbCountFrameworks,
		threats: m.lbCountThreats,
		reference_controls: m.lbCountReferenceControls,
		risk_matrices: m.lbCountRiskMatrices,
		requirement_mapping_sets: m.lbCountRequirementMappingSets,
		metric_definitions: m.lbCountMetricDefinitions,
		preset: m.lbCountPreset
	};

	function objectCountLabel(type: string): string {
		const count = objectCount(type);
		const label = OBJECT_LABELS[type];
		return label ? label({ count }) : `${count} ${type.replaceAll('_', ' ')}`;
	}

	let statusMessage = $state('');
	let statusType: 'success' | 'error' | '' = $state('');
	let statusTimeout: ReturnType<typeof setTimeout> | null = null;

	function setStatus(message: string, type: 'success' | 'error') {
		statusMessage = message;
		statusType = type;
		if (statusTimeout) clearTimeout(statusTimeout);
		if (type === 'success') {
			statusTimeout = setTimeout(() => {
				statusMessage = '';
				statusType = '';
			}, 3000);
		}
	}

	const base = () => `/experimental/library-builder/${draft.id}`;

	async function reload() {
		const res = await fetch(`${base()}?action=read`);
		if (res.ok) {
			draft = await res.json();
			resetForms();
		}
	}

	// --- Metadata form ------------------------------------------------------
	let meta = $state({} as Record<string, any>);
	let dependenciesText = $state('');
	let labelsText = $state('');
	let metaTranslations: Record<string, Record<string, string>> = $state({});
	let savingMeta = $state(false);
	let metaBaseline = $state('');

	function metaSnapshot(): string {
		return JSON.stringify({ meta, dependenciesText, labelsText, translations: metaTranslations });
	}

	function serverFormState() {
		return {
			meta: {
				name: draft.name ?? '',
				description: draft.description ?? '',
				packager: draft.packager ?? '',
				ref_id: draft.ref_id ?? '',
				locale: draft.locale ?? 'en',
				version: draft.version ?? 1,
				provider: draft.provider ?? '',
				copyright: draft.copyright ?? '',
				publication_date: draft.publication_date ?? '',
				annotation: draft.annotation ?? ''
			} as Record<string, any>,
			dependenciesText: (draft.dependencies ?? []).join('\n'),
			labelsText: (draft.labels ?? []).join(', '),
			translations: (draft.translations ?? {}) as Record<string, Record<string, string>>
		};
	}

	function resetForms() {
		const server = serverFormState();
		// The draft is refreshed by every card action (imports, object
		// upserts, publish, …). Merge rather than reset: fields the user
		// edited since the last baseline keep their unsaved value, untouched
		// fields take the fresh server value.
		if (metaBaseline) {
			const baseline = JSON.parse(metaBaseline);
			for (const key of Object.keys(server.meta)) {
				if (meta[key] !== baseline.meta[key]) {
					server.meta[key] = meta[key];
				}
			}
			if (dependenciesText !== baseline.dependenciesText) {
				server.dependenciesText = dependenciesText;
			}
			if (labelsText !== baseline.labelsText) {
				server.labelsText = labelsText;
			}
			if (JSON.stringify(metaTranslations) !== JSON.stringify(baseline.translations ?? {})) {
				server.translations = metaTranslations;
			}
		}
		metaBaseline = JSON.stringify(serverFormState());
		meta = server.meta;
		dependenciesText = server.dependenciesText;
		labelsText = server.labelsText;
		metaTranslations = server.translations;
	}
	resetForms();

	let metaDirty = $derived(metaSnapshot() !== metaBaseline);

	async function patch(payload: Record<string, any>): Promise<boolean> {
		const res = await fetch(base(), {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});
		if (!res.ok) {
			const err = await res.json().catch(() => ({}));
			setStatus(JSON.stringify(err), 'error');
			return false;
		}
		await reload();
		return true;
	}

	async function saveMeta() {
		savingMeta = true;
		try {
			const payload: Record<string, any> = {
				...meta,
				version: Number(meta.version) || 1,
				publication_date: meta.publication_date || null,
				provider: meta.provider || null,
				copyright: meta.copyright || null,
				annotation: meta.annotation || null,
				description: meta.description || null,
				translations: metaTranslations,
				dependencies: dependenciesText
					.split('\n')
					.map((s) => s.trim())
					.filter(Boolean),
				labels: labelsText
					.split(',')
					.map((s) => s.trim())
					.filter(Boolean)
			};
			if (draft.identity_locked) {
				delete payload.packager;
				delete payload.ref_id;
			}
			if (await patch(payload)) setStatus(m.lbDraftMetadataSaved(), 'success');
		} finally {
			savingMeta = false;
		}
	}

	// --- Import objects (clone / selective extraction) ----------------------
	let importSource = $state('');
	let importTypes: string[] = $state([]);
	let importPolicy = $state('strip');
	let importOverwrite = $state(false);
	let importing = $state(false);
	let importReport: any = $state(null);

	function toggleType(type: string) {
		importTypes = importTypes.includes(type)
			? importTypes.filter((t) => t !== type)
			: [...importTypes, type];
	}

	async function importObjects() {
		if (!importSource) return;
		importing = true;
		importReport = null;
		try {
			const res = await fetch(base(), {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					action: 'import-objects',
					source: importSource,
					object_types: importTypes.length ? importTypes : undefined,
					default_policy: importPolicy,
					overwrite: importOverwrite
				})
			});
			const result = await res.json();
			if (!res.ok) throw new Error(result.error || JSON.stringify(result));
			importReport = result.report;
			draft = result.draft;
			resetForms();
			setStatus(m.lbDraftObjectsImported(), 'success');
		} catch (e: any) {
			setStatus(safeTranslate(e.message), 'error');
		} finally {
			importing = false;
		}
	}

	// --- Validate / conflicts ------------------------------------------------
	let validation: { errors: string[]; warnings: string[] } | null = $state(null);
	let validating = $state(false);
	let conflicts: any[] = $state([]);

	async function validateDraft() {
		validating = true;
		try {
			const res = await fetch(`${base()}?action=validate`);
			validation = await res.json();
		} finally {
			validating = false;
		}
	}

	async function loadConflicts() {
		const res = await fetch(`${base()}?action=conflicts`);
		if (res.ok) {
			const data_ = await res.json();
			conflicts = data_.conflicts ?? [];
		}
	}

	onMount(() => {
		if (!draft.identity_locked) loadConflicts();
		try {
			const stored = localStorage.getItem(viewKey());
			if (stored === 'simple' || stored === 'full') viewChoice = stored;
		} catch {
			/* storage unavailable */
		}
	});

	// --- Publish --------------------------------------------------------------
	let publishing = $state(false);
	let scoreConflict: any = $state(null);

	async function publish(extra: Record<string, any> = {}) {
		publishing = true;
		scoreConflict = null;
		try {
			// Re-publishing a preset library can delete journey steps that users
			// have progress on — warn once per publish attempt (the internal
			// _presetChecked marker skips the check on bump/strategy retries).
			const { _presetChecked, ...body } = extra;
			if (!_presetChecked && draft.content?.preset && draft.identity_locked) {
				const previewRes = await fetch(base(), {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ action: 'preset-editor-preview' })
				});
				const preview = previewRes.ok ? await previewRes.json() : null;
				const deleted = preview?.deleted_steps ?? [];
				if (deleted.length > 0) {
					const withState = deleted.reduce(
						(sum: number, step: any) => sum + (step.with_user_state ?? 0),
						0
					);
					if (
						!confirm(
							m.lbDraftPublishRemovesSteps({ count: deleted.length }) +
								(withState ? m.lbDraftStepsWithUserProgress({ count: withState }) : '') +
								'. ' +
								m.lbDraftContinueQuestion()
						)
					) {
						return;
					}
				}
			}
			const res = await fetch(base(), {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ action: 'publish', ...body })
			});
			const result = await res.json();
			if (res.ok) {
				setStatus(m.lbDraftPublished({ urn: result.urn, version: result.version }), 'success');
				validation = null;
				await reload();
				return;
			}
			if (result.error === 'libraryVersionOutdated') {
				if (
					confirm(
						m.lbDraftVersionOutdatedConfirm({
							version: draft.version,
							maxVersion: result.max_version,
							nextVersion: result.max_version + 1
						})
					)
				) {
					await publish({ ...extra, bump_version: true, _presetChecked: true });
				}
				return;
			}
			if (result.error === 'versionBumpRequired') {
				if (confirm(m.lbDraftVersionBumpConfirm({ version: draft.version }))) {
					await publish({ ...extra, bump_version: true, _presetChecked: true });
				}
				return;
			}
			if (result.error === 'score_change_detected') {
				scoreConflict = result;
				return;
			}
			if (result.error === 'draftValidationFailed') {
				validation = { errors: result.details ?? [], warnings: [] };
				setStatus(m.lbDraftValidationFailedSeePanel(), 'error');
				return;
			}
			setStatus(result.detail || safeTranslate(result.error) || JSON.stringify(result), 'error');
		} catch (e: any) {
			setStatus(safeTranslate(e.message), 'error');
		} finally {
			publishing = false;
		}
	}

	// --- Export --------------------------------------------------------------
	// Publish (the commit) is required before exporting the canonical
	// artifact; the escape hatch downloads a -draft-suffixed working copy.
	async function commitOnly(bump = false): Promise<boolean> {
		const res = await fetch(base(), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				action: 'publish',
				load: false,
				...(bump ? { bump_version: true } : {})
			})
		});
		const result = await res.json();
		if (res.ok) {
			await reload();
			return true;
		}
		if (result.error === 'versionBumpRequired' && !bump) {
			if (confirm(m.lbDraftVersionBumpConfirm({ version: draft.version }))) {
				return commitOnly(true);
			}
			return false;
		}
		if (result.error === 'draftValidationFailed') {
			validation = { errors: result.details ?? [], warnings: [] };
			setStatus(m.lbDraftValidationFailedSeePanel(), 'error');
			return false;
		}
		setStatus(result.detail || safeTranslate(result.error) || JSON.stringify(result), 'error');
		return false;
	}

	async function exportYaml() {
		const clean = draft.identity_locked && !draft.has_unpublished_changes;
		if (!clean) {
			if (confirm(m.lbDraftExportPublishFirstConfirm())) {
				if (!(await commitOnly())) return;
			} else if (!confirm(m.lbDraftExportWorkingCopyConfirm())) {
				return;
			}
		}
		window.location.href = `${base()}/export`;
	}

	function objectCount(type: string): number {
		return draft.objects_meta?.[type] ?? 0;
	}

	// Kinds the builder allows at most one of per library.
	const SINGLE_KINDS = ['frameworks', 'risk_matrices', 'preset'];
	function singleKindFull(type: string): boolean {
		return SINGLE_KINDS.includes(type) && objectCount(type) > 0;
	}

	// --- Simple / full view ---------------------------------------------------
	// A library holding exactly one primary object (a framework or a matrix)
	// and nothing else reads as "editing that object": the library layer is
	// packaging, folded away behind the full view.
	let viewChoice: 'simple' | 'full' | null = $state(null);
	const viewKey = () => `library-builder:view:${draft.id}`;
	let primaryKind = $derived.by(() => {
		const populated = OBJECT_TYPES.filter((type) => objectCount(type) > 0);
		if (populated.length !== 1) return null;
		if (populated[0] === 'frameworks' && objectCount('frameworks') === 1) return 'framework';
		if (populated[0] === 'risk_matrices' && objectCount('risk_matrices') === 1) return 'matrix';
		return null;
	});
	let view = $derived(primaryKind ? (viewChoice ?? 'simple') : 'full');
	function setView(mode: 'simple' | 'full') {
		viewChoice = mode;
		try {
			localStorage.setItem(viewKey(), mode);
		} catch {
			/* storage unavailable — the choice just won't persist */
		}
	}

	// --- Visual framework editor -----------------------------------------------
	let frameworks = $derived((draft.content?.frameworks ?? []) as any[]);
	let addingFramework = $state(false);

	// --- Leaf object editors (threats, reference controls) ----------------------
	const CATEGORIES = ['policy', 'process', 'technical', 'physical', 'procedure'];
	const CSF_FUNCTIONS = ['govern', 'identify', 'protect', 'detect', 'respond', 'recover'];

	let threats = $derived((draft.content?.threats ?? []) as any[]);
	let referenceControls = $derived((draft.content?.reference_controls ?? []) as any[]);
	let riskMatrices = $derived((draft.content?.risk_matrices ?? []) as any[]);
	let mappingSets = $derived((draft.content?.requirement_mapping_sets ?? []) as any[]);
	let metricDefinitions = $derived((draft.content?.metric_definitions ?? []) as any[]);

	/** Short display form for a framework URN (its trailing ref). */
	function urnLeaf(urn: unknown): string {
		const parts = String(urn ?? '').split(':');
		return parts.length > 4 ? parts.slice(4).join(':') : String(urn ?? '');
	}

	// One shared inline form for both flat kinds; null = closed.
	let leafForm: null | {
		field: 'threats' | 'reference_controls';
		urn: string | null;
		values: Record<string, string>;
		translations: Record<string, Record<string, string>>;
	} = $state(null);
	let savingLeaf = $state(false);

	function openLeafForm(field: 'threats' | 'reference_controls', item: any = null) {
		leafForm = {
			field,
			urn: item?.urn ?? null,
			values: {
				ref_id: item?.ref_id ?? '',
				name: item?.name ?? '',
				description: item?.description ?? '',
				...(field === 'reference_controls'
					? {
							category: item?.category ?? '',
							csf_function: item?.csf_function ?? '',
							typical_evidence: item?.typical_evidence ?? ''
						}
					: {})
			},
			translations: { ...(item?.translations ?? {}) }
		};
	}

	async function saveLeafForm() {
		if (!leafForm) return;
		savingLeaf = true;
		try {
			const object: Record<string, any> = {};
			for (const [key, value] of Object.entries(leafForm.values)) {
				object[key] = value.trim() === '' ? null : value;
			}
			// null clears the key on the stored object (upsert semantics)
			object.translations =
				Object.keys(leafForm.translations).length > 0 ? leafForm.translations : null;
			const res = await fetch(base(), {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					action: 'upsert-object',
					field: leafForm.field,
					urn: leafForm.urn ?? undefined,
					object
				})
			});
			const result = await res.json();
			if (!res.ok) throw new Error(result.error || JSON.stringify(result));
			draft = result.draft;
			resetForms();
			leafForm = null;
			setStatus(m.saved(), 'success');
		} catch (e: any) {
			setStatus(safeTranslate(e.message), 'error');
		} finally {
			savingLeaf = false;
		}
	}

	async function deleteObject(item: any, force = false) {
		if (
			!force &&
			!confirm(m.lbDraftDeleteObjectConfirm({ name: item.name || item.ref_id || item.urn }))
		) {
			return;
		}
		const res = await fetch(base(), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ action: 'delete-object', urn: item.urn, force })
		});
		const result = await res.json();
		if (res.status === 409 && result.error === 'objectIsReferenced') {
			if (
				confirm(
					m.lbDraftObjectReferencedConfirm({
						name: item.name || item.ref_id,
						count: result.references.length
					})
				)
			) {
				await deleteObject(item, true);
			}
			return;
		}
		if (!res.ok) {
			setStatus(safeTranslate(result.error) || JSON.stringify(result), 'error');
			return;
		}
		draft = result.draft;
		resetForms();
		setStatus(m.deleted(), 'success');
	}

	// The journey preset is a singular top-level key, removed by name.
	async function deletePreset() {
		if (!confirm(m.lbDraftRemovePresetConfirm())) return;
		const res = await fetch(base(), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ action: 'delete-object', field: 'preset' })
		});
		const result = await res.json();
		if (!res.ok) {
			setStatus(safeTranslate(result.error) || JSON.stringify(result), 'error');
			return;
		}
		draft = result.draft;
		resetForms();
		setStatus(m.deleted(), 'success');
	}

	// --- Risk matrices ------------------------------------------------------------
	let addingMatrix = $state(false);

	function matrixEditorHref(matrix: any): string {
		return `/experimental/library-builder/${draft.id}/matrix?matrix_urn=${encodeURIComponent(
			matrix.urn
		)}`;
	}

	async function addMatrix() {
		// Single matrix per library: it carries the library's own identity
		// (bare family URN server-side), same as Add framework.
		addingMatrix = true;
		try {
			const res = await fetch(base(), {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					action: 'upsert-object',
					field: 'risk_matrices',
					object: defaultMatrixObject(draft.ref_id, draft.name)
				})
			});
			const result = await res.json();
			if (!res.ok) throw new Error(result.error || JSON.stringify(result));
			window.location.href = `/experimental/library-builder/${draft.id}/matrix?matrix_urn=${encodeURIComponent(
				result.object.urn
			)}`;
		} catch (e: any) {
			setStatus(safeTranslate(e.message), 'error');
			addingMatrix = false;
		}
	}

	function frameworkEditorHref(framework: any): string {
		return `/experimental/library-builder/${draft.id}/framework?framework_urn=${encodeURIComponent(
			framework.urn
		)}`;
	}

	async function addFramework() {
		addingFramework = true;
		try {
			const res = await fetch(base(), {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ action: 'add-framework' })
			});
			const result = await res.json();
			if (!res.ok) throw new Error(result.error || JSON.stringify(result));
			window.location.href = `/experimental/library-builder/${draft.id}/framework?framework_urn=${encodeURIComponent(
				result.framework_urn
			)}`;
		} catch (e: any) {
			setStatus(safeTranslate(e.message), 'error');
			addingFramework = false;
		}
	}
</script>

<div class="space-y-6">
	<!-- Header -->
	<div class="card p-4">
		<div class="flex flex-wrap items-center justify-between gap-4">
			<div>
				<div class="flex items-center gap-2">
					<a href="/experimental/library-builder" class="text-surface-500 hover:text-surface-700">
						<i class="fa-solid fa-arrow-left"></i>
					</a>
					<h2 class="text-xl font-semibold">{draft.name}</h2>
					<!-- Publication status, mirroring the drafts list. Published =
					     identity committed (frozen), by decision or by proof; the
					     packager/ref_id fields show the (frozen) hint. -->
					{#if !draft.identity_locked}
						<span class="badge variant-ghost-surface text-xs">{m.lbListDraft()}</span>
					{:else if draft.has_unpublished_changes}
						<span class="badge variant-filled-warning text-xs">
							<i class="fa-solid fa-cloud-arrow-up mr-0.5" aria-hidden="true"
							></i>{m.lbListPublishedModified()}
						</span>
					{:else}
						<span class="badge variant-filled-success text-xs">
							<i class="fa-solid fa-cloud-arrow-up mr-0.5" aria-hidden="true"
							></i>{m.lbListPublished()}
						</span>
					{/if}
					<span class="badge variant-ghost-surface text-xs">v{draft.version}</span>
				</div>
				<p class="text-xs font-mono text-surface-500 mt-1">{draft.urn}</p>
				{#if draft.last_published_at}
					<p class="text-xs text-surface-500">
						{m.lbDraftLastPublished({ date: new Date(draft.last_published_at).toLocaleString() })}
					</p>
				{/if}
			</div>
			<!-- Toolbar. Decorative icons are aria-hidden: their ::before glyph
			     would otherwise pollute the controls' accessible names (breaking
			     exact-name queries like the functional tests' /^publish$/). -->
			<div class="flex items-center gap-2">
				{#if statusMessage}
					<span
						class="text-xs px-2 py-1 rounded-full {statusType === 'error'
							? 'bg-red-100 text-red-700'
							: 'bg-green-100 text-green-700'}"
					>
						{statusMessage}
					</span>
				{/if}
				{#if primaryKind}
					<button
						type="button"
						class="btn btn-sm variant-ghost-surface"
						onclick={() => setView(view === 'simple' ? 'full' : 'simple')}
						title={view === 'simple' ? m.lbDraftFullViewTitle() : m.lbDraftSimpleViewTitle()}
					>
						<i
							class="fa-solid {view === 'simple' ? 'fa-layer-group' : 'fa-minimize'} mr-1"
							aria-hidden="true"
						></i>
						{view === 'simple' ? m.lbDraftFullView() : m.lbDraftSimpleView()}
					</button>
				{/if}
				<button
					type="button"
					class="btn btn-sm variant-ghost-surface"
					onclick={validateDraft}
					disabled={validating}
				>
					<i class="fa-solid fa-list-check mr-1" aria-hidden="true"></i>{m.validate()}
				</button>
				<button type="button" class="btn btn-sm variant-ghost-surface" onclick={exportYaml}>
					<i class="fa-solid fa-file-arrow-down mr-1" aria-hidden="true"></i>{m.exportYaml()}
				</button>
				<button
					type="button"
					class="btn btn-sm variant-filled-primary"
					onclick={() => publish()}
					disabled={publishing}
				>
					{#if publishing}
						<i class="fa-solid fa-spinner fa-spin mr-1" aria-hidden="true"></i>
					{:else}
						<i class="fa-solid fa-cloud-arrow-up mr-1" aria-hidden="true"></i>
					{/if}
					{m.publish()}
				</button>
			</div>
		</div>

		<!-- Contents summary line -->
		{#if view === 'full'}
			<div
				class="flex items-center gap-2 flex-wrap mt-3 pt-3 border-t border-surface-200-800 text-xs text-surface-600-400"
			>
				<i class="fa-solid fa-cubes"></i>
				{#if OBJECT_TYPES.some((type) => objectCount(type) > 0)}
					{#each OBJECT_TYPES as type}
						{#if objectCount(type) > 0}
							<span class="badge variant-ghost-surface text-xs">
								{objectCountLabel(type)}
							</span>
						{/if}
					{/each}
				{:else}
					<span>{m.lbDraftEmptyLibrary()}</span>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Advisory identity conflicts -->
	{#if conflicts.length > 0}
		<div class="card p-4 bg-amber-50 border border-amber-300">
			<p class="text-sm text-amber-800">
				<i class="fa-solid fa-triangle-exclamation mr-1"></i>
				{m.lbDraftIdentityCollides({ count: conflicts.length })}
			</p>
			<ul class="text-xs font-mono text-amber-700 mt-2 space-y-0.5">
				{#each conflicts.slice(0, 5) as conflict}
					<li>{conflict.kind}: {conflict.urn}</li>
				{/each}
				{#if conflicts.length > 5}<li>…</li>{/if}
			</ul>
		</div>
	{/if}

	<!-- Score change conflict on publish -->
	{#if scoreConflict}
		<div class="card p-4 bg-amber-50 border border-amber-300 space-y-2">
			<p class="text-sm text-amber-800">
				<i class="fa-solid fa-triangle-exclamation mr-1"></i>
				{m.lbDraftScoreChanged({
					urn: scoreConflict.framework_urn,
					count: scoreConflict.affected_assessments?.length ?? 0
				})}
			</p>
			<div class="flex gap-2">
				{#each scoreConflict.strategies ?? [] as strategy}
					<button
						type="button"
						class="btn btn-sm variant-ghost-warning"
						onclick={() => publish({ strategy: strategy.action, _presetChecked: true })}
					>
						{strategy.name}
					</button>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Validation results -->
	{#if validation}
		<div class="card p-4">
			<h3 class="text-lg font-semibold mb-2">
				<i class="fa-solid fa-list-check mr-1"></i>{m.lbDraftValidation()}
			</h3>
			{#if validation.errors.length === 0 && validation.warnings.length === 0}
				<p class="text-sm text-green-700">
					<i class="fa-solid fa-circle-check mr-1"></i>{m.lbDraftIsPublishable()}
				</p>
			{/if}
			{#each validation.errors as error}
				<p class="text-sm text-red-700">
					<i class="fa-solid fa-circle-xmark mr-1"></i>{safeTranslate(error)}
				</p>
			{/each}
			{#each validation.warnings as warning}
				<p class="text-sm text-amber-700">
					<i class="fa-solid fa-triangle-exclamation mr-1"></i>{safeTranslate(warning)}
				</p>
			{/each}
		</div>
	{/if}

	{#if view === 'full'}
		<div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
			<!-- Metadata -->
			<div class="card p-4 space-y-3">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-tags mr-1"></i>{m.lbDraftLibraryMetadata()}
				</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
					<label class="label text-sm md:col-span-2">
						<span>{m.name()}</span>
						<input class="input" type="text" bind:value={meta.name} />
					</label>
					<label class="label text-sm md:col-span-2">
						<span>{m.description()}</span>
						<textarea class="textarea" rows="2" bind:value={meta.description}></textarea>
					</label>
					<label class="label text-sm">
						<span>{m.packager()} {draft.identity_locked ? m.lbDraftFrozenSuffix() : ''}</span>
						<input
							class="input"
							type="text"
							bind:value={meta.packager}
							disabled={draft.identity_locked}
						/>
					</label>
					<label class="label text-sm">
						<span>{m.refId()} {draft.identity_locked ? m.lbDraftFrozenSuffix() : ''}</span>
						<input
							class="input"
							type="text"
							bind:value={meta.ref_id}
							disabled={draft.identity_locked}
						/>
					</label>
					<label class="label text-sm">
						<span>{m.version()}</span>
						<input class="input" type="number" min="1" bind:value={meta.version} />
					</label>
					<label class="label text-sm">
						<span>{m.locale()}</span>
						<input class="input" type="text" bind:value={meta.locale} />
					</label>
					<label class="label text-sm">
						<span>{m.provider()}</span>
						<input class="input" type="text" bind:value={meta.provider} />
					</label>
					<label class="label text-sm">
						<span>{m.publicationDate()}</span>
						<input class="input" type="date" bind:value={meta.publication_date} />
					</label>
					<label class="label text-sm md:col-span-2">
						<span>{m.copyright()}</span>
						<input class="input" type="text" bind:value={meta.copyright} />
					</label>
					<label class="label text-sm md:col-span-2">
						<span>{m.lbDraftDependenciesLabel()}</span>
						<textarea class="textarea font-mono text-xs" rows="3" bind:value={dependenciesText}
						></textarea>
					</label>
					<label class="label text-sm md:col-span-2">
						<span>{m.lbDraftLabelsLabel()}</span>
						<input class="input" type="text" bind:value={labelsText} />
					</label>
				</div>
				{#if !draft.identity_locked}
					<p class="text-xs text-surface-500">
						{m.lbDraftIdentityHelp()}
					</p>
				{/if}
				<!-- Library-level translations (name / description per language) -->
				<TranslationsEditor
					bind:translations={metaTranslations}
					fields={[
						{ key: 'name', label: m.name() },
						{ key: 'description', label: m.description(), textarea: true }
					]}
					baseLang={meta.locale || 'en'}
				/>
				<div class="flex items-center justify-end gap-2 pt-1">
					{#if metaDirty}
						<span class="text-xs text-amber-600">
							<i class="fa-solid fa-pen-nib mr-1"></i>{m.unsavedChanges()}
						</span>
					{/if}
					<button
						type="button"
						class="btn btn-sm variant-filled-primary"
						onclick={saveMeta}
						disabled={savingMeta || !metaDirty}
					>
						{#if savingMeta}<i class="fa-solid fa-spinner fa-spin mr-1"></i>{:else}<i
								class="fa-solid fa-floppy-disk mr-1"
							></i>{/if}
						{m.lbDraftSaveMetadata()}
					</button>
				</div>
			</div>

			<!-- Import objects -->
			<div class="card p-4 space-y-3">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-file-import mr-1"></i>{m.lbDraftImportObjects()}
				</h3>
				<p class="text-xs text-surface-500">
					{m.lbDraftImportObjectsHelp()}
				</p>
				<select class="select text-sm" bind:value={importSource}>
					<option value="">{m.lbDraftSourceLibrary()}</option>
					{#if storedLibraries.length > 0}
						<optgroup label={m.lbDraftStoredLibraries()}>
							{#each storedLibraries as library}
								<option value={library.id}>
									{library.name} (v{library.version}){library.builtin
										? m.lbDraftBuiltinSuffix()
										: ''}
								</option>
							{/each}
						</optgroup>
					{/if}
					{#if otherDrafts.length > 0}
						<optgroup label={m.lbDraftYourDrafts()}>
							{#each otherDrafts as other}
								<option value={'draft:' + other.id}>{other.name}</option>
							{/each}
						</optgroup>
					{/if}
				</select>
				<div class="flex flex-wrap gap-3 text-sm">
					{#each OBJECT_TYPES as type}
						{@const atLimit = singleKindFull(type)}
						<label class="flex items-center gap-1 {atLimit ? 'opacity-50' : ''}">
							<input
								type="checkbox"
								class="checkbox"
								checked={importTypes.includes(type)}
								onchange={() => toggleType(type)}
								disabled={atLimit}
								title={atLimit ? m.lbDraftSingleKindTitle() : undefined}
							/>
							{type.replaceAll('_', ' ')}
						</label>
					{/each}
				</div>
				<p class="text-xs text-surface-500">{m.lbDraftNothingChecked()}</p>
				<div class="flex flex-wrap items-center gap-4 text-sm">
					<span class="font-medium">{m.lbDraftOutOfSelectionRefs()}</span>
					<label class="flex items-center gap-1">
						<input type="radio" class="radio" bind:group={importPolicy} value="strip" />
						{m.lbDraftPolicyStrip()}
					</label>
					<label class="flex items-center gap-1">
						<input type="radio" class="radio" bind:group={importPolicy} value="pull" />
						{m.lbDraftPolicyPull()}
					</label>
					<label class="flex items-center gap-1">
						<input type="radio" class="radio" bind:group={importPolicy} value="reference" />
						{m.lbDraftPolicyReference()}
					</label>
					<label class="flex items-center gap-1 ml-auto">
						<input type="checkbox" class="checkbox" bind:checked={importOverwrite} />
						{m.lbDraftOverwriteExisting()}
					</label>
				</div>
				<button
					type="button"
					class="btn btn-sm variant-filled-primary"
					onclick={importObjects}
					disabled={!importSource || importing}
				>
					{#if importing}<i class="fa-solid fa-spinner fa-spin mr-1"></i>{:else}<i
							class="fa-solid fa-file-import mr-1"
						></i>{/if}
					{m.lbDraftImport()}
				</button>
				{#if importReport}
					<div class="text-xs text-surface-600-400 space-y-1 border-t border-surface-200-800 pt-2">
						{#if importReport.pulled?.length}
							<p>{m.lbDraftReportPulled({ count: importReport.pulled.length })}</p>
						{/if}
						{#if importReport.stripped?.length}
							<p>{m.lbDraftReportStripped({ count: importReport.stripped.length })}</p>
						{/if}
						{#if importReport.referenced?.length}
							<p>{m.lbDraftReportReferenced({ count: importReport.referenced.length })}</p>
						{/if}
						{#if importReport.external?.length}
							<p>{m.lbDraftReportExternal({ count: importReport.external.length })}</p>
						{/if}
						{#if importReport.unresolved?.length}
							<p class="text-amber-600">
								{m.lbDraftReportUnresolved({ list: importReport.unresolved.join(', ') })}
							</p>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Frameworks: visual editor entry points -->
	{#if view === 'full' || primaryKind === 'framework'}
		<div class="card p-4 space-y-3">
			<div class="flex items-center justify-between">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-sitemap mr-1"></i>{m.framework()}
				</h3>
				{#if frameworks.length === 0}
					<button
						type="button"
						class="btn btn-sm variant-ghost-primary"
						onclick={addFramework}
						disabled={addingFramework}
					>
						{#if addingFramework}<i class="fa-solid fa-spinner fa-spin mr-1"></i>{:else}<i
								class="fa-solid fa-plus mr-1"
							></i>{/if}
						{m.addFramework()}
					</button>
				{/if}
			</div>
			{#if frameworks.length > 0}
				<ul class="divide-y divide-surface-200-800">
					{#each frameworks as framework}
						<li class="flex items-center justify-between py-2">
							<div class="min-w-0">
								<p class="font-medium truncate">{framework.name || framework.ref_id}</p>
								<p class="text-xs font-mono text-surface-500 truncate">{framework.urn}</p>
								<p class="text-xs text-surface-500">
									{m.lbDraftNodeCount({ count: (framework.requirement_nodes ?? []).length })}
								</p>
							</div>
							<div class="flex items-center gap-1">
								<a href={frameworkEditorHref(framework)} class="btn btn-sm variant-filled-primary">
									<i class="fa-solid fa-pen-to-square mr-1"></i>
									{m.lbDraftEditVisually()}
								</a>
								<button
									type="button"
									class="btn btn-sm variant-ghost-error"
									onclick={() => deleteObject(framework)}
									aria-label={m.lbDraftDeleteFramework()}
								>
									<i class="fa-solid fa-trash"></i>
								</button>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="text-sm text-surface-500">
					{m.lbDraftNoFramework()}
				</p>
			{/if}
		</div>
	{/if}

	<!-- Risk matrices: visual editor entry points -->
	{#if view === 'full' || primaryKind === 'matrix'}
		<div class="card p-4 space-y-3">
			<div class="flex items-center justify-between">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-table-cells mr-1"></i>{m.riskMatrix()}
				</h3>
				{#if riskMatrices.length === 0}
					<button
						type="button"
						class="btn btn-sm variant-ghost-primary"
						onclick={addMatrix}
						disabled={addingMatrix}
					>
						{#if addingMatrix}<i class="fa-solid fa-spinner fa-spin mr-1"></i>{:else}<i
								class="fa-solid fa-plus mr-1"
							></i>{/if}
						{m.lbDraftAddMatrix()}
					</button>
				{/if}
			</div>
			{#if riskMatrices.length > 0}
				<ul class="divide-y divide-surface-200-800">
					{#each riskMatrices as matrix}
						<li class="flex items-center justify-between py-2">
							<div class="min-w-0">
								<p class="font-medium truncate">{matrix.name || matrix.ref_id}</p>
								<p class="text-xs font-mono text-surface-500 truncate">{matrix.urn}</p>
								<p class="text-xs text-surface-500">
									{m.lbDraftMatrixDims({
										probability: (matrix.probability ?? []).length,
										impact: (matrix.impact ?? []).length,
										risk: (matrix.risk ?? []).length
									})}
								</p>
							</div>
							<div class="flex items-center gap-1">
								<a href={matrixEditorHref(matrix)} class="btn btn-sm variant-filled-primary">
									<i class="fa-solid fa-pen-to-square mr-1"></i>
									{m.lbDraftEditVisually()}
								</a>
								<button
									type="button"
									class="btn btn-sm variant-ghost-error"
									onclick={() => deleteObject(matrix)}
									aria-label={m.lbDraftDeleteMatrix()}
								>
									<i class="fa-solid fa-trash"></i>
								</button>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="text-sm text-surface-500">{m.lbDraftNoMatrix()}</p>
			{/if}
		</div>
	{/if}

	{#if view === 'full'}
		<!-- Journey preset -->
		<div class="card p-4 space-y-3">
			<div class="flex items-center justify-between">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-route mr-1"></i>{m.lbDraftJourneyPreset()}
				</h3>
				<div class="flex items-center gap-1">
					<a
						href="/experimental/library-builder/{draft.id}/preset"
						class="btn btn-sm {draft.content?.preset
							? 'variant-filled-primary'
							: 'variant-ghost-primary'}"
					>
						<i class="fa-solid fa-pen-to-square mr-1"></i>
						{draft.content?.preset ? m.lbDraftEditJourney() : m.lbDraftCreateJourney()}
					</a>
					{#if draft.content?.preset}
						<button
							type="button"
							class="btn btn-sm variant-ghost-error"
							onclick={deletePreset}
							aria-label={m.lbDraftRemovePreset()}
						>
							<i class="fa-solid fa-trash"></i>
						</button>
					{/if}
				</div>
			</div>
			{#if draft.content?.preset}
				<p class="text-sm text-surface-600-400">
					{#if draft.content.preset.name}
						<span class="font-medium">{draft.content.preset.name}</span> —
					{/if}
					{m.lbDraftPresetSummary({
						steps: (draft.content.preset.journey?.steps ?? []).length,
						objects: (draft.content.preset.scaffolded_objects ?? []).length
					})}
				</p>
			{:else}
				<p class="text-sm text-surface-500">
					{m.lbDraftNoPreset()}
				</p>
			{/if}
		</div>

		<!-- Threats + Reference controls: inline table editors -->
		{#each [{ field: 'threats' as const, label: m.threats(), icon: 'fa-bolt', items: threats }, { field: 'reference_controls' as const, label: m.referenceControls(), icon: 'fa-shield-halved', items: referenceControls }] as kind}
			<div class="card p-4 space-y-3">
				<div class="flex items-center justify-between">
					<h3 class="text-lg font-semibold">
						<i class="fa-solid {kind.icon} mr-1"></i>{kind.label}
					</h3>
					<button
						type="button"
						class="btn btn-sm variant-ghost-primary"
						onclick={() => openLeafForm(kind.field)}
					>
						<i class="fa-solid fa-plus mr-1"></i>
						{kind.field === 'threats' ? m.addThreat() : m.addReferenceControl()}
					</button>
				</div>

				{#if leafForm && leafForm.field === kind.field}
					<div
						class="border border-primary-200-800 rounded p-3 grid grid-cols-1 md:grid-cols-3 gap-3 bg-primary-50-950/30"
					>
						<label class="label text-sm">
							<span>{m.refId()} {leafForm.urn ? '' : m.lbDraftMintUrnSuffix()}</span>
							<input
								class="input"
								type="text"
								bind:value={leafForm.values.ref_id}
								disabled={leafForm.urn !== null}
							/>
						</label>
						<label class="label text-sm md:col-span-2">
							<span>{m.name()}</span>
							<input class="input" type="text" bind:value={leafForm.values.name} />
						</label>
						<label class="label text-sm md:col-span-3">
							<span>{m.description()}</span>
							<textarea class="textarea" rows="2" bind:value={leafForm.values.description}
							></textarea>
						</label>
						{#if kind.field === 'reference_controls'}
							<label class="label text-sm">
								<span>{m.category()}</span>
								<select class="select" bind:value={leafForm.values.category}>
									<option value="">—</option>
									{#each CATEGORIES as category}
										<option value={category}>{category}</option>
									{/each}
								</select>
							</label>
							<label class="label text-sm">
								<span>{m.csfFunction()}</span>
								<select class="select" bind:value={leafForm.values.csf_function}>
									<option value="">—</option>
									{#each CSF_FUNCTIONS as fn}
										<option value={fn}>{fn}</option>
									{/each}
								</select>
							</label>
							<label class="label text-sm">
								<span>{m.typicalEvidence()}</span>
								<input class="input" type="text" bind:value={leafForm.values.typical_evidence} />
							</label>
						{/if}
						<div class="md:col-span-3">
							<TranslationsEditor
								bind:translations={leafForm.translations}
								fields={[
									{ key: 'name', label: m.name() },
									{ key: 'description', label: m.description(), textarea: true }
								]}
								baseLang={draft.locale ?? 'en'}
							/>
						</div>
						<div class="md:col-span-3 flex justify-end gap-2">
							<button
								type="button"
								class="btn btn-sm variant-ghost-surface"
								onclick={() => (leafForm = null)}
							>
								{m.cancel()}
							</button>
							<button
								type="button"
								class="btn btn-sm variant-filled-primary"
								onclick={saveLeafForm}
								disabled={savingLeaf || (!leafForm.urn && !leafForm.values.ref_id.trim())}
							>
								{#if savingLeaf}<i class="fa-solid fa-spinner fa-spin mr-1"></i>{/if}
								{leafForm.urn ? m.save() : m.create()}
							</button>
						</div>
					</div>
				{/if}

				{#if kind.items.length > 0}
					<div class="table-container">
						<table class="table table-compact w-full">
							<thead>
								<tr>
									<th class="w-28">{m.lbDraftColRef()}</th>
									<th>{m.name()}</th>
									{#if kind.field === 'reference_controls'}
										<th class="w-28">{m.category()}</th>
										<th class="w-28">{m.lbDraftColCsf()}</th>
									{/if}
									<th>{m.description()}</th>
									<th class="w-24"></th>
								</tr>
							</thead>
							<tbody>
								{#each kind.items as item}
									<tr>
										<td class="font-mono text-xs">{item.ref_id}</td>
										<td class="font-medium">{item.name || '—'}</td>
										{#if kind.field === 'reference_controls'}
											<td class="text-xs">{item.category || '—'}</td>
											<td class="text-xs">{item.csf_function || '—'}</td>
										{/if}
										<td class="text-sm text-surface-600-400 max-w-64 truncate">
											{item.description || '—'}
										</td>
										<td class="space-x-1 text-right">
											<button
												type="button"
												class="btn-icon btn-icon-sm variant-ghost-surface"
												onclick={() => openLeafForm(kind.field, item)}
												aria-label={m.edit()}
											>
												<i class="fa-solid fa-pen"></i>
											</button>
											<button
												type="button"
												class="btn-icon btn-icon-sm variant-ghost-error"
												onclick={() => deleteObject(item)}
												aria-label={m.delete()}
											>
												<i class="fa-solid fa-trash"></i>
											</button>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<p class="text-sm text-surface-500">{m.lbDraftNoneYet()}</p>
				{/if}
			</div>
		{/each}

		<!-- Requirement mapping sets: arrive via import, removable here -->
		{#if mappingSets.length > 0}
			<div class="card p-4 space-y-3">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-arrows-left-right mr-1"></i>{m.lbDraftMappingSets()}
				</h3>
				<ul class="divide-y divide-surface-200-800">
					{#each mappingSets as mappingSet}
						<li class="flex items-center justify-between py-2 gap-3">
							<div class="min-w-0">
								<p class="font-medium truncate">{mappingSet.name || mappingSet.ref_id}</p>
								<p class="text-xs font-mono text-surface-500 truncate">{mappingSet.urn}</p>
								<p class="text-xs text-surface-500">
									<span class="font-mono">{urnLeaf(mappingSet.source_framework_urn)}</span>
									<i class="fa-solid fa-arrow-right mx-1"></i>
									<span class="font-mono">{urnLeaf(mappingSet.target_framework_urn)}</span>
									— {m.lbDraftMappingCount({
										count: (mappingSet.requirement_mappings ?? []).length
									})}
								</p>
							</div>
							<button
								type="button"
								class="btn btn-sm variant-ghost-error shrink-0"
								onclick={() => deleteObject(mappingSet)}
								aria-label={m.lbDraftDeleteMappingSet()}
							>
								<i class="fa-solid fa-trash"></i>
							</button>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Metric definitions: arrive via import, removable here -->
		{#if metricDefinitions.length > 0}
			<div class="card p-4 space-y-3">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-gauge-high mr-1"></i>{m.lbDraftMetricDefinitions()}
				</h3>
				<ul class="divide-y divide-surface-200-800">
					{#each metricDefinitions as metric}
						<li class="flex items-center justify-between py-2 gap-3">
							<div class="min-w-0">
								<p class="font-medium truncate">{metric.name || metric.ref_id}</p>
								<p class="text-xs font-mono text-surface-500 truncate">{metric.urn}</p>
							</div>
							<button
								type="button"
								class="btn btn-sm variant-ghost-error shrink-0"
								onclick={() => deleteObject(metric)}
								aria-label={m.lbDraftDeleteMetricDefinition()}
							>
								<i class="fa-solid fa-trash"></i>
							</button>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	{/if}

	{#if view === 'simple'}
		<p class="text-xs text-surface-500 text-center">
			{primaryKind === 'framework'
				? m.lbDraftSimpleViewPackagedFramework({ urn: draft.urn })
				: m.lbDraftSimpleViewPackagedMatrix({ urn: draft.urn })}
		</p>
	{/if}
</div>
