<script lang="ts">
	import { page } from '$app/state';
	import LevelEditor from '$lib/components/RiskMatrixEditor/LevelEditor.svelte';
	import GridEditor from '$lib/components/RiskMatrixEditor/GridEditor.svelte';
	import TranslationEditor from '$lib/components/RiskMatrixEditor/TranslationEditor.svelte';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { LOCALE_MAP, language } from '$lib/utils/locales';
	import { onMount } from 'svelte';

	$pageTitle = m.matrixEditor();

	// Warn before leaving with unsaved changes
	onMount(() => {
		const handler = (e: BeforeUnloadEvent) => {
			if (hasUnsavedChanges) {
				e.preventDefault();
			}
		};
		window.addEventListener('beforeunload', handler);
		return () => window.removeEventListener('beforeunload', handler);
	});

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
	let matrixId: string | null = $state(null);
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

	// Auto-load the most recent draft on page load
	if (existingDrafts.length > 0) {
		const latest = existingDrafts[0];
		matrixId = latest.id;
		matrixName = latest.name || '';
		matrixDescription = latest.description || '';
		provider = latest.provider || '';
		locale = latest.locale || 'en';
		selectedFolder = latest.folder?.id || latest.folder || selectedFolder;

		const src = latest.editing_draft || latest.json_definition;
		const jd = typeof src === 'string' ? JSON.parse(src) : src;
		if (jd?.probability) probabilityLevels = jd.probability;
		if (jd?.impact) impactLevels = jd.impact;
		if (jd?.risk) riskLevels = jd.risk;
		if (jd?.grid) grid = jd.grid;
	}

	// Active tab
	let activeTab: string = $state('probability');

	// Status messages with auto-dismiss
	let statusMessage = $state('');
	let statusType: 'success' | 'error' | '' = $state('');
	let saving = $state(false);
	let publishing = $state(false);
	let statusTimeout: ReturnType<typeof setTimeout> | null = null;
	let hasUnsavedChanges = $state(false);
	let lastSavedSnapshot = $state('');

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

	// Track dirty state — only when a matrix is actively being edited
	let currentSnapshot = $derived(
		JSON.stringify({ matrixName, matrixDescription, provider, ...jsonDefinition })
	);
	$effect(() => {
		hasUnsavedChanges = matrixId !== null && currentSnapshot !== lastSavedSnapshot;
	});

	function markClean() {
		lastSavedSnapshot = currentSnapshot;
		hasUnsavedChanges = false;
	}

	// Real-time validation warnings
	let validationWarnings = $derived(() => {
		const warnings: string[] = [];
		if (probabilityLevels.length < 2)
			warnings.push(m.needAtLeast2Levels({ category: m.probability() }));
		if (impactLevels.length < 2) warnings.push(m.needAtLeast2Levels({ category: m.impact() }));
		if (riskLevels.length < 2) warnings.push(m.needAtLeast2Levels({ category: m.riskLevels() }));

		if (grid.length !== probabilityLevels.length) {
			warnings.push(
				m.gridRowsMismatch({
					gridRows: String(grid.length),
					probLevels: String(probabilityLevels.length)
				})
			);
		}
		for (let r = 0; r < grid.length; r++) {
			if (grid[r]?.length !== impactLevels.length) {
				warnings.push(
					m.gridColsMismatch({
						row: String(r),
						gridCols: String(grid[r]?.length),
						impactLevels: String(impactLevels.length)
					})
				);
				break;
			}
		}

		const maxRisk = riskLevels.length - 1;
		for (let r = 0; r < grid.length; r++) {
			for (let c = 0; c < (grid[r]?.length ?? 0); c++) {
				if (grid[r][c] > maxRisk) {
					warnings.push(
						m.invalidGridCell({
							row: String(r),
							col: String(c),
							value: String(grid[r][c]),
							max: String(maxRisk)
						})
					);
				}
			}
		}

		for (const [cat, levels] of [
			[m.probability(), probabilityLevels],
			[m.impact(), impactLevels],
			[m.riskLevels(), riskLevels]
		] as [string, Level[]][]) {
			const abbrs = new Set<string>();
			for (const level of levels) {
				if (!level.name) warnings.push(m.levelMissingName({ category: cat, id: String(level.id) }));
				if (!level.hexcolor)
					warnings.push(m.levelMissingColor({ category: cat, id: String(level.id) }));
				if (level.abbreviation && abbrs.has(level.abbreviation)) {
					warnings.push(
						m.duplicateAbbreviation({ category: cat, abbreviation: level.abbreviation })
					);
				}
				abbrs.add(level.abbreviation);
			}
		}

		if (!matrixName.trim()) warnings.push(m.matrixNameEmpty());

		return warnings;
	});

	// Export as library YAML (server-side)
	async function exportAsYaml() {
		if (!matrixId) {
			// Save first so there's something to export
			await saveDraft();
			if (!matrixId) return;
		}
		try {
			const res = await fetch(`/experimental/matrix-editor/${matrixId}?action=export-yaml`);
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || m.exportFailed());
			}
			const blob = await res.blob();
			const disposition = res.headers.get('Content-Disposition') || '';
			const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
			const filename = filenameMatch?.[1] || 'risk-matrix.yaml';

			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = filename;
			a.click();
			URL.revokeObjectURL(url);
			setStatus(m.exportedAsYaml(), 'success');
		} catch (e: any) {
			setStatus(e.message, 'error');
		}
	}

	// Import from library YAML file (server-side parsing)
	function importFromFile() {
		const input = document.createElement('input');
		input.type = 'file';
		input.accept = '.yaml,.yml';
		input.onchange = async (e) => {
			const file = (e.target as HTMLInputElement).files?.[0];
			if (!file) return;
			try {
				const formData = new FormData();
				formData.append('file', file);

				const res = await fetch('/experimental/matrix-editor?action=import-yaml', {
					method: 'POST',
					body: formData
				});

				if (!res.ok) {
					const err = await res.json();
					throw new Error(err.error || m.importFailed());
				}

				const result = await res.json();
				// Load the newly created draft
				loadDraft({
					id: result.id,
					name: result.name,
					editing_draft: result.editing_draft
				});
				refreshDrafts();
				setStatus(m.importedSuccessfully(), 'success');
			} catch (err: any) {
				setStatus(`${m.importFailed()}: ${err.message}`, 'error');
			}
		};
		input.click();
	}

	// Sync grid dimensions when probability/impact levels change
	function onProbabilityChange(newLevels: Level[]) {
		probabilityLevels = newLevels;
		syncGridDimensions();
	}

	function onImpactChange(newLevels: Level[]) {
		impactLevels = newLevels;
		syncGridDimensions();
	}

	function onRiskChange(newLevels: Level[]) {
		riskLevels = newLevels;
		// Clamp any grid values that exceed the new max risk index
		const maxIdx = newLevels.length - 1;
		grid = grid.map((row) => row.map((val) => Math.min(val, maxIdx)));
	}

	function onGridChange(newGrid: number[][]) {
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
			if (!matrixId) {
				// Create a new matrix with an editing_draft
				const res = await fetch('/experimental/matrix-editor', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						name: matrixName || 'Untitled Matrix',
						description: matrixDescription,
						folder: selectedFolder,
						editing_draft: jsonDefinition
					})
				});
				if (!res.ok) {
					const err = await res.json();
					throw new Error(err.error || JSON.stringify(err));
				}
				const result = await res.json();
				matrixId = result.id;
			} else {
				// Save editing_draft on existing matrix
				const res = await fetch(`/experimental/matrix-editor/${matrixId}`, {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						editing_draft: jsonDefinition,
						name: matrixName || 'Untitled Matrix',
						description: matrixDescription,
						provider
					})
				});
				if (!res.ok) {
					const err = await res.json();
					throw new Error(err.error || JSON.stringify(err));
				}
			}
			markClean();
			setStatus(m.draftSaved(), 'success');
			refreshDrafts();
		} catch (e: any) {
			setStatus(e.message, 'error');
		} finally {
			saving = false;
		}
	}

	async function publishMatrix() {
		if (!matrixId) {
			await saveDraft();
			if (!matrixId) return;
		}

		if (!confirm(m.publishConfirm())) return;

		publishing = true;
		statusMessage = '';
		try {
			const res = await fetch(`/experimental/matrix-editor/${matrixId}?action=publish-draft`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});

			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || err.errors?.join(', ') || JSON.stringify(err));
			}

			setStatus(m.matrixPublished(), 'success');
			refreshDrafts();
		} catch (e: any) {
			setStatus(e.message, 'error');
		} finally {
			publishing = false;
		}
	}

	/** Discard the editing_draft on the currently active matrix (if any) before switching. */
	async function discardCurrentDraft() {
		if (!matrixId) return true;
		if (hasUnsavedChanges) {
			if (!confirm(m.discardUnsavedConfirm())) return false;
		}
		// Discard the editing_draft on the current matrix
		try {
			await fetch(`/experimental/matrix-editor/${matrixId}?action=discard-draft`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});
		} catch {
			// If discard fails (e.g. unpublished matrix), ignore — we'll still switch
		}
		matrixId = null;
		hasUnsavedChanges = false;
		return true;
	}

	async function editPublishedMatrix(id: string) {
		if (!(await discardCurrentDraft())) return;
		try {
			// Start editing: copies json_definition → editing_draft on the same object
			const res = await fetch(`/experimental/matrix-editor/${id}?action=start-editing`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || JSON.stringify(err));
			}
			const result = await res.json();
			// Find the matrix in our list and load it
			const matrix = matrices.find((m: any) => m.id === id);
			if (matrix) {
				matrix.editing_draft = result.editing_draft;
				loadDraft(matrix);
			}
			refreshDrafts();
		} catch (e: any) {
			setStatus(e.message, 'error');
		}
	}

	async function loadDraft(matrix: any) {
		matrixId = matrix.id;
		matrixName = matrix.name;
		matrixDescription = matrix.description || '';
		provider = matrix.provider || '';
		locale = matrix.locale || 'en';
		selectedFolder = matrix.folder?.id || matrix.folder || '';

		// Load from editing_draft (WIP) if available, otherwise from json_definition
		const src = matrix.editing_draft || matrix.json_definition;
		const jd = typeof src === 'string' ? JSON.parse(src) : src;

		if (jd?.probability) probabilityLevels = jd.probability;
		if (jd?.impact) impactLevels = jd.impact;
		if (jd?.risk) riskLevels = jd.risk;
		if (jd?.grid) grid = jd.grid;

		statusMessage = '';
		statusType = '';
		// Use $effect.pre or defer to next tick so derived state updates first
		setTimeout(() => markClean(), 0);
	}

	async function cloneFromMatrix(sourceMatrixId: string) {
		if (!(await discardCurrentDraft())) return;
		try {
			// Create a new matrix by cloning the source's json_definition into editing_draft
			const res = await fetch(
				`/experimental/matrix-editor/${sourceMatrixId}?action=create-draft-from`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' }
				}
			);

			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || JSON.stringify(err));
			}

			const result = await res.json();
			// Load the newly created clone
			loadDraft({
				id: result.id,
				name: result.name,
				editing_draft: result.editing_draft
			});
			refreshDrafts();
		} catch (e: any) {
			setStatus(e.message, 'error');
		}
	}

	async function newMatrix() {
		if (!(await discardCurrentDraft())) return;
		// Set template values first
		matrixName = 'New matrix';
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
		// Clear matrixId so saveDraft creates a new one, then auto-save
		matrixId = null;
		statusMessage = '';
		statusType = '';
		// Wait a tick so derived jsonDefinition updates before saveDraft reads it
		await new Promise((r) => setTimeout(r, 0));
		await saveDraft();
	}

	async function refreshDrafts() {
		try {
			const res = await fetch('/experimental/matrix-editor');
			if (res.ok) {
				const data = await res.json();
				const allMatrices = data.results || data;
				existingDrafts = allMatrices.filter((m: any) => m.editing_draft !== null);
			}
		} catch {
			// ignore
		}
	}

	async function deleteDraft(matrix: any) {
		const isPublished = matrix.is_published;
		const msg = isPublished ? m.discardDraftConfirm() : m.deleteUnpublishedConfirm();
		if (!confirm(msg)) return;
		try {
			let res;
			if (isPublished) {
				// Discard draft only
				res = await fetch(`/experimental/matrix-editor/${matrix.id}?action=discard-draft`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' }
				});
			} else {
				// Delete the whole matrix
				res = await fetch(`/experimental/matrix-editor/${matrix.id}`, { method: 'DELETE' });
			}
			if (res.ok || res.status === 204) {
				const wasActive = matrixId === matrix.id;
				await refreshDrafts();
				if (wasActive) {
					// Switch to latest available draft, or clear editor
					if (existingDrafts.length > 0) {
						loadDraft(existingDrafts[0]);
					} else {
						matrixId = null;
						matrixName = '';
						matrixDescription = '';
						hasUnsavedChanges = false;
						setTimeout(() => markClean(), 0);
					}
				}
				setStatus(isPublished ? m.draftDiscarded() : m.matrixDeleted(), 'success');
			} else {
				const err = await res.json().catch(() => ({ error: m.deleteFailed() }));
				setStatus(err.error || m.deleteFailed(), 'error');
			}
		} catch (e: any) {
			setStatus(e.message || m.deleteFailed(), 'error');
		}
	}

	function onTranslationsChange(newProb: Level[], newImpact: Level[], newRisk: Level[]) {
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
				<button
					type="button"
					class="btn btn-sm bg-primary-500 text-white hover:bg-primary-600 transition-colors"
					onclick={newMatrix}
				>
					<i class="fa-solid fa-plus mr-1"></i>
					{m.newMatrix()}
				</button>
				<button
					type="button"
					class="btn btn-sm bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
					onclick={importFromFile}
				>
					<i class="fa-solid fa-file-import mr-1"></i>
					{m.importYaml()}
				</button>
				<button
					type="button"
					class="btn btn-sm bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
					onclick={exportAsYaml}
				>
					<i class="fa-solid fa-file-export mr-1"></i>
					{m.exportYaml()}
				</button>
			</div>

			<div class="flex items-center gap-2">
				{#if statusMessage}
					<span
						class="text-xs px-2 py-1 rounded-full transition-opacity {statusType === 'error'
							? 'bg-red-100 text-red-700'
							: 'bg-green-100 text-green-700'}"
					>
						<i
							class="fa-solid {statusType === 'error' ? 'fa-circle-xmark' : 'fa-circle-check'} mr-1"
						></i>
						{statusMessage}
					</span>
				{/if}
				{#if matrixId}
					<button
						type="button"
						class="btn btn-sm bg-gray-600 text-white hover:bg-gray-700 transition-colors disabled:opacity-50"
						onclick={saveDraft}
						disabled={saving}
					>
						<i class="fa-solid fa-floppy-disk mr-1"></i>
						{saving ? '...' : m.saveDraft()}
					</button>
					<button
						type="button"
						class="btn btn-sm bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-50"
						onclick={publishMatrix}
						disabled={publishing}
					>
						<i class="fa-solid fa-rocket mr-1"></i>
						{publishing ? '...' : m.publishMatrix()}
					</button>
				{/if}
			</div>
		</div>
	</div>

	<!-- All matrices: published + drafts -->
	<div class="card p-4">
		<h3 class="text-lg font-semibold mb-3">
			<i class="fa-solid fa-table-cells-large mr-1"></i>
			{m.riskMatrix()}s
		</h3>
		{#if matrices.length > 0 || existingDrafts.length > 0}
			<div class="table-container">
				<table class="table table-compact w-full">
					<thead>
						<tr>
							<th>{m.name()}</th>
							<th>{m.description()}</th>
							<th>{m.status()}</th>
							<th>{m.provider()}</th>
							<th class="w-48"></th>
						</tr>
					</thead>
					<tbody>
						<!-- Matrices with active drafts (editing in progress) -->
						{#each existingDrafts as draft}
							<tr class={matrixId === draft.id ? 'bg-primary-50 ring-1 ring-primary-200' : ''}>
								<td class="font-medium">{draft.name}</td>
								<td class="text-sm text-gray-500 truncate max-w-48">{draft.description || '—'}</td>
								<td>
									{#if draft.is_published}
										<span class="badge variant-filled-success text-xs">{m.published()}</span>
									{:else}
										<span class="badge variant-filled-warning text-xs">{m.new()}</span>
									{/if}
									<span class="badge variant-filled-primary text-xs ml-1">
										<i class="fa-solid fa-pen-to-square mr-0.5"></i>
										{m.editing()}
									</span>
								</td>
								<td class="text-sm text-gray-500">{draft.provider || '—'}</td>
								<td>
									<div class="flex gap-1">
										<button
											type="button"
											class="btn btn-sm variant-filled-primary"
											onclick={async () => {
												if (matrixId !== draft.id && !(await discardCurrentDraft())) return;
												loadDraft(draft);
											}}
											title={m.continueEditing()}
										>
											<i class="fa-solid fa-pen-to-square mr-1"></i>
											{m.continueEditing()}
										</button>
										<button
											type="button"
											class="btn btn-sm variant-ghost-error"
											onclick={() => deleteDraft(draft)}
											title={draft.is_published ? m.discardDraft() : m.delete()}
										>
											<i class="fa-solid fa-xmark"></i>
										</button>
									</div>
								</td>
							</tr>
						{/each}
						<!-- Published matrices without active drafts -->
						{#each matrices.filter((mx) => !existingDrafts.some((d) => d.id === mx.id)) as matrix}
							<tr class={matrixId === matrix.id ? 'bg-primary-50 ring-1 ring-primary-200' : ''}>
								<td class="font-medium">{matrix.name}</td>
								<td class="text-sm text-gray-500 truncate max-w-48">{matrix.description || '—'}</td>
								<td>
									<span class="badge variant-filled-success text-xs">{m.published()}</span>
									{#if matrix.urn}
										<span
											class="badge variant-ghost-surface text-xs ml-1"
											title={m.fromLibraryTooltip()}
										>
											<i class="fa-solid fa-book-open mr-0.5"></i>{m.fromLibrary()}
										</span>
									{/if}
									{#if matrix.editing_version > 1}
										<span class="text-xs text-gray-400 ml-1">v{matrix.editing_version}</span>
									{/if}
								</td>
								<td class="text-sm text-gray-500">{matrix.provider || '—'}</td>
								<td>
									<div class="flex gap-1">
										{#if !matrix.urn}
											<button
												type="button"
												class="btn btn-sm variant-ghost-primary"
												onclick={() => editPublishedMatrix(matrix.id)}
												title={m.editMatrixTooltip()}
											>
												<i class="fa-solid fa-pen-to-square mr-1"></i>
												{m.edit()}
											</button>
										{/if}
										<button
											type="button"
											class="btn btn-sm variant-ghost-surface"
											onclick={() => cloneFromMatrix(matrix.id)}
											title={m.cloneMatrixTooltip()}
										>
											<i class="fa-solid fa-copy mr-1"></i>
											{m.clone()}
										</button>
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<p class="text-sm text-gray-400 py-4 text-center">
				{@html m.noMatricesYet({
					link:
						'<a href="/libraries" class="text-primary-500 hover:underline">' +
						m.libraries() +
						'</a>'
				})}
			</p>
		{/if}
	</div>

	{#if matrixId}
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
						placeholder={m.matrixNamePlaceholder()}
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
						placeholder={m.descriptionPlaceholder()}
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
						placeholder={m.providerPlaceholder()}
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
							<option value={folder.id}>{folder.name}</option>
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
					{m.invalidMatrix()} — {m.needAtLeast2PerDimension()}
				</p>
			{/if}
		</div>
	{:else}
		<!-- No matrix selected placeholder -->
		<div class="card p-8">
			<div class="text-center space-y-4">
				<i class="fa-solid fa-table-cells-large text-4xl text-gray-300"></i>
				<h3 class="text-lg font-semibold text-gray-500">{m.noMatrixSelected()}</h3>
				<p class="text-sm text-gray-400 max-w-md mx-auto">
					{m.noMatrixSelectedHint()}
				</p>
			</div>
		</div>
	{/if}
</div>
