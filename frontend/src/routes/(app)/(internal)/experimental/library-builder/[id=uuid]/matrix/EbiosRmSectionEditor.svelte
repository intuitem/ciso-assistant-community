<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { isDark } from '$lib/utils/helpers';

	interface RatingLevel {
		name: string;
		description?: string;
		default?: boolean;
		hexcolor?: string;
		translations?: Record<string, { name?: string; description?: string }>;
	}

	interface RoToSection {
		motivation: RatingLevel[];
		resources: RatingLevel[];
		activity: RatingLevel[];
		pertinence: RatingLevel[];
		pertinence_grid: number[][];
	}

	interface Section {
		ro_to: RoToSection;
		success_probability: RatingLevel[];
		technical_difficulty: RatingLevel[];
		likelihood_grid: number[][];
	}

	interface Props {
		section: Section | null;
		likelihoodLevels: RatingLevel[];
		activeLang: string;
		baseLang: string;
		onchange: () => void;
	}

	let { section = $bindable(), likelihoodLevels, activeLang, baseLang, onchange }: Props = $props();

	// Same scale as the pertinence badges (irrelevant → highly relevant).
	const PERTINENCE_COLORS = ['#bbf7d0', '#fef08a', '#fed7aa', '#fecaca'];

	const size = $derived(likelihoodLevels.length);
	const translating = $derived(activeLang !== baseLang);
	const customized = $derived(!!section);

	let defaults = $state<Section | null>(null);
	let open = $state({ workshop2: false, workshop4: false });

	// Defaults are i18n keys; written into the library as plain text in its base
	// language, so they lose the `default` flag and are shown as written from then on.
	function localize(levels: RatingLevel[]): RatingLevel[] {
		return levels.map(({ default: _default, ...level }) => ({
			...level,
			name: safeTranslate(level.name, {}, { locale: baseLang })
		}));
	}

	async function fetchDefaults(levels: number): Promise<Section> {
		const res = await fetch(`/ebios-rm/rating-kit-defaults?size=${levels}`);
		const raw = await res.json();
		return {
			ro_to: {
				motivation: localize(raw.ro_to.motivation),
				resources: localize(raw.ro_to.resources),
				activity: localize(raw.ro_to.activity),
				pertinence: localize(raw.ro_to.pertinence),
				pertinence_grid: raw.ro_to.pertinence_grid
			},
			success_probability: localize(raw.success_probability),
			technical_difficulty: localize(raw.technical_difficulty),
			likelihood_grid: raw.likelihood_grid
		};
	}

	$effect(() => {
		const levels = size;
		if (levels < 1) return;
		fetchDefaults(levels).then((fetched) => {
			defaults = fetched;
			const current = section;
			if (!current || current.success_probability.length === levels) return;
			// Step scales follow the probability levels: keep edits, default the rest.
			const keep = (edited: RatingLevel[], fallback: RatingLevel[]) =>
				fallback.map((level, index) => edited[index] ?? level);
			section = {
				...current,
				success_probability: keep(current.success_probability, fetched.success_probability),
				technical_difficulty: keep(current.technical_difficulty, fetched.technical_difficulty),
				likelihood_grid: fetched.likelihood_grid.map((row, p) =>
					row.map((cell, d) => Math.min(current.likelihood_grid[p]?.[d] ?? cell, levels - 1))
				)
			};
			onchange();
		});
	});

	// What the studies use: the custom section, or the guide values.
	const shown = $derived(section ?? defaults);

	const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
	const workshop4Changed = $derived(
		!!section &&
			!!defaults &&
			!same(
				[section.success_probability, section.technical_difficulty, section.likelihood_grid],
				[defaults.success_probability, defaults.technical_difficulty, defaults.likelihood_grid]
			)
	);
	const workshop2Changed = $derived(
		!!section && !!defaults && !same(section.ro_to, defaults.ro_to)
	);

	function setCustomized(enabled: boolean) {
		section = enabled && defaults ? structuredClone($state.snapshot(defaults)) : null;
		if (enabled) open = { workshop2: true, workshop4: true };
		onchange();
	}

	function resetWorkshop4() {
		if (!section || !defaults) return;
		const fresh = structuredClone($state.snapshot(defaults));
		section = {
			...section,
			success_probability: fresh.success_probability,
			technical_difficulty: fresh.technical_difficulty,
			likelihood_grid: fresh.likelihood_grid
		};
		onchange();
	}

	function resetWorkshop2() {
		if (!section || !defaults) return;
		section = { ...section, ro_to: structuredClone($state.snapshot(defaults.ro_to)) };
		onchange();
	}

	function levelName(level: RatingLevel): string {
		return translating ? (level.translations?.[activeLang]?.name ?? '') : level.name;
	}

	const displayName = (level: RatingLevel | undefined) =>
		(level && translating && level.translations?.[activeLang]?.name) || level?.name || '';

	function setLevelName(level: RatingLevel, value: string) {
		if (translating) {
			level.translations = {
				...level.translations,
				[activeLang]: { ...level.translations?.[activeLang], name: value }
			};
		} else {
			level.name = value;
		}
		section = { ...section! };
		onchange();
	}

	function cycleCell(grid: number[][], row: number, column: number, values: number) {
		grid[row][column] = ((grid[row][column] ?? 0) + 1) % values;
		section = { ...section! };
		onchange();
	}

	const editable = $derived(customized && !translating);
	const likelihoodColors = $derived(likelihoodLevels.map((level) => level.hexcolor ?? ''));
</script>

{#snippet statusChip(changed: boolean)}
	<span
		class="badge text-xs {changed ? 'preset-filled-primary-500' : 'preset-tonal-surface'}"
		data-testid="ebios-rm-section-status"
		>{changed ? m.lbEbiosRmCustomized() : m.lbEbiosRmGuideValues()}</span
	>
{/snippet}

{#snippet levelLabel(level: RatingLevel, number: number)}
	<span class="flex items-center gap-1">
		<span class="text-[10px] font-bold text-surface-500">{number}</span>
		{#if customized}
			<input
				class="input input-sm min-w-0 flex-1 text-xs"
				type="text"
				value={levelName(level)}
				placeholder={translating ? level.name : ''}
				oninput={(e) => setLevelName(level, e.currentTarget.value)}
			/>
		{:else}
			<span class="text-xs">{displayName(level)}</span>
		{/if}
	</span>
{/snippet}

<!-- Rows are the vertical axis (highest level on top), columns the horizontal one; the
     headers are the axis labels themselves, so they are edited in place. -->
{#snippet ratingGrid(
	grid: number[][],
	rows: RatingLevel[],
	columns: RatingLevel[],
	values: RatingLevel[],
	colors: string[],
	rowAxis: string,
	columnAxis: string
)}
	<div class="overflow-x-auto">
		<table class="w-full table-fixed border-collapse text-xs">
			<thead>
				<tr>
					<th
						class="w-44 border border-surface-300-700 bg-surface-100-900 p-2 text-left font-medium text-surface-600-400"
					>
						<span class="block">↓ {rowAxis}</span>
						<span class="block">{columnAxis} →</span>
					</th>
					{#each columns as column, columnIndex}
						<th class="border border-surface-300-700 bg-surface-100-900 p-2 font-medium">
							{@render levelLabel(column, columnIndex + 1)}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each [...rows.keys()].reverse() as rowIndex}
					<tr>
						<th class="border border-surface-300-700 bg-surface-100-900 p-2 text-left font-medium">
							{@render levelLabel(rows[rowIndex], rowIndex + 1)}
						</th>
						{#each columns as _, columnIndex}
							{@const value = grid[rowIndex]?.[columnIndex] ?? 0}
							{@const color = colors[value] || '#e5e7eb'}
							<td
								class="h-10 border border-surface-300-700 px-1 text-center font-semibold {editable
									? 'cursor-pointer hover:opacity-80'
									: ''}"
								style="background-color: {color}; color: {isDark(color) ? 'white' : 'black'}"
								title={editable ? m.lbEbiosRmClickToCycle() : undefined}
								role={editable ? 'button' : undefined}
								tabindex={editable ? 0 : undefined}
								onclick={() => editable && cycleCell(grid, rowIndex, columnIndex, values.length)}
								onkeydown={(e) => {
									if (editable && (e.key === 'Enter' || e.key === ' ')) {
										e.preventDefault();
										cycleCell(grid, rowIndex, columnIndex, values.length);
									}
								}}>{displayName(values[value])}</td
							>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
	{#if editable}
		<p class="text-xs text-surface-500">
			<i class="fa-solid fa-circle-info mr-1"></i>{m.lbEbiosRmClickToCycle()}
		</p>
	{/if}
{/snippet}

{#snippet legend(title: string, levels: RatingLevel[], colors: string[], labelsEditable: boolean)}
	<div class="flex flex-wrap items-center gap-2 text-xs">
		<span class="font-medium text-surface-600-400">{title}</span>
		{#each levels as level, index}
			{@const color = colors[index] || '#e5e7eb'}
			<span
				class="flex items-center gap-1 rounded-base px-2 py-1"
				style="background-color: {color}; color: {isDark(color) ? 'white' : 'black'}"
			>
				<span class="font-bold">{index + 1}</span>
				{#if labelsEditable && customized}
					<input
						class="input input-sm w-36 text-xs"
						type="text"
						value={levelName(level)}
						placeholder={translating ? level.name : ''}
						oninput={(e) => setLevelName(level, e.currentTarget.value)}
					/>
				{:else}
					{displayName(level)}
				{/if}
			</span>
		{/each}
	</div>
{/snippet}

{#snippet sectionHeader(
	key: 'workshop4' | 'workshop2',
	title: string,
	help: string,
	changed: boolean,
	reset: () => void
)}
	<div class="flex flex-wrap items-center justify-between gap-2">
		<button
			type="button"
			class="flex items-center gap-2 text-left font-semibold"
			aria-expanded={open[key]}
			onclick={() => (open[key] = !open[key])}
		>
			<i class="fa-solid {open[key] ? 'fa-chevron-down' : 'fa-chevron-right'} w-3 text-xs"></i>
			{title}
			{@render statusChip(changed)}
		</button>
		{#if editable && changed}
			<button type="button" class="btn btn-sm preset-tonal" onclick={reset}>
				<i class="fa-solid fa-rotate-left mr-1"></i>{m.resetToDefaults()}
			</button>
		{/if}
	</div>
	{#if open[key]}
		<p class="text-xs text-surface-600-400">{help}</p>
	{/if}
{/snippet}

<div class="card space-y-4 p-4" data-testid="ebios-rm-section-editor">
	<div>
		<h3 class="text-lg font-semibold">
			<i class="fa-solid fa-chess-knight mr-1"></i>{m.lbEbiosRmSection()}
		</h3>
		<div
			class="mt-2 flex flex-wrap items-center justify-between gap-3 rounded-base bg-surface-100-900 px-3 py-2 text-sm"
		>
			<span class="text-surface-700-300">
				<i class="fa-solid fa-circle-info mr-1 text-primary-500"></i>
				{customized ? m.lbEbiosRmCustomizedIntro() : m.lbEbiosRmIntro()}
			</span>
			{#if !translating}
				<button
					type="button"
					class="btn btn-sm {customized ? 'preset-tonal' : 'preset-filled-primary-500'}"
					disabled={!defaults}
					onclick={() => setCustomized(!customized)}
					data-testid="ebios-rm-customize"
				>
					{#if customized}
						<i class="fa-solid fa-rotate-left mr-1"></i>{m.lbEbiosRmBackToGuide()}
					{:else}
						<i class="fa-solid fa-pen mr-1"></i>{m.lbEbiosRmCustomize()}
					{/if}
				</button>
			{/if}
		</div>
	</div>

	{#if shown}
		<div class="space-y-3 rounded-base border border-surface-200-800 p-3">
			{@render sectionHeader(
				'workshop2',
				m.lbEbiosRmW2Title(),
				m.lbEbiosRmW2Help(),
				workshop2Changed,
				resetWorkshop2
			)}
			{#if open.workshop2}
				{@render ratingGrid(
					shown.ro_to.pertinence_grid,
					shown.ro_to.motivation,
					shown.ro_to.resources,
					shown.ro_to.pertinence,
					PERTINENCE_COLORS,
					safeTranslate('motivation'),
					safeTranslate('resources')
				)}
				{@render legend(
					safeTranslate('pertinence'),
					shown.ro_to.pertinence,
					PERTINENCE_COLORS,
					true
				)}
				{@render legend(m.lbEbiosRmActivityLegend(), shown.ro_to.activity, [], true)}
			{/if}
		</div>

		<div class="space-y-3 rounded-base border border-surface-200-800 p-3">
			{@render sectionHeader(
				'workshop4',
				m.lbEbiosRmW4Title(),
				m.lbEbiosRmW4Help(),
				workshop4Changed,
				resetWorkshop4
			)}
			{#if open.workshop4}
				{@render ratingGrid(
					shown.likelihood_grid,
					shown.success_probability,
					shown.technical_difficulty,
					likelihoodLevels,
					likelihoodColors,
					m.successProbability(),
					m.technicalDifficulty()
				)}
				{@render legend(m.lbEbiosRmLikelihoodLegend(), likelihoodLevels, likelihoodColors, false)}
			{/if}
		</div>
	{/if}
</div>
