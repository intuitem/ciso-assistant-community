<script lang="ts">
	import { page } from '$app/state';
	import LevelEditor from '$lib/components/RiskMatrixEditor/LevelEditor.svelte';
	import GridEditor from '$lib/components/RiskMatrixEditor/GridEditor.svelte';
	import TranslationEditor from '$lib/components/RiskMatrixEditor/TranslationEditor.svelte';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { LOCALE_MAP, language } from '$lib/utils/locales';

	$pageTitle = m.matrixEditor();

	interface Level {
		id: number;
		abbreviation: string;
		name: string;
		description: string;
		hexcolor: string;
	}

	// Page data from server
	let { data } = $props();
	let matrices: any[] = data.matrices ?? [];
	let existingDrafts: any[] = $state(data.drafts ?? []);
	let folders: any[] = data.folders ?? [];

	// Editor state
	let draftId: string | null = $state(null);
	let matrixName = $state('');
	let matrixDescription = $state('');
	let provider = $state('');
	let locale = $state('en');
	let selectedFolder = $state(folders[0]?.id ?? '');

	let probabilityLevels: Level[] = $state([
		{
			id: 0,
			abbreviation: '1',
			name: 'Low',
			description: 'Unlikely to occur',
			hexcolor: '#4CAF50'
		},
		{ id: 1, abbreviation: '2', name: 'Medium', description: 'May occur', hexcolor: '#FF9800' },
		{ id: 2, abbreviation: '3', name: 'High', description: 'Likely to occur', hexcolor: '#F44336' }
	]);

	let impactLevels: Level[] = $state([
		{
			id: 0,
			abbreviation: '1',
			name: 'Low',
			description: 'Minor consequences',
			hexcolor: '#4CAF50'
		},
		{
			id: 1,
			abbreviation: '2',
			name: 'Medium',
			description: 'Moderate consequences',
			hexcolor: '#FF9800'
		},
		{
			id: 2,
			abbreviation: '3',
			name: 'High',
			description: 'Severe consequences',
			hexcolor: '#F44336'
		}
	]);

	let riskLevels: Level[] = $state([
		{ id: 0, abbreviation: '1', name: 'Low', description: 'Acceptable risk', hexcolor: '#4CAF50' },
		{ id: 1, abbreviation: '2', name: 'Medium', description: 'Moderate risk', hexcolor: '#FFEB3B' },
		{
			id: 2,
			abbreviation: '3',
			name: 'High',
			description: 'Significant risk',
			hexcolor: '#FF9800'
		},
		{
			id: 3,
			abbreviation: '4',
			name: 'Critical',
			description: 'Unacceptable risk',
			hexcolor: '#F44336'
		}
	]);

	let grid: number[][] = $state([
		[0, 0, 1],
		[0, 1, 2],
		[1, 2, 3]
	]);

	// Active tab
	let activeTab: string = $state('probability');

	// Status messages
	let statusMessage = $state('');
	let statusType: 'success' | 'error' | '' = $state('');
	let saving = $state(false);
	let publishing = $state(false);

	// Undo/redo history
	interface EditorSnapshot {
		probabilityLevels: Level[];
		impactLevels: Level[];
		riskLevels: Level[];
		grid: number[][];
	}

	let undoStack: EditorSnapshot[] = $state([]);
	let redoStack: EditorSnapshot[] = $state([]);
	const MAX_HISTORY = 50;

	function takeSnapshot(): EditorSnapshot {
		return {
			probabilityLevels: JSON.parse(JSON.stringify(probabilityLevels)),
			impactLevels: JSON.parse(JSON.stringify(impactLevels)),
			riskLevels: JSON.parse(JSON.stringify(riskLevels)),
			grid: JSON.parse(JSON.stringify(grid))
		};
	}

	function pushUndo() {
		undoStack = [...undoStack.slice(-(MAX_HISTORY - 1)), takeSnapshot()];
		redoStack = [];
	}

	function undo() {
		if (undoStack.length === 0) return;
		redoStack = [...redoStack, takeSnapshot()];
		const prev = undoStack[undoStack.length - 1];
		undoStack = undoStack.slice(0, -1);
		applySnapshot(prev);
	}

	function redo() {
		if (redoStack.length === 0) return;
		undoStack = [...undoStack, takeSnapshot()];
		const next = redoStack[redoStack.length - 1];
		redoStack = redoStack.slice(0, -1);
		applySnapshot(next);
	}

	function applySnapshot(snap: EditorSnapshot) {
		probabilityLevels = snap.probabilityLevels;
		impactLevels = snap.impactLevels;
		riskLevels = snap.riskLevels;
		grid = snap.grid;
	}

	// Derived: build json_definition for preview
	let jsonDefinition = $derived({
		probability: probabilityLevels,
		impact: impactLevels,
		risk: riskLevels,
		grid: grid
	});

	// For the RiskMatrix preview component (expects stringified json_definition)
	let previewRiskMatrix = $derived({
		json_definition: JSON.stringify(jsonDefinition)
	});

	// Real-time validation warnings
	let validationWarnings = $derived(() => {
		const warnings: string[] = [];
		if (probabilityLevels.length < 2) warnings.push('Need at least 2 probability levels');
		if (impactLevels.length < 2) warnings.push('Need at least 2 impact levels');
		if (riskLevels.length < 2) warnings.push('Need at least 2 risk levels');

		if (grid.length !== probabilityLevels.length) {
			warnings.push(
				`Grid rows (${grid.length}) don't match probability levels (${probabilityLevels.length})`
			);
		}
		for (let r = 0; r < grid.length; r++) {
			if (grid[r]?.length !== impactLevels.length) {
				warnings.push(
					`Grid row ${r} columns (${grid[r]?.length}) don't match impact levels (${impactLevels.length})`
				);
				break;
			}
		}

		const maxRisk = riskLevels.length - 1;
		for (let r = 0; r < grid.length; r++) {
			for (let c = 0; c < (grid[r]?.length ?? 0); c++) {
				if (grid[r][c] > maxRisk) {
					warnings.push(
						`Grid cell [${r}][${c}] references risk level ${grid[r][c]} but max is ${maxRisk}`
					);
				}
			}
		}

		for (const [cat, levels] of [
			['Probability', probabilityLevels],
			['Impact', impactLevels],
			['Risk', riskLevels]
		] as const) {
			const abbrs = new Set<string>();
			for (const level of levels) {
				if (!level.name) warnings.push(`${cat} level ${level.id} has no name`);
				if (!level.hexcolor) warnings.push(`${cat} level ${level.id} has no color`);
				if (level.abbreviation && abbrs.has(level.abbreviation)) {
					warnings.push(`${cat} has duplicate abbreviation "${level.abbreviation}"`);
				}
				abbrs.add(level.abbreviation);
			}
		}

		if (!matrixName.trim()) warnings.push('Matrix name is empty');

		return warnings;
	});

	// YAML export
	function exportAsYaml() {
		const refId = (matrixName || 'untitled')
			.toLowerCase()
			.replace(/\s+/g, '-')
			.replace(/[^a-z0-9-]/g, '');
		const libraryData = {
			urn: `urn:custom:risk:library:risk-matrix-${refId}`,
			locale: locale,
			ref_id: refId,
			name: matrixName || 'Untitled Matrix',
			description: matrixDescription,
			version: 1,
			provider: provider || 'custom',
			packager: 'custom',
			objects: {
				risk_matrix: [
					{
						urn: `urn:custom:risk:matrix:${refId}`,
						ref_id: refId,
						name: matrixName || 'Untitled Matrix',
						description: matrixDescription,
						...jsonDefinition
					}
				]
			}
		};

		// Simple YAML-like serialization (no dependency needed)
		const yamlStr = JSON.stringify(libraryData, null, 2);
		const blob = new Blob([yamlStr], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `risk-matrix-${refId}.json`;
		a.click();
		URL.revokeObjectURL(url);
	}

	// JSON import
	function importFromFile() {
		const input = document.createElement('input');
		input.type = 'file';
		input.accept = '.json,.yaml,.yml';
		input.onchange = async (e) => {
			const file = (e.target as HTMLInputElement).files?.[0];
			if (!file) return;
			try {
				const text = await file.text();
				const data = JSON.parse(text);

				// Try to find the matrix definition
				let matrixDef = data;
				if (data.objects?.risk_matrix?.[0]) {
					matrixDef = data.objects.risk_matrix[0];
					matrixName = data.name || matrixDef.name || '';
					matrixDescription = data.description || matrixDef.description || '';
					provider = data.provider || '';
					locale = data.locale || 'en';
				}

				if (matrixDef.probability) {
					pushUndo();
					probabilityLevels = matrixDef.probability;
					impactLevels = matrixDef.impact;
					riskLevels = matrixDef.risk;
					grid = matrixDef.grid;
					statusMessage = 'Imported successfully';
					statusType = 'success';
				} else {
					statusMessage = 'Invalid file: no probability/impact/risk/grid found';
					statusType = 'error';
				}
			} catch (err: any) {
				statusMessage = `Import failed: ${err.message}`;
				statusType = 'error';
			}
		};
		input.click();
	}

	// Sync grid dimensions when probability/impact levels change
	function onProbabilityChange(newLevels: Level[]) {
		pushUndo();
		probabilityLevels = newLevels;
		syncGridDimensions();
	}

	function onImpactChange(newLevels: Level[]) {
		pushUndo();
		impactLevels = newLevels;
		syncGridDimensions();
	}

	function onRiskChange(newLevels: Level[]) {
		pushUndo();
		riskLevels = newLevels;
		// Clamp any grid values that exceed the new max risk index
		const maxIdx = newLevels.length - 1;
		grid = grid.map((row) => row.map((val) => Math.min(val, maxIdx)));
	}

	function onGridChange(newGrid: number[][]) {
		pushUndo();
		grid = newGrid;
	}

	function syncGridDimensions() {
		const rows = probabilityLevels.length;
		const cols = impactLevels.length;
		const maxRiskIdx = riskLevels.length - 1;

		const newGrid: number[][] = [];
		for (let r = 0; r < rows; r++) {
			const row: number[] = [];
			for (let c = 0; c < cols; c++) {
				// Preserve existing value if within bounds
				const existing = grid[r]?.[c];
				row.push(existing !== undefined ? Math.min(existing, maxRiskIdx) : 0);
			}
			newGrid.push(row);
		}
		grid = newGrid;
	}

	// API calls
	async function saveDraft() {
		saving = true;
		statusMessage = '';
		try {
			const body = {
				name: matrixName || 'Untitled Matrix',
				description: matrixDescription,
				folder: selectedFolder,
				json_definition: jsonDefinition,
				locale,
				provider,
				status: 'draft'
			};

			const url = draftId
				? `/experimental/matrix-editor/${draftId}`
				: '/experimental/matrix-editor';
			const method = draftId ? 'PATCH' : 'POST';

			const res = await fetch(url, {
				method,
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});

			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || JSON.stringify(err));
			}

			const result = await res.json();
			draftId = result.id;
			statusMessage = m.draftSaved();
			statusType = 'success';

			// Refresh drafts list
			refreshDrafts();
		} catch (e: any) {
			statusMessage = e.message;
			statusType = 'error';
		} finally {
			saving = false;
		}
	}

	async function publishMatrix() {
		if (!draftId) {
			// Save first
			await saveDraft();
			if (!draftId) return;
		}

		if (!confirm(m.publishConfirm())) return;

		publishing = true;
		statusMessage = '';
		try {
			const res = await fetch(`/experimental/matrix-editor/${draftId}/publish`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});

			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || err.errors?.join(', ') || JSON.stringify(err));
			}

			statusMessage = m.matrixPublished();
			statusType = 'success';
			refreshDrafts();
		} catch (e: any) {
			statusMessage = e.message;
			statusType = 'error';
		} finally {
			publishing = false;
		}
	}

	async function loadDraft(draft: any) {
		draftId = draft.id;
		matrixName = draft.name;
		matrixDescription = draft.description || '';
		provider = draft.provider || '';
		locale = draft.locale || 'en';
		selectedFolder = draft.folder?.id || draft.folder || '';

		const jd =
			typeof draft.json_definition === 'string'
				? JSON.parse(draft.json_definition)
				: draft.json_definition;

		if (jd.probability) probabilityLevels = jd.probability;
		if (jd.impact) impactLevels = jd.impact;
		if (jd.risk) riskLevels = jd.risk;
		if (jd.grid) grid = jd.grid;

		statusMessage = '';
		statusType = '';
	}

	async function cloneFromMatrix(matrixId: string) {
		try {
			const res = await fetch('/experimental/matrix-editor/clone-from-matrix', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					source_matrix_id: matrixId,
					folder: selectedFolder
				})
			});

			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || JSON.stringify(err));
			}

			const draft = await res.json();
			loadDraft(draft);
			refreshDrafts();
		} catch (e: any) {
			statusMessage = e.message;
			statusType = 'error';
		}
	}

	function newMatrix() {
		draftId = null;
		matrixName = '';
		matrixDescription = '';
		provider = '';
		locale = 'en';
		probabilityLevels = [
			{
				id: 0,
				abbreviation: '1',
				name: 'Low',
				description: 'Unlikely to occur',
				hexcolor: '#4CAF50'
			},
			{ id: 1, abbreviation: '2', name: 'Medium', description: 'May occur', hexcolor: '#FF9800' },
			{
				id: 2,
				abbreviation: '3',
				name: 'High',
				description: 'Likely to occur',
				hexcolor: '#F44336'
			}
		];
		impactLevels = [
			{
				id: 0,
				abbreviation: '1',
				name: 'Low',
				description: 'Minor consequences',
				hexcolor: '#4CAF50'
			},
			{
				id: 1,
				abbreviation: '2',
				name: 'Medium',
				description: 'Moderate consequences',
				hexcolor: '#FF9800'
			},
			{
				id: 2,
				abbreviation: '3',
				name: 'High',
				description: 'Severe consequences',
				hexcolor: '#F44336'
			}
		];
		riskLevels = [
			{
				id: 0,
				abbreviation: '1',
				name: 'Low',
				description: 'Acceptable risk',
				hexcolor: '#4CAF50'
			},
			{
				id: 1,
				abbreviation: '2',
				name: 'Medium',
				description: 'Moderate risk',
				hexcolor: '#FFEB3B'
			},
			{
				id: 2,
				abbreviation: '3',
				name: 'High',
				description: 'Significant risk',
				hexcolor: '#FF9800'
			},
			{
				id: 3,
				abbreviation: '4',
				name: 'Critical',
				description: 'Unacceptable risk',
				hexcolor: '#F44336'
			}
		];
		grid = [
			[0, 0, 1],
			[0, 1, 2],
			[1, 2, 3]
		];
		statusMessage = '';
		statusType = '';
	}

	async function refreshDrafts() {
		try {
			const res = await fetch('/experimental/matrix-editor');
			if (res.ok) {
				const data = await res.json();
				existingDrafts = data.results || data;
			}
		} catch {
			// ignore
		}
	}

	async function deleteDraft(id: string) {
		if (!confirm('Delete this draft?')) return;
		try {
			const res = await fetch(`/experimental/matrix-editor/${id}`, { method: 'DELETE' });
			if (res.ok || res.status === 204) {
				if (draftId === id) {
					newMatrix();
				}
				refreshDrafts();
			}
		} catch {
			// ignore
		}
	}

	function onTranslationsChange(newProb: Level[], newImpact: Level[], newRisk: Level[]) {
		pushUndo();
		probabilityLevels = newProb;
		impactLevels = newImpact;
		riskLevels = newRisk;
	}

	const tabs = [
		{ id: 'probability', label: m.probability, icon: 'fa-solid fa-arrow-up' },
		{ id: 'impact', label: m.impact, icon: 'fa-solid fa-arrow-right' },
		{ id: 'risk', label: () => m.riskLevels(), icon: 'fa-solid fa-exclamation-triangle' },
		{ id: 'grid', label: m.grid, icon: 'fa-solid fa-table-cells' },
		{ id: 'i18n', label: m.translations, icon: 'fa-solid fa-language' }
	];
</script>

<div class="space-y-6">
	<!-- Top bar: actions -->
	<div class="card p-4">
		<div class="flex flex-wrap items-center justify-between gap-4">
			<div class="flex items-center gap-2">
				<button type="button" class="btn variant-filled-primary btn-sm" onclick={newMatrix}>
					<i class="fa-solid fa-plus mr-1"></i>
					{m.newMatrix()}
				</button>
				<button type="button" class="btn variant-ghost-surface btn-sm" onclick={importFromFile}>
					<i class="fa-solid fa-file-import mr-1"></i>
					Import
				</button>
				<button type="button" class="btn variant-ghost-surface btn-sm" onclick={exportAsYaml}>
					<i class="fa-solid fa-file-export mr-1"></i>
					Export
				</button>

				<!-- Clone from existing -->
				{#if matrices.length > 0}
					<div class="relative">
						<select
							class="select select-sm w-64"
							onchange={(e) => {
								const val = e.currentTarget.value;
								if (val) cloneFromMatrix(val);
								e.currentTarget.value = '';
							}}
						>
							<option value="">{m.cloneFromExisting()}...</option>
							{#each matrices as matrix}
								<option value={matrix.id}>{matrix.name}</option>
							{/each}
						</select>
					</div>
				{/if}
			</div>

			<div class="flex items-center gap-2">
				<!-- Undo/Redo -->
				<button
					type="button"
					class="btn btn-sm variant-ghost"
					disabled={undoStack.length === 0}
					onclick={undo}
					title="Undo (Ctrl+Z)"
				>
					<i class="fa-solid fa-rotate-left"></i>
				</button>
				<button
					type="button"
					class="btn btn-sm variant-ghost"
					disabled={redoStack.length === 0}
					onclick={redo}
					title="Redo (Ctrl+Y)"
				>
					<i class="fa-solid fa-rotate-right"></i>
				</button>
				<span class="border-l border-gray-300 h-6 mx-1"></span>
				{#if statusMessage}
					<span class="text-sm {statusType === 'error' ? 'text-red-600' : 'text-green-600'}">
						{statusMessage}
					</span>
				{/if}
				<button
					type="button"
					class="btn variant-filled-secondary btn-sm"
					onclick={saveDraft}
					disabled={saving}
				>
					<i class="fa-solid fa-floppy-disk mr-1"></i>
					{saving ? '...' : m.saveDraft()}
				</button>
				<button
					type="button"
					class="btn variant-filled-success btn-sm"
					onclick={publishMatrix}
					disabled={publishing}
				>
					<i class="fa-solid fa-rocket mr-1"></i>
					{publishing ? '...' : m.publishMatrix()}
				</button>
			</div>
		</div>
	</div>

	<!-- Saved drafts -->
	<div class="card p-4">
		<h3 class="text-lg font-semibold mb-3">
			<i class="fa-solid fa-file-pen mr-1"></i>
			{m.saveDraft()}s ({existingDrafts.length})
		</h3>
		{#if existingDrafts.length > 0}
			<div class="table-container">
				<table class="table table-compact w-full">
					<thead>
						<tr>
							<th>{m.name()}</th>
							<th>{m.description()}</th>
							<th>Status</th>
							<th>{m.locale()}</th>
							<th>{m.provider()}</th>
							<th class="w-32"></th>
						</tr>
					</thead>
					<tbody>
						{#each existingDrafts as draft}
							<tr class={draftId === draft.id ? 'bg-primary-50 ring-1 ring-primary-200' : ''}>
								<td class="font-medium">{draft.name}</td>
								<td class="text-sm text-gray-500 truncate max-w-48">{draft.description || '—'}</td>
								<td>
									<span
										class="badge {draft.status === 'published'
											? 'variant-filled-success'
											: 'variant-filled-warning'} text-xs"
									>
										{draft.status}
									</span>
								</td>
								<td class="text-sm">{draft.locale}</td>
								<td class="text-sm text-gray-500">{draft.provider || '—'}</td>
								<td class="flex gap-1">
									<button
										type="button"
										class="btn btn-sm variant-ghost-primary"
										onclick={() => loadDraft(draft)}
										title={m.resumeDraft()}
									>
										<i class="fa-solid fa-pen-to-square"></i>
									</button>
									<button
										type="button"
										class="btn btn-sm variant-ghost-error"
										onclick={() => deleteDraft(draft.id)}
										title="Delete"
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
			<p class="text-sm text-gray-400 py-4 text-center">
				No drafts yet. Create one using the editor below.
			</p>
		{/if}
	</div>

	<!-- Metadata -->
	<div class="card p-4">
		<h3 class="text-lg font-semibold mb-3">{m.metadata()}</h3>
		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
			<div>
				<label class="label" for="matrix-name">
					<span>{m.name()}</span>
				</label>
				<input
					id="matrix-name"
					type="text"
					class="input"
					bind:value={matrixName}
					placeholder="Matrix name..."
				/>
			</div>
			<div>
				<label class="label" for="matrix-desc">
					<span>{m.description()}</span>
				</label>
				<input
					id="matrix-desc"
					type="text"
					class="input"
					bind:value={matrixDescription}
					placeholder="Description..."
				/>
			</div>
			<div>
				<label class="label" for="matrix-provider">
					<span>{m.provider()}</span>
				</label>
				<input
					id="matrix-provider"
					type="text"
					class="input"
					bind:value={provider}
					placeholder="Provider..."
				/>
			</div>
			<div>
				<label class="label" for="matrix-locale">
					<span>{m.locale()}</span>
				</label>
				<select id="matrix-locale" class="select" bind:value={locale}>
					{#each Object.entries(LOCALE_MAP) as [code, info]}
						<option value={code}>{language[info.name] ?? info.name} ({code})</option>
					{/each}
				</select>
			</div>
			<div>
				<label class="label" for="matrix-folder">
					<span>{m.domain()}</span>
				</label>
				<select id="matrix-folder" class="select" bind:value={selectedFolder}>
					{#each folders as folder}
						<option value={folder.id}>{folder.str}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>

	<!-- Editor tabs -->
	<div class="card p-4">
		<div class="flex border-b mb-4 gap-1">
			{#each tabs as tab}
				<button
					type="button"
					class="px-4 py-2 text-sm font-medium rounded-t transition-colors
						{activeTab === tab.id
						? 'bg-primary-500 text-white'
						: 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
					onclick={() => (activeTab = tab.id)}
				>
					<i class="{tab.icon} mr-1"></i>
					{typeof tab.label === 'function' ? tab.label() : tab.label()}
				</button>
			{/each}
		</div>

		{#if activeTab === 'probability'}
			<LevelEditor
				title={m.probability()}
				bind:levels={probabilityLevels}
				onchange={onProbabilityChange}
			/>
		{:else if activeTab === 'impact'}
			<LevelEditor title={m.impact()} bind:levels={impactLevels} onchange={onImpactChange} />
		{:else if activeTab === 'risk'}
			<LevelEditor title={m.riskLevels()} bind:levels={riskLevels} onchange={onRiskChange} />
		{:else if activeTab === 'grid'}
			<GridEditor
				bind:grid
				{probabilityLevels}
				{impactLevels}
				{riskLevels}
				onchange={onGridChange}
			/>
		{:else if activeTab === 'i18n'}
			<TranslationEditor
				bind:probabilityLevels
				bind:impactLevels
				bind:riskLevels
				onchange={onTranslationsChange}
			/>
		{/if}
	</div>

	<!-- Validation warnings -->
	{#if validationWarnings().length > 0}
		<div class="card p-3 border-l-4 border-yellow-400 bg-yellow-50">
			<div class="flex items-start gap-2">
				<i class="fa-solid fa-triangle-exclamation text-yellow-600 mt-0.5"></i>
				<div>
					<p class="font-semibold text-sm text-yellow-800">{m.invalidMatrix()}</p>
					<ul class="text-xs text-yellow-700 mt-1 list-disc list-inside">
						{#each validationWarnings() as warning}
							<li>{warning}</li>
						{/each}
					</ul>
				</div>
			</div>
		</div>
	{/if}

	<!-- Live preview -->
	<div class="card p-4">
		<h3 class="text-lg font-semibold mb-3">
			<i class="fa-solid fa-eye mr-1"></i>
			{m.matrixPreview()}
		</h3>
		{#if probabilityLevels.length >= 2 && impactLevels.length >= 2 && riskLevels.length >= 2}
			<div class="max-w-3xl mx-auto">
				{#key JSON.stringify(jsonDefinition)}
					<RiskMatrix
						riskMatrix={previewRiskMatrix}
						matrixName="editor-preview"
						showLegend={true}
					/>
				{/key}
			</div>
		{:else}
			<p class="text-gray-500 text-center py-8">
				{m.invalidMatrix()} — need at least 2 levels for each dimension.
			</p>
		{/if}
	</div>
</div>
