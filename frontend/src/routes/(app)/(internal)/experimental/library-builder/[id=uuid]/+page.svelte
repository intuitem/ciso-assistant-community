<script lang="ts">
	import { onMount } from 'svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { defaultMatrixObject } from '../builder-helpers';

	let { data } = $props();
	let draft: any = $state(data.draft);
	let storedLibraries: any[] = $state(data.storedLibraries ?? []);
	let otherDrafts: any[] = $state(data.otherDrafts ?? []);

	$pageTitle = 'Library Builder';

	const OBJECT_TYPES = [
		'frameworks',
		'threats',
		'reference_controls',
		'risk_matrices',
		'requirement_mapping_sets',
		'metric_definitions',
		'preset'
	];

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
	let savingMeta = $state(false);
	let metaBaseline = $state('');

	function metaSnapshot(): string {
		return JSON.stringify({ meta, dependenciesText, labelsText });
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
			labelsText: (draft.labels ?? []).join(', ')
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
		}
		metaBaseline = JSON.stringify(serverFormState());
		meta = server.meta;
		dependenciesText = server.dependenciesText;
		labelsText = server.labelsText;
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
			if (await patch(payload)) setStatus('Metadata saved', 'success');
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
			setStatus('Objects imported', 'success');
		} catch (e: any) {
			setStatus(e.message, 'error');
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
							`Publishing removes ${deleted.length} journey step(s) from the preset` +
								(withState ? `, ${withState} with user progress that will be lost` : '') +
								'. Continue?'
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
				setStatus(`Published ${result.urn} v${result.version}`, 'success');
				validation = null;
				await reload();
				return;
			}
			if (result.error === 'libraryVersionOutdated') {
				if (
					confirm(
						`Version ${draft.version} is not newer than the published v${result.max_version}. ` +
							`Bump to v${result.max_version + 1} and publish?`
					)
				) {
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
				setStatus('Validation failed — see the validation panel', 'error');
				return;
			}
			setStatus(result.detail || result.error || JSON.stringify(result), 'error');
		} catch (e: any) {
			setStatus(e.message, 'error');
		} finally {
			publishing = false;
		}
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
			}
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
			setStatus('Saved', 'success');
		} catch (e: any) {
			setStatus(e.message, 'error');
		} finally {
			savingLeaf = false;
		}
	}

	async function deleteObject(item: any, force = false) {
		if (!force && !confirm(`Delete "${item.name || item.ref_id || item.urn}" from the draft?`)) {
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
					`"${item.name || item.ref_id}" is linked from ${result.references.length} requirement node(s). Remove the links and delete it?`
				)
			) {
				await deleteObject(item, true);
			}
			return;
		}
		if (!res.ok) {
			setStatus(result.error || JSON.stringify(result), 'error');
			return;
		}
		draft = result.draft;
		resetForms();
		setStatus('Deleted', 'success');
	}

	// The journey preset is a singular top-level key, removed by name.
	async function deletePreset() {
		if (!confirm('Remove the journey preset from this library?')) return;
		const res = await fetch(base(), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ action: 'delete-object', field: 'preset' })
		});
		const result = await res.json();
		if (!res.ok) {
			setStatus(result.error || JSON.stringify(result), 'error');
			return;
		}
		draft = result.draft;
		resetForms();
		setStatus('Deleted', 'success');
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
			setStatus(e.message, 'error');
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
			setStatus(e.message, 'error');
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
					{#if draft.identity_locked}
						<span class="badge variant-filled-success text-xs">
							<i class="fa-solid fa-lock mr-0.5"></i>Identity frozen
						</span>
					{:else}
						<span class="badge variant-ghost-surface text-xs">Draft</span>
					{/if}
					<span class="badge variant-ghost-surface text-xs">v{draft.version}</span>
				</div>
				<p class="text-xs font-mono text-surface-500 mt-1">{draft.urn}</p>
				{#if draft.last_published_at}
					<p class="text-xs text-surface-500">
						Last published {new Date(draft.last_published_at).toLocaleString()}
					</p>
				{/if}
			</div>
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
						title={view === 'simple'
							? 'Show the whole library: metadata, imports, all content types'
							: 'Back to the focused single-object view'}
					>
						<i class="fa-solid {view === 'simple' ? 'fa-layer-group' : 'fa-minimize'} mr-1"></i>
						{view === 'simple' ? 'Full view' : 'Simple view'}
					</button>
				{/if}
				<button
					type="button"
					class="btn btn-sm variant-ghost-surface"
					onclick={validateDraft}
					disabled={validating}
				>
					<i class="fa-solid fa-list-check mr-1"></i>Validate
				</button>
				<a href="{base()}/export" class="btn btn-sm variant-ghost-surface">
					<i class="fa-solid fa-file-arrow-down mr-1"></i>Export YAML
				</a>
				<button
					type="button"
					class="btn btn-sm variant-filled-primary"
					onclick={() => publish()}
					disabled={publishing}
				>
					{#if publishing}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
					{:else}
						<i class="fa-solid fa-cloud-arrow-up mr-1"></i>
					{/if}
					Publish
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
								{objectCount(type)}
								{type.replaceAll('_', ' ')}
							</span>
						{/if}
					{/each}
				{:else}
					<span>Empty library — add or import objects below.</span>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Advisory identity conflicts -->
	{#if conflicts.length > 0}
		<div class="card p-4 bg-amber-50 border border-amber-300">
			<p class="text-sm text-amber-800">
				<i class="fa-solid fa-triangle-exclamation mr-1"></i>
				This identity collides with {conflicts.length} existing object(s). Publishing will conflict —
				rename the draft (packager / reference ID) while it is still cheap.
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
				Score boundaries changed for {scoreConflict.framework_urn} and
				{scoreConflict.affected_assessments?.length ?? 0} assessment(s) are affected. Choose a strategy:
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
				<i class="fa-solid fa-list-check mr-1"></i>Validation
			</h3>
			{#if validation.errors.length === 0 && validation.warnings.length === 0}
				<p class="text-sm text-green-700">
					<i class="fa-solid fa-circle-check mr-1"></i>The draft is publishable.
				</p>
			{/if}
			{#each validation.errors as error}
				<p class="text-sm text-red-700"><i class="fa-solid fa-circle-xmark mr-1"></i>{error}</p>
			{/each}
			{#each validation.warnings as warning}
				<p class="text-sm text-amber-700">
					<i class="fa-solid fa-triangle-exclamation mr-1"></i>{warning}
				</p>
			{/each}
		</div>
	{/if}

	{#if view === 'full'}
		<div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
			<!-- Metadata -->
			<div class="card p-4 space-y-3">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-tags mr-1"></i>Library metadata
				</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
					<label class="label text-sm md:col-span-2">
						<span>Name</span>
						<input class="input" type="text" bind:value={meta.name} />
					</label>
					<label class="label text-sm md:col-span-2">
						<span>Description</span>
						<textarea class="textarea" rows="2" bind:value={meta.description}></textarea>
					</label>
					<label class="label text-sm">
						<span>Packager {draft.identity_locked ? '(frozen)' : ''}</span>
						<input
							class="input"
							type="text"
							bind:value={meta.packager}
							disabled={draft.identity_locked}
						/>
					</label>
					<label class="label text-sm">
						<span>Reference ID {draft.identity_locked ? '(frozen)' : ''}</span>
						<input
							class="input"
							type="text"
							bind:value={meta.ref_id}
							disabled={draft.identity_locked}
						/>
					</label>
					<label class="label text-sm">
						<span>Version</span>
						<input class="input" type="number" min="1" bind:value={meta.version} />
					</label>
					<label class="label text-sm">
						<span>Locale</span>
						<input class="input" type="text" bind:value={meta.locale} />
					</label>
					<label class="label text-sm">
						<span>Provider</span>
						<input class="input" type="text" bind:value={meta.provider} />
					</label>
					<label class="label text-sm">
						<span>Publication date</span>
						<input class="input" type="date" bind:value={meta.publication_date} />
					</label>
					<label class="label text-sm md:col-span-2">
						<span>Copyright</span>
						<input class="input" type="text" bind:value={meta.copyright} />
					</label>
					<label class="label text-sm md:col-span-2">
						<span>Dependencies (one library URN per line)</span>
						<textarea class="textarea font-mono text-xs" rows="3" bind:value={dependenciesText}
						></textarea>
					</label>
					<label class="label text-sm md:col-span-2">
						<span>Labels (comma-separated)</span>
						<input class="input" type="text" bind:value={labelsText} />
					</label>
				</div>
				{#if !draft.identity_locked}
					<p class="text-xs text-surface-500">
						Renaming packager / reference ID regenerates every URN of the document. Once published,
						the identity is frozen.
					</p>
				{/if}
				<div class="flex items-center justify-end gap-2 pt-1">
					{#if metaDirty}
						<span class="text-xs text-amber-600">
							<i class="fa-solid fa-pen-nib mr-1"></i>Unsaved changes
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
						Save metadata
					</button>
				</div>
			</div>

			<!-- Import objects -->
			<div class="card p-4 space-y-3">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-file-import mr-1"></i>Import objects (clone)
				</h3>
				<p class="text-xs text-surface-500">
					Copy objects by value from an existing library, rebased onto this draft's URN family.
					References leaving the selection follow the chosen policy.
				</p>
				<select class="select text-sm" bind:value={importSource}>
					<option value="">Source library…</option>
					{#if storedLibraries.length > 0}
						<optgroup label="Stored libraries">
							{#each storedLibraries as library}
								<option value={library.id}>
									{library.name} (v{library.version}){library.builtin ? ' — builtin' : ''}
								</option>
							{/each}
						</optgroup>
					{/if}
					{#if otherDrafts.length > 0}
						<optgroup label="Your drafts">
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
								title={atLimit
									? 'The library already holds one — a library has at most one of this kind.'
									: undefined}
							/>
							{type.replaceAll('_', ' ')}
						</label>
					{/each}
				</div>
				<p class="text-xs text-surface-500">Nothing checked = import everything.</p>
				<div class="flex flex-wrap items-center gap-4 text-sm">
					<span class="font-medium">Out-of-selection references:</span>
					<label class="flex items-center gap-1">
						<input type="radio" class="radio" bind:group={importPolicy} value="strip" />
						strip
					</label>
					<label class="flex items-center gap-1">
						<input type="radio" class="radio" bind:group={importPolicy} value="pull" />
						pull in
					</label>
					<label class="flex items-center gap-1">
						<input type="radio" class="radio" bind:group={importPolicy} value="reference" />
						keep as reference
					</label>
					<label class="flex items-center gap-1 ml-auto">
						<input type="checkbox" class="checkbox" bind:checked={importOverwrite} />
						overwrite existing
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
					Import
				</button>
				{#if importReport}
					<div class="text-xs text-surface-600-400 space-y-1 border-t border-surface-200-800 pt-2">
						{#if importReport.pulled?.length}
							<p>Pulled in: {importReport.pulled.length} object(s)</p>
						{/if}
						{#if importReport.stripped?.length}
							<p>Stripped links: {importReport.stripped.length}</p>
						{/if}
						{#if importReport.referenced?.length}
							<p>Kept as reference: {importReport.referenced.length}</p>
						{/if}
						{#if importReport.external?.length}
							<p>External references: {importReport.external.length}</p>
						{/if}
						{#if importReport.unresolved?.length}
							<p class="text-amber-600">
								Unresolved external references: {importReport.unresolved.join(', ')}
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
					<i class="fa-solid fa-sitemap mr-1"></i>Framework
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
						Add framework
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
									{(framework.requirement_nodes ?? []).length} requirement node(s)
								</p>
							</div>
							<div class="flex items-center gap-1">
								<a href={frameworkEditorHref(framework)} class="btn btn-sm variant-filled-primary">
									<i class="fa-solid fa-pen-to-square mr-1"></i>
									Edit visually
								</a>
								<button
									type="button"
									class="btn btn-sm variant-ghost-error"
									onclick={() => deleteObject(framework)}
									aria-label="Delete framework"
								>
									<i class="fa-solid fa-trash"></i>
								</button>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="text-sm text-surface-500">
					No framework in this library yet. Add one to author it in the visual editor, or import one
					from an existing library above.
				</p>
			{/if}
		</div>
	{/if}

	<!-- Risk matrices: visual editor entry points -->
	{#if view === 'full' || primaryKind === 'matrix'}
		<div class="card p-4 space-y-3">
			<div class="flex items-center justify-between">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-table-cells mr-1"></i>Risk matrix
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
						Add matrix
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
									{(matrix.probability ?? []).length}×{(matrix.impact ?? []).length},
									{(matrix.risk ?? []).length} risk level(s)
								</p>
							</div>
							<div class="flex items-center gap-1">
								<a href={matrixEditorHref(matrix)} class="btn btn-sm variant-filled-primary">
									<i class="fa-solid fa-pen-to-square mr-1"></i>
									Edit visually
								</a>
								<button
									type="button"
									class="btn btn-sm variant-ghost-error"
									onclick={() => deleteObject(matrix)}
									aria-label="Delete matrix"
								>
									<i class="fa-solid fa-trash"></i>
								</button>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="text-sm text-surface-500">No risk matrix in this library yet.</p>
			{/if}
		</div>
	{/if}

	{#if view === 'full'}
		<!-- Journey preset -->
		<div class="card p-4 space-y-3">
			<div class="flex items-center justify-between">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-route mr-1"></i>Journey preset
				</h3>
				<div class="flex items-center gap-1">
					<a
						href="/experimental/library-builder/{draft.id}/preset"
						class="btn btn-sm {draft.content?.preset
							? 'variant-filled-primary'
							: 'variant-ghost-primary'}"
					>
						<i class="fa-solid fa-pen-to-square mr-1"></i>
						{draft.content?.preset ? 'Edit journey' : 'Create journey'}
					</a>
					{#if draft.content?.preset}
						<button
							type="button"
							class="btn btn-sm variant-ghost-error"
							onclick={deletePreset}
							aria-label="Remove journey preset"
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
					{(draft.content.preset.journey?.steps ?? []).length} step(s),
					{(draft.content.preset.scaffolded_objects ?? []).length} scaffolded object(s)
				</p>
			{:else}
				<p class="text-sm text-surface-500">
					No journey preset in this library yet. A preset scaffolds objects and guides users through
					an onboarding journey when the library is loaded.
				</p>
			{/if}
		</div>

		<!-- Threats + Reference controls: inline table editors -->
		{#each [{ field: 'threats' as const, label: 'Threats', icon: 'fa-bolt', items: threats }, { field: 'reference_controls' as const, label: 'Reference controls', icon: 'fa-shield-halved', items: referenceControls }] as kind}
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
						Add
					</button>
				</div>

				{#if leafForm && leafForm.field === kind.field}
					<div
						class="border border-primary-200-800 rounded p-3 grid grid-cols-1 md:grid-cols-3 gap-3 bg-primary-50-950/30"
					>
						<label class="label text-sm">
							<span>Reference ID {leafForm.urn ? '' : '(used to mint the URN)'}</span>
							<input
								class="input"
								type="text"
								bind:value={leafForm.values.ref_id}
								disabled={leafForm.urn !== null}
							/>
						</label>
						<label class="label text-sm md:col-span-2">
							<span>Name</span>
							<input class="input" type="text" bind:value={leafForm.values.name} />
						</label>
						<label class="label text-sm md:col-span-3">
							<span>Description</span>
							<textarea class="textarea" rows="2" bind:value={leafForm.values.description}
							></textarea>
						</label>
						{#if kind.field === 'reference_controls'}
							<label class="label text-sm">
								<span>Category</span>
								<select class="select" bind:value={leafForm.values.category}>
									<option value="">—</option>
									{#each CATEGORIES as category}
										<option value={category}>{category}</option>
									{/each}
								</select>
							</label>
							<label class="label text-sm">
								<span>CSF function</span>
								<select class="select" bind:value={leafForm.values.csf_function}>
									<option value="">—</option>
									{#each CSF_FUNCTIONS as fn}
										<option value={fn}>{fn}</option>
									{/each}
								</select>
							</label>
							<label class="label text-sm">
								<span>Typical evidence</span>
								<input class="input" type="text" bind:value={leafForm.values.typical_evidence} />
							</label>
						{/if}
						<div class="md:col-span-3 flex justify-end gap-2">
							<button
								type="button"
								class="btn btn-sm variant-ghost-surface"
								onclick={() => (leafForm = null)}
							>
								Cancel
							</button>
							<button
								type="button"
								class="btn btn-sm variant-filled-primary"
								onclick={saveLeafForm}
								disabled={savingLeaf || (!leafForm.urn && !leafForm.values.ref_id.trim())}
							>
								{#if savingLeaf}<i class="fa-solid fa-spinner fa-spin mr-1"></i>{/if}
								{leafForm.urn ? 'Save' : 'Create'}
							</button>
						</div>
					</div>
				{/if}

				{#if kind.items.length > 0}
					<div class="table-container">
						<table class="table table-compact w-full">
							<thead>
								<tr>
									<th class="w-28">Ref</th>
									<th>Name</th>
									{#if kind.field === 'reference_controls'}
										<th class="w-28">Category</th>
										<th class="w-28">CSF</th>
									{/if}
									<th>Description</th>
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
												aria-label="Edit"
											>
												<i class="fa-solid fa-pen"></i>
											</button>
											<button
												type="button"
												class="btn-icon btn-icon-sm variant-ghost-error"
												onclick={() => deleteObject(item)}
												aria-label="Delete"
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
					<p class="text-sm text-surface-500">None yet.</p>
				{/if}
			</div>
		{/each}

		<!-- Requirement mapping sets: arrive via import, removable here -->
		{#if mappingSets.length > 0}
			<div class="card p-4 space-y-3">
				<h3 class="text-lg font-semibold">
					<i class="fa-solid fa-arrows-left-right mr-1"></i>Requirement mapping sets
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
									— {(mappingSet.requirement_mappings ?? []).length} mapping(s)
								</p>
							</div>
							<button
								type="button"
								class="btn btn-sm variant-ghost-error shrink-0"
								onclick={() => deleteObject(mappingSet)}
								aria-label="Delete mapping set"
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
					<i class="fa-solid fa-gauge-high mr-1"></i>Metric definitions
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
								aria-label="Delete metric definition"
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
			This {primaryKind} is packaged as the library
			<span class="font-mono">{draft.urn}</span> — switch to the full view for metadata, dependencies,
			imports and the other content types.
		</p>
	{/if}
</div>
