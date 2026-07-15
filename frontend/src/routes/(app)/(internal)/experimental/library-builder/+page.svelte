<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { defaultMatrixObject, identitySlug } from './builder-helpers';

	$pageTitle = m.lbListLibraryBuilder();

	let { data } = $props();
	let drafts: any[] = $state(data.drafts ?? []);
	let customLibraries: any[] = $state(data.customLibraries ?? []);
	let orphanFrameworks: any[] = $state(data.orphanFrameworks ?? []);

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

	// --- Create form -------------------------------------------------------
	let showCreate = $state(false);
	let creating = $state(false);
	let newName = $state('');
	let newPackager = $state('');
	let newRefId = $state('');
	let identityCheck: { urn?: string; conflicts?: any[]; error?: string } | null = $state(null);
	let checkTimeout: ReturnType<typeof setTimeout> | null = null;

	const IDENTITY_RE = /^[a-z0-9_-]+$/;

	function scheduleIdentityCheck() {
		identityCheck = null;
		if (checkTimeout) clearTimeout(checkTimeout);
		if (!IDENTITY_RE.test(newPackager) || !IDENTITY_RE.test(newRefId)) return;
		checkTimeout = setTimeout(async () => {
			const params = new URLSearchParams({ packager: newPackager, ref_id: newRefId });
			const res = await fetch(`/experimental/library-builder?${params}`);
			// A permission-denied / empty-body response has no JSON to parse.
			identityCheck = res.ok ? await res.json() : null;
		}, 350);
	}

	async function createDraft() {
		creating = true;
		try {
			rememberPackager(newPackager);
			const res = await fetch('/experimental/library-builder', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					action: 'create',
					name: newName || newRefId,
					packager: newPackager,
					ref_id: newRefId
				})
			});
			const result = await res.json();
			if (!res.ok)
				throw new Error(result.error ? safeTranslate(result.error) : JSON.stringify(result));
			window.location.href = `/experimental/library-builder/${result.id}`;
		} catch (e: any) {
			setStatus(e.message, 'error');
			creating = false;
		}
	}

	// --- Import a YAML file directly (no corpus round-trip) ----------------
	let importingYaml = $state(false);

	async function importYaml(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		input.value = ''; // allow re-selecting the same file after an error
		if (!file) return;
		importingYaml = true;
		try {
			const form = new FormData();
			form.append('file', file);
			const res = await fetch('/experimental/library-builder', {
				method: 'POST',
				body: form
			});
			const result = await res.json();
			if (!res.ok)
				throw new Error(
					result.detail || (result.error ? safeTranslate(result.error) : JSON.stringify(result))
				);
			window.location.href = `/experimental/library-builder/${result.id}`;
		} catch (e: any) {
			setStatus(e.message, 'error');
			importingYaml = false;
		}
	}

	// --- Adopt -------------------------------------------------------------
	let adoptSource = $state('');
	let adopting = $state(false);

	async function adoptLibrary() {
		if (!adoptSource) return;
		adopting = true;
		try {
			// Values are "library:<id>" or "framework:<id>" (library-less live
			// framework from the retired standalone editor, adopted in place).
			const [kind, id] = adoptSource.split(':', 2);
			const body =
				kind === 'framework'
					? { action: 'adopt', framework: id }
					: { action: 'adopt', stored_library: id };
			const res = await fetch('/experimental/library-builder', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			const result = await res.json();
			if (res.status === 409 && result.draft) {
				window.location.href = `/experimental/library-builder/${result.draft}`;
				return;
			}
			if (!res.ok)
				throw new Error(result.error ? safeTranslate(result.error) : JSON.stringify(result));
			window.location.href = `/experimental/library-builder/${result.id}`;
		} catch (e: any) {
			setStatus(e.message, 'error');
			adopting = false;
		}
	}

	// --- Quick create: a single-object library that feels like no library ----
	// "New framework" / "New matrix" ask for a name and a packager — the two
	// parameters every URN of the family derives from. The packager is
	// remembered across uses (typed once); the ref_id is slugged from the
	// name and deduped against the corpus. The wrapping library is minted
	// behind the scenes and the user lands straight in the object's editor.
	const PACKAGER_KEY = 'library-builder:packager';
	let quickKind: 'framework' | 'matrix' | null = $state(null);
	let quickName = $state('');
	let quickPackager = $state('');
	let quickCreating = $state(false);

	function rememberedPackager(): string {
		try {
			return localStorage.getItem(PACKAGER_KEY) ?? '';
		} catch {
			return '';
		}
	}

	function rememberPackager(packager: string) {
		try {
			localStorage.setItem(PACKAGER_KEY, packager);
		} catch {
			/* storage unavailable — the value just won't persist */
		}
	}

	function openQuick(kind: 'framework' | 'matrix') {
		quickKind = quickKind === kind ? null : kind;
		showCreate = false;
		if (!quickPackager) quickPackager = rememberedPackager() || data.defaultPackager;
	}

	async function freeIdentity(packager: string, slugBase: string): Promise<string> {
		let refId = slugBase;
		for (let suffix = 2; suffix <= 9; suffix++) {
			const draftTaken = drafts.some((d) => d.packager === packager && d.ref_id === refId);
			let conflicted = draftTaken;
			if (!conflicted) {
				const params = new URLSearchParams({ packager, ref_id: refId });
				const res = await fetch(`/experimental/library-builder?${params}`);
				const check = res.ok ? await res.json() : {};
				conflicted = (check.conflicts?.length ?? 0) > 0;
			}
			if (!conflicted) return refId;
			refId = `${slugBase}-${suffix}`;
		}
		return refId;
	}

	async function createQuick() {
		const kind = quickKind;
		const slugBase = identitySlug(quickName);
		const packager = quickPackager.trim();
		if (!kind || !slugBase || !IDENTITY_RE.test(packager)) return;
		quickCreating = true;
		try {
			rememberPackager(packager);
			const refId = await freeIdentity(packager, slugBase);
			const createRes = await fetch('/experimental/library-builder', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ action: 'create', name: quickName, packager, ref_id: refId })
			});
			const created = await createRes.json();
			if (!createRes.ok)
				throw new Error(created.error ? safeTranslate(created.error) : JSON.stringify(created));
			const draftBase = `/experimental/library-builder/${created.id}`;

			if (kind === 'framework') {
				const res = await fetch(draftBase, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ action: 'add-framework' })
				});
				const result = await res.json();
				if (!res.ok)
					throw new Error(result.error ? safeTranslate(result.error) : JSON.stringify(result));
				window.location.href = `${draftBase}/framework?framework_urn=${encodeURIComponent(
					result.framework_urn
				)}`;
			} else {
				const res = await fetch(draftBase, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						action: 'upsert-object',
						field: 'risk_matrices',
						object: defaultMatrixObject(refId, quickName)
					})
				});
				const result = await res.json();
				if (!res.ok)
					throw new Error(result.error ? safeTranslate(result.error) : JSON.stringify(result));
				window.location.href = `${draftBase}/matrix?matrix_urn=${encodeURIComponent(
					result.object.urn
				)}`;
			}
		} catch (e: any) {
			setStatus(e.message, 'error');
			quickCreating = false;
		}
	}

	// --- Delete ------------------------------------------------------------
	async function deleteDraft(draft: any) {
		if (!confirm(m.lbListDeleteConfirm({ name: draft.name }))) return;
		const res = await fetch(`/experimental/library-builder?id=${draft.id}`, { method: 'DELETE' });
		if (res.ok) {
			drafts = drafts.filter((d) => d.id !== draft.id);
			setStatus(m.lbListDraftDeleted(), 'success');
		} else {
			setStatus(m.lbListDeleteDraftFailed(), 'error');
		}
	}

	// Each object kind gets a count-aware, localized label (singular/plural
	// handled by the message). Unknown keys fall back to the raw key.
	const OBJECT_LABELS: Record<string, (args: { count: number }) => string> = {
		frameworks: m.lbCountFrameworks,
		threats: m.lbCountThreats,
		reference_controls: m.lbCountReferenceControls,
		risk_matrices: m.lbCountRiskMatrices,
		requirement_mapping_sets: m.lbCountRequirementMappingSets,
		metric_definitions: m.lbCountMetricDefinitions,
		preset: m.lbCountPreset
	};

	function objectsSummary(draft: any): string {
		const meta = draft.objects_meta ?? {};
		const parts = Object.entries(meta)
			.filter(([, v]) => (v as number) > 0)
			.map(([k, v]) => {
				const label = OBJECT_LABELS[k];
				return label ? label({ count: v as number }) : `${v} ${k.replaceAll('_', ' ')}`;
			});
		return parts.length ? parts.join(', ') : m.lbListEmpty();
	}
</script>

<div class="space-y-6">
	<!-- Top bar -->
	<div class="card p-4">
		<p class="text-xs text-surface-600-400 mb-4">
			{m.lbListIntro()}
		</p>
		<div class="flex flex-wrap items-center justify-between gap-4">
			<div class="flex items-center gap-2">
				<button
					type="button"
					class="btn btn-sm bg-primary-500 text-white hover:bg-primary-600 transition-colors"
					onclick={() => openQuick('framework')}
				>
					<i class="fa-solid fa-sitemap mr-1"></i>
					{m.lbListNewFramework()}
				</button>
				<button
					type="button"
					class="btn btn-sm bg-primary-500 text-white hover:bg-primary-600 transition-colors"
					onclick={() => openQuick('matrix')}
				>
					<i class="fa-solid fa-table-cells mr-1"></i>
					{m.lbListNewMatrix()}
				</button>
				<button
					type="button"
					class="btn btn-sm variant-ghost-primary"
					onclick={() => {
						showCreate = !showCreate;
						quickKind = null;
						if (!newPackager) newPackager = rememberedPackager() || data.defaultPackager;
					}}
				>
					<i class="fa-solid fa-plus mr-1"></i>
					{m.lbListNewLibraryDraft()}
				</button>
				<label
					class="btn btn-sm variant-ghost-primary cursor-pointer"
					title={m.lbListImportYamlTooltip()}
				>
					{#if importingYaml}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
					{:else}
						<i class="fa-solid fa-file-arrow-up mr-1"></i>
					{/if}
					{m.lbListImportYaml()}
					<input
						type="file"
						accept=".yaml,.yml"
						class="hidden"
						disabled={importingYaml}
						onchange={importYaml}
					/>
				</label>
				{#if customLibraries.length > 0 || orphanFrameworks.length > 0}
					<select class="select w-64 text-sm" bind:value={adoptSource}>
						<option value="">{m.lbListAdoptPlaceholder()}</option>
						{#if customLibraries.length > 0}
							<optgroup label={m.lbListCustomLibraries()}>
								{#each customLibraries as library}
									<option value={'library:' + library.id}>
										{library.name} (v{library.version})
									</option>
								{/each}
							</optgroup>
						{/if}
						{#if orphanFrameworks.length > 0}
							<optgroup label={m.lbListCustomFrameworksNoLibrary()}>
								{#each orphanFrameworks as framework}
									<option value={'framework:' + framework.id}>{framework.name}</option>
								{/each}
							</optgroup>
						{/if}
					</select>
					<button
						type="button"
						class="btn btn-sm variant-ghost-primary"
						onclick={adoptLibrary}
						disabled={!adoptSource || adopting}
					>
						{#if adopting}
							<i class="fa-solid fa-spinner fa-spin mr-1"></i>
						{:else}
							<i class="fa-solid fa-file-import mr-1"></i>
						{/if}
						{m.lbListAdopt()}
					</button>
				{/if}
			</div>
			{#if statusMessage}
				<span
					class="text-xs px-2 py-1 rounded-full transition-opacity {statusType === 'error'
						? 'bg-red-100 text-red-700'
						: 'bg-green-100 text-green-700'}"
				>
					<i class="fa-solid {statusType === 'error' ? 'fa-circle-xmark' : 'fa-circle-check'} mr-1"
					></i>
					{statusMessage}
				</span>
			{/if}
		</div>

		{#if quickKind}
			<div class="mt-4 border-t border-surface-200-800 pt-4 flex flex-wrap items-end gap-3">
				<label class="label text-sm grow max-w-md">
					<span>{quickKind === 'framework' ? m.lbListFrameworkName() : m.lbListMatrixName()}</span>
					<!-- svelte-ignore a11y_autofocus -->
					<input
						class="input"
						type="text"
						bind:value={quickName}
						placeholder={quickKind === 'framework'
							? m.lbListFrameworkNamePlaceholder()
							: m.lbListMatrixNamePlaceholder()}
						autofocus
						onkeydown={(e) => e.key === 'Enter' && createQuick()}
					/>
				</label>
				<label class="label text-sm w-48">
					<span>{m.packager()}</span>
					<input
						class="input"
						type="text"
						bind:value={quickPackager}
						placeholder="my-org"
						onkeydown={(e) => e.key === 'Enter' && createQuick()}
					/>
				</label>
				<button
					type="button"
					class="btn btn-sm variant-filled-primary"
					onclick={createQuick}
					disabled={quickCreating ||
						!identitySlug(quickName) ||
						!IDENTITY_RE.test(quickPackager.trim())}
				>
					{#if quickCreating}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
					{:else}
						<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>
					{/if}
					{m.lbListCreateAndEdit()}
				</button>
				<div class="basis-full text-xs space-y-1">
					{#if quickPackager && !IDENTITY_RE.test(quickPackager.trim())}
						<p class="text-red-600">{m.lbListPackagerPattern()}</p>
					{/if}
					{#if identitySlug(quickName) && IDENTITY_RE.test(quickPackager.trim())}
						<p class="text-surface-500 font-mono">
							urn:{quickPackager.trim()}:risk:{quickKind}:{identitySlug(quickName)}
						</p>
					{/if}
					<p class="text-surface-500">
						{quickKind === 'framework' ? m.lbListQuickHelpFramework() : m.lbListQuickHelpMatrix()}
					</p>
				</div>
			</div>
		{/if}

		{#if showCreate}
			<div class="mt-4 border-t border-surface-200-800 pt-4 grid grid-cols-1 md:grid-cols-4 gap-3">
				<label class="label text-sm">
					<span>{m.name()}</span>
					<input
						class="input"
						type="text"
						bind:value={newName}
						placeholder={m.lbListLibraryNamePlaceholder()}
					/>
				</label>
				<label class="label text-sm">
					<span>{m.packager()}</span>
					<input
						class="input"
						type="text"
						bind:value={newPackager}
						oninput={scheduleIdentityCheck}
						placeholder="my-org"
					/>
				</label>
				<label class="label text-sm">
					<span>{m.lbListReferenceId()}</span>
					<input
						class="input"
						type="text"
						bind:value={newRefId}
						oninput={scheduleIdentityCheck}
						placeholder="my-library"
					/>
				</label>
				<div class="flex items-end">
					<button
						type="button"
						class="btn btn-sm variant-filled-primary"
						onclick={createDraft}
						disabled={creating || !IDENTITY_RE.test(newPackager) || !IDENTITY_RE.test(newRefId)}
					>
						{#if creating}
							<i class="fa-solid fa-spinner fa-spin mr-1"></i>
						{/if}
						{m.create()}
					</button>
				</div>
				<div class="md:col-span-4 text-xs space-y-1">
					{#if newPackager && !IDENTITY_RE.test(newPackager)}
						<p class="text-red-600">{m.lbListPackagerPattern()}</p>
					{/if}
					{#if newRefId && !IDENTITY_RE.test(newRefId)}
						<p class="text-red-600">{m.lbListReferenceIdPattern()}</p>
					{/if}
					{#if identityCheck?.urn}
						<p class="text-surface-500 font-mono">{identityCheck.urn}</p>
						{#if identityCheck.conflicts?.length}
							<p class="text-amber-600">
								<i class="fa-solid fa-triangle-exclamation mr-1"></i>
								{m.lbListIdentityCollides({
									count: identityCheck.conflicts.length,
									objects:
										identityCheck.conflicts
											.slice(0, 3)
											.map((c: any) => `${c.kind} ${c.urn}`)
											.join('; ') + (identityCheck.conflicts.length > 3 ? '…' : '')
								})}
							</p>
						{:else}
							<p class="text-green-600">
								<i class="fa-solid fa-circle-check mr-1"></i>{m.lbListIdentityFree()}
							</p>
						{/if}
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<!-- Drafts -->
	<div class="card p-4">
		<h3 class="text-lg font-semibold mb-3">
			<i class="fa-solid fa-boxes-packing mr-1"></i>
			{m.lbListLibraryDrafts()}
		</h3>
		{#if drafts.length > 0}
			<div class="table-container">
				<table class="table table-compact w-full">
					<thead>
						<tr>
							<th>{m.name()}</th>
							<th>URN</th>
							<th>{m.version()}</th>
							<th>{m.lbListContents()}</th>
							<th>{m.status()}</th>
							<th class="w-40"></th>
						</tr>
					</thead>
					<tbody>
						{#each drafts as draft}
							<tr>
								<td class="font-medium">{draft.name}</td>
								<td class="text-xs font-mono text-surface-600-400 max-w-64 truncate">
									{draft.urn}
								</td>
								<td class="text-sm">v{draft.version}</td>
								<td class="text-sm text-surface-600-400">{objectsSummary(draft)}</td>
								<td>
									<!-- Published = identity committed (frozen), whether by the
									     user's publish decision or by proof (loaded / adopted /
									     in-use content). Three states: Draft; Published; Published
									     with edits not yet re-published. -->
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
								</td>
								<td class="space-x-1">
									<a
										href="/experimental/library-builder/{draft.id}"
										class="btn btn-sm variant-filled-primary"
									>
										<i class="fa-solid fa-pen-to-square mr-1"></i>
										{m.edit()}
									</a>
									<button
										type="button"
										class="btn btn-sm variant-ghost-error"
										onclick={() => deleteDraft(draft)}
										aria-label={m.lbListDeleteDraft()}
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
			<p class="text-sm text-surface-500 py-4 text-center">
				{m.lbListNoDrafts()}
			</p>
		{/if}
	</div>
</div>
