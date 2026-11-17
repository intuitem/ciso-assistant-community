<script lang="ts">
	import {
		fitGrid,
		getTranslation,
		gridToRules,
		rulesToGrid,
		ruleIdFromLabel,
		withTranslation,
		type OutcomeRule,
		type Scale
	} from './builder-state';
	import ConfirmAction from './ConfirmAction.svelte';
	import { m } from '#paraglide/messages.js';

	// One rating outcome: the scales it measures (dimensions), its named levels, how a
	// point is classified (a grid painted by clicking, for two dimensions; or rules,
	// the first CEL `when` that holds), and the pages it reads.
	interface Props {
		rule: OutcomeRule;
		scales: Scale[];
		pages: { id: string; label: string }[];
		measured?: string[];
		onaddscale?: () => Scale;
		activeLanguage?: string | null;
		onchange: (rule: OutcomeRule) => void;
	}

	let {
		rule,
		scales,
		pages,
		measured = [],
		onaddscale,
		activeLanguage = null,
		onchange
	}: Props = $props();

	const scaleOf = (ref?: string) => scales.find((s) => s.ref_id === ref);
	const dimensions = $derived(rule.dimensions ?? []);
	const levels = $derived(rule.levels ?? []);
	const usesGrid = $derived(rule.rules === undefined);
	const rows = $derived(scaleOf(dimensions[0]));
	const cells = $derived(scaleOf(dimensions[1]));
	const grid = $derived(fitGrid(rule, scales));
	const colorOf = (ref: string) => levels.find((l) => l.ref_id === ref)?.color ?? 'transparent';
	const labelOf = (ref: string) => levels.find((l) => l.ref_id === ref)?.label ?? ref;

	// A grid only exists for two dimensions; with any other number, rules classify.
	function update(patch: Partial<OutcomeRule>, added: Scale[] = []) {
		const next: OutcomeRule = { ...rule, ...patch };
		if (next.rules === undefined && (next.dimensions ?? []).length !== 2) {
			// What the grid said becomes rules, so a third dimension loses nothing.
			next.rules = asRules(rule);
		}
		if (next.rules === undefined) {
			next.grid = fitGrid(next, [...scales, ...added]);
		} else {
			delete next.grid;
		}
		onchange(next);
	}

	const asRules = (from: OutcomeRule) => {
		const rules = gridToRules(from, scales);
		return rules.length ? rules : [{ level: levels.at(-1)?.ref_id ?? '', when: 'true' }];
	};

	// Grid and rules convert into each other, so switching back and forth keeps the
	// painting (rules written by hand cannot be drawn: the grid then starts afresh).
	function useGrid(on: boolean) {
		if (on) {
			update({ rules: undefined, grid: rulesToGrid(rule, scales) ?? undefined });
		} else {
			update({ rules: asRules(rule) });
		}
	}

	function addDimension() {
		const unused = scales.find((s) => !dimensions.includes(s.ref_id));
		const added = unused || !onaddscale ? [] : [onaddscale()];
		const ref = unused?.ref_id ?? added[0]?.ref_id;
		if (ref) update({ dimensions: [...dimensions, ref] }, added);
	}

	function setDimension(index: number, ref: string) {
		const next = [...dimensions];
		next[index] = ref;
		update({ dimensions: next });
	}

	function paint(ri: number, ci: number) {
		if (!levels.length) return;
		const current = levels.findIndex((l) => l.ref_id === grid[ri][ci]);
		const next = grid.map((row) => [...row]);
		next[ri][ci] = levels[(current + 1) % levels.length].ref_id;
		update({ grid: next });
	}

	function setLevel(index: number, patch: Record<string, unknown>) {
		const next = levels.map((l) => ({ ...l }));
		const level = next[index];
		if (!level.ref_id && typeof patch.label === 'string' && patch.label.trim()) {
			level.ref_id = ruleIdFromLabel(
				patch.label,
				next.filter((_, i) => i !== index).map((l) => l.ref_id)
			);
		}
		Object.assign(level, patch);
		update({ levels: next });
	}

	function setRule(index: number, patch: Partial<{ level: string; when: string }>) {
		const next = (rule.rules ?? []).map((r) => ({ ...r }));
		Object.assign(next[index], patch);
		update({ rules: next });
	}

	function moveRule(index: number, to: number) {
		const next = [...(rule.rules ?? [])];
		const [moved] = next.splice(index, 1);
		next.splice(to, 0, moved);
		update({ rules: next });
	}

	function togglePage(id: string) {
		const current = rule.pages ?? [];
		const next = current.includes(id) ? current.filter((p) => p !== id) : [...current, id];
		update({ pages: next.length ? next : undefined });
	}
</script>

<div class="space-y-3 text-sm" data-testid="rating-rule-editor">
	<div class="flex flex-wrap gap-3">
		<label class="flex flex-col gap-1">
			<span class="text-xs text-surface-600-400">{m.builderRatingLabel()}</span>
			<input
				class="input w-56 text-sm py-1"
				value={rule.label ?? ''}
				onblur={(e) => update({ label: e.currentTarget.value })}
			/>
		</label>
		{#if activeLanguage}
			<label class="flex flex-col gap-1">
				<span class="text-xs text-blue-500">{activeLanguage.toUpperCase()}</span>
				<input
					class="input w-56 text-sm py-1 border-blue-100"
					value={getTranslation(rule.translations, activeLanguage, 'label')}
					onblur={(e) =>
						update({
							translations: withTranslation(
								rule.translations,
								activeLanguage!,
								'label',
								e.currentTarget.value
							)
						})}
				/>
			</label>
		{/if}
	</div>

	<div>
		<p class="text-xs font-semibold text-surface-600-400">{m.builderRatingDimensions()}</p>
		<ol class="mt-1 flex flex-wrap items-center gap-2">
			{#each dimensions as dimension, index (index)}
				<li class="flex items-center gap-1">
					{#if index > 0}<span class="text-surface-500">×</span>{/if}
					<select
						class="select w-40 text-sm py-1"
						value={dimension}
						onchange={(e) => setDimension(index, e.currentTarget.value)}
					>
						{#each scales as s, i (i)}<option value={s.ref_id}>{s.label || s.ref_id}</option>{/each}
					</select>
					{#if dimensions.length > 1}
						<ConfirmAction
							onconfirm={() => update({ dimensions: dimensions.filter((_, i) => i !== index) })}
						/>
					{/if}
					{#if dimension && !measured.includes(dimension)}
						<span class="text-xs text-warning-700 dark:text-warning-300"
							>{m.builderRatingDimensionUnmeasured()}</span
						>
					{/if}
				</li>
			{/each}
			<li>
				<button type="button" class="btn btn-sm preset-tonal" onclick={addDimension}>
					<i class="fa-solid fa-plus mr-1"></i>{m.builderRatingAddDimension()}
				</button>
			</li>
		</ol>
	</div>

	<div>
		<p class="text-xs font-semibold text-surface-600-400">{m.builderRatingLevels()}</p>
		<ol class="mt-1 space-y-1">
			{#each levels as level, index (index)}
				<li class="flex flex-wrap items-center gap-2">
					<input
						type="color"
						class="h-7 w-8 cursor-pointer rounded border border-surface-200-800"
						value={level.color || '#ffffff'}
						onchange={(e) => setLevel(index, { color: e.currentTarget.value })}
					/>
					<input
						class="input w-44 text-sm py-1"
						value={level.label}
						placeholder={m.builderLevelLabel()}
						onblur={(e) => setLevel(index, { label: e.currentTarget.value })}
					/>
					{#if activeLanguage}
						<input
							class="input w-44 text-sm py-1 border-blue-100"
							value={getTranslation(level.translations, activeLanguage, 'label')}
							placeholder="{m.builderLevelLabel()} ({activeLanguage.toUpperCase()})"
							onblur={(e) =>
								setLevel(index, {
									translations: withTranslation(
										level.translations,
										activeLanguage!,
										'label',
										e.currentTarget.value
									)
								})}
						/>
					{/if}
					{#if level.ref_id}<code class="text-xs text-surface-500">{level.ref_id}</code>{/if}
					{#if levels.length > 1}
						<ConfirmAction
							onconfirm={() => update({ levels: levels.filter((_, i) => i !== index) })}
						/>
					{/if}
				</li>
			{/each}
		</ol>
		<button
			type="button"
			class="btn btn-sm preset-tonal mt-1"
			onclick={() => update({ levels: [...levels, { ref_id: '', label: '' }] })}
		>
			<i class="fa-solid fa-plus mr-1"></i>{m.builderAddLevel()}
		</button>
	</div>

	<div class="flex items-center gap-3 text-xs">
		<span class="font-semibold text-surface-600-400">{m.builderRatingClassify()}</span>
		<label class="flex items-center gap-1">
			<input
				type="radio"
				class="radio"
				checked={usesGrid}
				disabled={dimensions.length !== 2}
				onchange={() => useGrid(true)}
			/>{m.builderRatingGrid()}
		</label>
		<label class="flex items-center gap-1">
			<input
				type="radio"
				class="radio"
				checked={!usesGrid}
				onchange={() => useGrid(false)}
			/>{m.builderRatingRules()}
		</label>
		{#if dimensions.length !== 2}
			<span class="text-surface-500">{m.builderRatingGridNeedsTwo()}</span>
		{/if}
	</div>

	{#if usesGrid && rows && cells}
		<div>
			<p class="text-xs text-surface-500">{m.builderRatingGridHelp()}</p>
			<div class="mt-1 flex max-w-full gap-2 overflow-x-auto">
				<div
					class="flex items-center justify-center text-xs font-semibold text-surface-600-400 [writing-mode:vertical-rl] rotate-180"
				>
					{rows.label || rows.ref_id}
				</div>
				<div
					class="grid gap-1"
					style="grid-template-columns: auto repeat({cells.levels.length}, minmax(4rem, 1fr));"
				>
					{#each rows.levels.map((_, i) => rows.levels.length - 1 - i) as ri (ri)}
						<div class="flex items-center justify-end pr-1 text-xs text-surface-600-400">
							{rows.levels[ri].label}
						</div>
						{#each cells.levels as _, ci (ci)}
							<button
								type="button"
								class="h-10 rounded-base border border-surface-200-800 text-[11px] font-medium {colorOf(
									grid[ri][ci]
								) === 'transparent'
									? ''
									: 'text-surface-950'}"
								style="background-color: {colorOf(grid[ri][ci])};"
								onclick={() => paint(ri, ci)}
								data-testid="rating-cell">{labelOf(grid[ri][ci])}</button
							>
						{/each}
					{/each}
					<div></div>
					{#each cells.levels as level, i (i)}
						<div class="text-center text-xs text-surface-600-400">{level.label}</div>
					{/each}
				</div>
			</div>
			<p class="mt-1 text-center text-xs font-semibold text-surface-600-400">
				{cells.label || cells.ref_id}
			</p>
		</div>
	{:else if !usesGrid}
		<div>
			<p class="text-xs text-surface-500">
				{m.builderRatingRulesHelp({ dims: dimensions.map((d) => `dims.${d}.value`).join(' × ') })}
			</p>
			<ol class="mt-1 space-y-1">
				{#each rule.rules ?? [] as entry, index (index)}
					<li class="flex flex-wrap items-center gap-2">
						<select
							class="select w-40 text-sm py-1"
							value={entry.level}
							onchange={(e) => setRule(index, { level: e.currentTarget.value })}
						>
							{#each levels as level, i (i)}<option value={level.ref_id}
									>{level.label || level.ref_id}</option
								>{/each}
						</select>
						<span class="text-xs text-surface-500">{m.builderRatingWhen()}</span>
						<input
							class="input flex-1 min-w-64 font-mono text-xs py-1"
							value={entry.when}
							onblur={(e) => setRule(index, { when: e.currentTarget.value })}
							data-testid="rating-rule-when"
						/>
						<button
							type="button"
							class="text-xs text-surface-500 disabled:opacity-30"
							disabled={index === 0}
							aria-label="↑"
							onclick={() => moveRule(index, index - 1)}
							><i class="fa-solid fa-arrow-up"></i></button
						>
						<ConfirmAction
							onconfirm={() => update({ rules: (rule.rules ?? []).filter((_, i) => i !== index) })}
						/>
					</li>
				{/each}
			</ol>
			<button
				type="button"
				class="btn btn-sm preset-tonal mt-1"
				onclick={() =>
					update({
						rules: [...(rule.rules ?? []), { level: levels[0]?.ref_id ?? '', when: 'true' }]
					})}
			>
				<i class="fa-solid fa-plus mr-1"></i>{m.builderRatingAddRule()}
			</button>
		</div>
	{/if}

	<div>
		<p class="text-xs font-semibold text-surface-600-400">{m.builderRatingPages()}</p>
		<p class="text-xs text-surface-500">{m.builderRatingPagesHelp()}</p>
		<div class="mt-1 flex flex-wrap gap-2">
			{#each pages as page (page.id)}
				<label class="flex items-center gap-1 text-xs">
					<input
						type="checkbox"
						class="checkbox"
						checked={(rule.pages ?? []).includes(page.id)}
						onchange={() => togglePage(page.id)}
					/>{page.label}
				</label>
			{/each}
		</div>
	</div>
</div>
