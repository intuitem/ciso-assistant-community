<script lang="ts">
	import LevelEditor from '$lib/components/RiskMatrixEditor/LevelEditor.svelte';
	import GridEditor from '$lib/components/RiskMatrixEditor/GridEditor.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { LOCALE_MAP, language } from '$lib/utils/locales';

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

	$pageTitle = m.lbMatrixPageTitle({ name: matrix.name || matrix.ref_id });

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

	// --- Translations (ported from the retired standalone matrix editor) ----
	// activeLang !== baseLang flips the meta inputs and the LevelEditors into
	// translation mode: edits land in translations[activeLang] instead of the
	// base fields.
	let activeLang = $state(baseLang);
	let addedLanguages: string[] = $state([]);
	let metaTranslations: Record<string, { name?: string; description?: string }> = $state({
		...(matrix.translations ?? {})
	});
	let isTranslatingMeta = $derived(activeLang !== baseLang);

	// Languages that already carry translations anywhere in the matrix.
	let usedLanguages = $derived.by(() => {
		const langs = new Set<string>();
		for (const levels of [probabilityLevels, impactLevels, riskLevels]) {
			for (const level of levels) {
				for (const lang of Object.keys(level.translations ?? {})) langs.add(lang);
			}
		}
		for (const lang of Object.keys(metaTranslations)) langs.add(lang);
		for (const lang of addedLanguages) langs.add(lang);
		langs.delete(baseLang);
		return langs;
	});

	let availableToAdd = $derived(
		Object.entries(LOCALE_MAP)
			.filter(([code]) => code !== baseLang && !usedLanguages.has(code))
			.map(([code, info]) => ({ code, name: language[info.name] ?? info.name }))
	);

	function localeLabel(code: string): string {
		return language[LOCALE_MAP[code as keyof typeof LOCALE_MAP]?.name] ?? code;
	}

	function addLanguage(code: string) {
		addedLanguages = [...addedLanguages, code];
		activeLang = code;
	}

	function removeLanguage(code: string) {
		if (code === baseLang) return;
		for (const levels of [probabilityLevels, impactLevels, riskLevels]) {
			for (const level of levels) {
				if (level.translations?.[code]) delete level.translations[code];
			}
		}
		probabilityLevels = [...probabilityLevels];
		impactLevels = [...impactLevels];
		riskLevels = [...riskLevels];
		if (metaTranslations[code]) {
			const { [code]: _removed, ...rest } = metaTranslations;
			metaTranslations = rest;
		}
		addedLanguages = addedLanguages.filter((lang) => lang !== code);
		if (activeLang === code) activeLang = baseLang;
		unsaved = true;
	}

	function setMetaTranslation(field: 'name' | 'description', value: string) {
		const current = metaTranslations[activeLang] ?? {};
		metaTranslations = { ...metaTranslations, [activeLang]: { ...current, [field]: value } };
		unsaved = true;
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
						// null clears the key on the stored object (upsert semantics)
						translations: Object.keys(metaTranslations).length > 0 ? metaTranslations : null,
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
			setStatus(m.lbMatrixSavedToDraft(), 'success');
		} catch (e: any) {
			setStatus(safeTranslate(e.message), 'error');
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
					<h2 class="text-xl font-semibold">
						{(isTranslatingMeta && metaTranslations[activeLang]?.name) || name || matrix.ref_id}
					</h2>
					{#if unsaved}
						<span class="badge variant-filled-warning text-xs">{m.lbMatrixUnsavedChanges()}</span>
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
					{m.lbMatrixSaveToDraft()}
				</button>
			</div>
		</div>
		<!-- Language bar: base locale chip, translation chips, add-language -->
		<div class="flex flex-wrap items-center gap-2 mt-4">
			<button
				type="button"
				class="px-3 py-1 rounded-full text-sm transition-colors {activeLang === baseLang
					? 'bg-primary-500 text-white'
					: 'bg-surface-100-900 text-surface-600-400 hover:bg-surface-200-800'}"
				onclick={() => (activeLang = baseLang)}
			>
				{localeLabel(baseLang)}
				<span class="text-xs opacity-70">({baseLang})</span>
			</button>
			{#each [...usedLanguages] as lang}
				<span
					class="inline-flex items-center rounded-full text-sm transition-colors {activeLang ===
					lang
						? 'bg-primary-500 text-white'
						: 'bg-surface-100-900 text-surface-600-400 hover:bg-surface-200-800'}"
				>
					<button type="button" class="px-3 py-1" onclick={() => (activeLang = lang)}>
						{localeLabel(lang)}
						<span class="text-xs opacity-70">({lang})</span>
					</button>
					<button
						type="button"
						class="pr-2 pl-0 py-1 opacity-50 hover:opacity-100 transition-opacity"
						onclick={(e) => {
							e.stopPropagation();
							if (confirm(m.removeLanguageConfirm({ lang: localeLabel(lang) }))) {
								removeLanguage(lang);
							}
						}}
						aria-label="{m.removeLanguageConfirm({ lang: localeLabel(lang) })} ({lang})"
					>
						<i class="fa-solid fa-xmark text-xs" aria-hidden="true"></i>
					</button>
				</span>
			{/each}
			{#if availableToAdd.length > 0}
				<select
					class="select select-sm w-36 text-xs"
					onchange={(e) => {
						const value = e.currentTarget.value;
						if (value) addLanguage(value);
						e.currentTarget.value = '';
					}}
				>
					<option value="">+ {m.addLanguage()}</option>
					{#each availableToAdd as lang}
						<option value={lang.code}>{lang.name}</option>
					{/each}
				</select>
			{/if}
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
			<label class="label text-sm">
				<span
					>{m.name()}{#if isTranslatingMeta}
						<span class="text-xs font-normal text-surface-500">({activeLang})</span>{/if}</span
				>
				{#if isTranslatingMeta}
					<input
						class="input"
						type="text"
						value={metaTranslations[activeLang]?.name ?? ''}
						oninput={(e) => setMetaTranslation('name', e.currentTarget.value)}
						placeholder={name || m.matrixNamePlaceholder()}
					/>
					{#if name}
						<span class="text-xs text-surface-500 block mt-0.5 truncate" title={name}>
							↳ {baseLang}: {name}
						</span>
					{/if}
				{:else}
					<input class="input" type="text" bind:value={name} oninput={() => (unsaved = true)} />
				{/if}
			</label>
			<label class="label text-sm">
				<span
					>{m.description()}{#if isTranslatingMeta}
						<span class="text-xs font-normal text-surface-500">({activeLang})</span>{/if}</span
				>
				{#if isTranslatingMeta}
					<input
						class="input"
						type="text"
						value={metaTranslations[activeLang]?.description ?? ''}
						oninput={(e) => setMetaTranslation('description', e.currentTarget.value)}
						placeholder={description || m.descriptionPlaceholder()}
					/>
					{#if description}
						<span class="text-xs text-surface-500 block mt-0.5 truncate" title={description}>
							↳ {baseLang}: {description}
						</span>
					{/if}
				{:else}
					<input
						class="input"
						type="text"
						bind:value={description}
						oninput={() => (unsaved = true)}
					/>
				{/if}
			</label>
		</div>
	</div>

	<div class="space-y-6">
		<div class="card p-4">
			<LevelEditor
				bind:levels={probabilityLevels}
				title={m.lbMatrixProbability()}
				onchange={onProbabilityChange}
				{activeLang}
				{baseLang}
			/>
		</div>
		<div class="card p-4">
			<LevelEditor
				bind:levels={impactLevels}
				title={m.lbMatrixImpact()}
				onchange={onImpactChange}
				{activeLang}
				{baseLang}
			/>
		</div>
		<div class="card p-4">
			<LevelEditor
				bind:levels={riskLevels}
				title={m.lbMatrixRisk()}
				onchange={onRiskChange}
				{activeLang}
				{baseLang}
			/>
		</div>
	</div>

	<div class="card p-4">
		<h3 class="text-lg font-semibold mb-3">
			<i class="fa-solid fa-table-cells mr-1"></i>{m.grid()}
		</h3>
		<GridEditor
			bind:grid
			{probabilityLevels}
			{impactLevels}
			{riskLevels}
			onchange={onGridChange}
			{activeLang}
			{baseLang}
		/>
	</div>
</div>
