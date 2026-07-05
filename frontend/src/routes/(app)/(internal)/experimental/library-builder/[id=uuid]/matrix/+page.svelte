<script lang="ts">
	import LevelEditor from '$lib/components/RiskMatrixEditor/LevelEditor.svelte';
	import GridEditor from '$lib/components/RiskMatrixEditor/GridEditor.svelte';
	import { pageTitle } from '$lib/utils/stores';

	interface Level {
		id: number;
		abbreviation: string;
		name: string;
		description: string;
		hexcolor: string;
		translations?: Record<string, { name?: string; description?: string }>;
	}

	let { data } = $props();
	const draft = data.draft;
	const matrix = data.matrix;

	$pageTitle = `Library Builder — ${matrix.name || matrix.ref_id}`;

	const baseLang = draft.locale ?? 'en';

	// The document's level objects carry no numeric id; the editor components
	// key on one. Assigned on load, stripped on save.
	function withIds(levels: any[]): Level[] {
		return (levels ?? []).map((level, index) => ({
			id: index,
			abbreviation: level.abbreviation ?? '',
			name: level.name ?? '',
			description: level.description ?? '',
			hexcolor: level.hexcolor ?? '#CCCCCC',
			translations: level.translations
		}));
	}

	function withoutIds(levels: Level[]): Record<string, unknown>[] {
		return levels.map(({ id, translations, ...level }) => ({
			...level,
			...(translations ? { translations } : {})
		}));
	}

	let name = $state(matrix.name ?? '');
	let description = $state(matrix.description ?? '');
	let probabilityLevels = $state(withIds(matrix.probability));
	let impactLevels = $state(withIds(matrix.impact));
	let riskLevels = $state(withIds(matrix.risk));
	let grid = $state<number[][]>((matrix.grid ?? []).map((row: number[]) => [...row]));
	let unsaved = $state(false);
	let saving = $state(false);

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

	// Grid synchronization on level changes — same semantics as the live
	// matrix editor (experimental/matrix-editor).
	function syncGridDimensions() {
		const rows = probabilityLevels.length;
		const cols = impactLevels.length;
		const maxRiskIdx = riskLevels.length - 1;
		const newGrid: number[][] = [];
		for (let r = 0; r < rows; r++) {
			const row: number[] = [];
			for (let c = 0; c < cols; c++) {
				const existing = grid[r]?.[c];
				row.push(existing !== undefined ? Math.min(existing, maxRiskIdx) : 0);
			}
			newGrid.push(row);
		}
		grid = newGrid;
	}

	function onProbabilityChange(newLevels: Level[], indexMap?: Map<number, number>) {
		if (indexMap) {
			const newGrid: number[][] = [];
			for (let oldIdx = 0; oldIdx < grid.length; oldIdx++) {
				const newIdx = indexMap.get(oldIdx);
				if (newIdx !== undefined && newIdx >= 0) {
					newGrid[newIdx] = grid[oldIdx];
				}
			}
			grid = newGrid;
		}
		probabilityLevels = newLevels;
		syncGridDimensions();
		unsaved = true;
	}

	function onImpactChange(newLevels: Level[], indexMap?: Map<number, number>) {
		if (indexMap) {
			grid = grid.map((row) => {
				const newRow: number[] = [];
				for (let oldIdx = 0; oldIdx < row.length; oldIdx++) {
					const newIdx = indexMap.get(oldIdx);
					if (newIdx !== undefined && newIdx >= 0) {
						newRow[newIdx] = row[oldIdx];
					}
				}
				return newRow;
			});
		}
		impactLevels = newLevels;
		syncGridDimensions();
		unsaved = true;
	}

	function onRiskChange(newLevels: Level[], indexMap?: Map<number, number>) {
		riskLevels = newLevels;
		if (indexMap) {
			grid = grid.map((row) =>
				row.map((val) => {
					const newIdx = indexMap.get(val);
					return newIdx !== undefined && newIdx >= 0 ? newIdx : 0;
				})
			);
		} else {
			const maxIdx = newLevels.length - 1;
			grid = grid.map((row) => row.map((val) => Math.min(val, maxIdx)));
		}
		unsaved = true;
	}

	function onGridChange(newGrid: number[][]) {
		grid = newGrid;
		unsaved = true;
	}

	async function save() {
		saving = true;
		try {
			const res = await fetch(`/experimental/library-builder/${draft.id}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					action: 'upsert-object',
					field: 'risk_matrices',
					urn: matrix.urn,
					object: {
						name: name || null,
						description: description || null,
						probability: withoutIds(probabilityLevels),
						impact: withoutIds(impactLevels),
						risk: withoutIds(riskLevels),
						grid
					}
				})
			});
			const result = await res.json();
			if (!res.ok) throw new Error(result.error || JSON.stringify(result));
			unsaved = false;
			setStatus('Matrix saved to the draft', 'success');
		} catch (e: any) {
			setStatus(e.message, 'error');
		} finally {
			saving = false;
		}
	}
</script>

<div class="space-y-6">
	<div class="card p-4">
		<div class="flex flex-wrap items-center justify-between gap-4">
			<div>
				<div class="flex items-center gap-2">
					<a
						href="/experimental/library-builder/{draft.id}"
						class="text-surface-500 hover:text-surface-700"
					>
						<i class="fa-solid fa-arrow-left"></i>
					</a>
					<h2 class="text-xl font-semibold">{name || matrix.ref_id}</h2>
					{#if unsaved}
						<span class="badge variant-filled-warning text-xs">Unsaved changes</span>
					{/if}
				</div>
				<p class="text-xs font-mono text-surface-500 mt-1">{matrix.urn}</p>
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
				<button
					type="button"
					class="btn btn-sm variant-filled-primary"
					onclick={save}
					disabled={saving}
				>
					{#if saving}<i class="fa-solid fa-spinner fa-spin mr-1"></i>{:else}<i
							class="fa-solid fa-floppy-disk mr-1"
						></i>{/if}
					Save to draft
				</button>
			</div>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
			<label class="label text-sm">
				<span>Name</span>
				<input class="input" type="text" bind:value={name} oninput={() => (unsaved = true)} />
			</label>
			<label class="label text-sm">
				<span>Description</span>
				<input
					class="input"
					type="text"
					bind:value={description}
					oninput={() => (unsaved = true)}
				/>
			</label>
		</div>
	</div>

	<div class="space-y-6">
		<div class="card p-4">
			<LevelEditor
				bind:levels={probabilityLevels}
				title="Probability"
				onchange={onProbabilityChange}
				activeLang={baseLang}
				{baseLang}
			/>
		</div>
		<div class="card p-4">
			<LevelEditor
				bind:levels={impactLevels}
				title="Impact"
				onchange={onImpactChange}
				activeLang={baseLang}
				{baseLang}
			/>
		</div>
		<div class="card p-4">
			<LevelEditor
				bind:levels={riskLevels}
				title="Risk"
				onchange={onRiskChange}
				activeLang={baseLang}
				{baseLang}
			/>
		</div>
	</div>

	<div class="card p-4">
		<h3 class="text-lg font-semibold mb-3">
			<i class="fa-solid fa-table-cells mr-1"></i>Grid
		</h3>
		<GridEditor bind:grid {probabilityLevels} {impactLevels} {riskLevels} onchange={onGridChange} />
	</div>
</div>
