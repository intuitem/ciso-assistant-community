<script lang="ts">
	import * as m from '$paraglide/messages';
	import { getLocale, locales } from '$paraglide/runtime';
	import { defaultLangLabels } from '$lib/utils/locales';
	import {
		SCORE_SCALE_PRESETS,
		MAX_LABELLED_LEVELS,
		getPreset,
		hasLabelledLevels,
		presetLevelName,
		resolveLevelName,
		localizedLevelField,
		type ScoreLevel,
		type ScoreScaleValue,
		type DefaultScoreScale
	} from '$lib/utils/score-scales';

	interface Props {
		value: ScoreScaleValue | null;
		onChange: (value: ScoreScaleValue | null) => void;
		defaultScale?: DefaultScoreScale | null;
		declaredRange?: { min: number; max: number } | null;
		isScaleBound?: boolean;
		rangeLocked?: boolean;
		scoringEnabled?: boolean;
		helpText?: string;
	}

	let {
		value,
		onChange,
		defaultScale = null,
		declaredRange = null,
		isScaleBound = false,
		rangeLocked = false,
		scoringEnabled = true,
		helpText = m.scoreScaleHelpText()
	}: Props = $props();

	const initial = $state.snapshot(value);
	const initialLevels = structuredClone(initial?.scores_definition ?? []);
	const storedLocales = new Set(initialLevels.flatMap((l) => Object.keys(l.translations ?? {})));

	let selection = $state<string>(
		!initial
			? 'default'
			: getPreset(initial.score_scale_preset)
				? initial.score_scale_preset!
				: 'custom'
	);
	let min = $state(initial?.min_score ?? 0);
	let max = $state(initial?.max_score ?? 100);
	let levels = $state<ScoreLevel[]>(initialLevels);
	let languages = $state<string[]>([
		getLocale(),
		...[...storedLocales].filter((l) => l !== getLocale())
	]);

	let preset = $derived(getPreset(selection));
	let defaultPreset = $derived(getPreset(defaultScale?.score_scale_preset));
	let rangeError = $derived(selection === 'custom' && !(max > min));
	let scores = $derived(
		selection !== 'default' && hasLabelledLevels(min, max)
			? Array.from({ length: max - min + 1 }, (_, i) => min + i)
			: []
	);
	let unusedLocales = $derived(
		(locales as readonly string[]).filter((l) => !languages.includes(l))
	);

	function commit() {
		onChange(
			selection === 'default'
				? null
				: {
						score_scale_preset: preset?.id ?? null,
						min_score: min,
						max_score: max,
						scores_definition: $state.snapshot(levels)
					}
		);
	}

	function seedLevels(
		source: ScoreLevel[],
		sourcePreset: ReturnType<typeof getPreset>,
		lo: number,
		hi: number
	): ScoreLevel[] {
		if (!hasLabelledLevels(lo, hi)) return [];
		return Array.from({ length: hi - lo + 1 }, (_, i) => lo + i).map((score) => {
			const level = source.find((l) => l.score === score);
			const translations = structuredClone(level?.translations ?? {});
			for (const loc of languages) {
				const name = resolveLevelName(level, sourcePreset, score, loc);
				if (name) translations[loc] = { ...translations[loc], name };
			}
			return {
				score,
				name: level?.name ?? translations[languages[0]]?.name ?? '',
				translations
			};
		});
	}

	let pendingSelection = $state<string | null>(null);

	let hasOwnWording = $derived(
		levels.some((l) => l.name || Object.values(l.translations ?? {}).some((t) => t.name))
	);

	let defaultPreview = $derived.by(() => {
		if (!defaultScale) return [];
		const lang = getLocale();
		const own = defaultScale.scores_definition ?? [];
		const { min_score: lo, max_score: hi } = defaultScale;
		if (defaultPreset && hasLabelledLevels(lo, hi)) {
			return Array.from({ length: hi - lo + 1 }, (_, i) => lo + i).map((score) => ({
				score,
				name: localizedLevelField(
					{ ...own.find((l) => l.score === score), score, preset: defaultPreset.id },
					'name',
					lang
				)
			}));
		}
		return own
			.map((l) => ({ score: l.score, name: localizedLevelField(l, 'name', lang) }))
			.filter((l) => l.name);
	});

	function select(id: string) {
		if (id === selection) return;
		if (id !== 'custom' && hasOwnWording) {
			pendingSelection = id;
			return;
		}
		applySelection(id);
	}

	function confirmPending() {
		const id = pendingSelection;
		pendingSelection = null;
		if (id) applySelection(id);
	}

	function applySelection(id: string) {
		if (id === 'custom') {
			if (selection === 'default') {
				min = defaultScale?.min_score ?? 0;
				max = defaultScale?.max_score ?? 5;
				levels = seedLevels(defaultScale?.scores_definition ?? [], defaultPreset, min, max);
			} else {
				levels = seedLevels(levels, preset, min, max);
			}
			selection = 'custom';
		} else if (id === 'default') {
			selection = 'default';
			levels = [];
		} else {
			const next = getPreset(id);
			if (!next) return;
			selection = id;
			min = next.min;
			max = next.max;
			levels = [];
		}
		commit();
	}

	function setRange(nextMin: number, nextMax: number) {
		min = nextMin;
		max = nextMax;
		if (!(max > min)) return;
		levels = levels.filter((l) => l.score >= min && l.score <= max);
		commit();
	}

	function cellValue(score: number, loc: string) {
		const level = levels.find((l) => l.score === score);
		if (preset) return resolveLevelName(level, preset, score, loc);
		return level?.translations?.[loc]?.name ?? (loc === languages[0] ? (level?.name ?? '') : '');
	}

	function isOverridden(score: number, loc: string) {
		return Boolean(preset && levels.find((l) => l.score === score)?.translations?.[loc]?.name);
	}

	function setCell(score: number, loc: string, value: string) {
		const text = value.trim();
		const next = levels.filter((l) => l.score !== score);
		const level = levels.find((l) => l.score === score) ?? { score, translations: {} };
		const translations = { ...(level.translations ?? {}) };
		const matchesCatalog = preset && text === presetLevelName(preset, score, loc);
		if (!text || matchesCatalog) delete translations[loc];
		else translations[loc] = { ...translations[loc], name: text };

		if (preset) {
			if (Object.keys(translations).length) next.push({ score, translations });
		} else {
			const fallback =
				translations[languages[0]]?.name ?? Object.values(translations).find((t) => t.name)?.name;
			next.push({ score, name: fallback ?? '', translations });
		}
		levels = next.sort((a, b) => a.score - b.score);
		commit();
	}

	function addLanguage() {
		const next = unusedLocales[0];
		if (next) languages = [...languages, next];
	}

	function changeLanguage(idx: number, loc: string) {
		const old = languages[idx];
		languages = languages.map((l, i) => (i === idx ? loc : l));
		levels = levels.map((level) => {
			const translations = { ...(level.translations ?? {}) };
			if (translations[old]) {
				translations[loc] = translations[old];
				delete translations[old];
			}
			return { ...level, translations };
		});
		refreshFallbacks();
	}

	function removeLanguage(idx: number) {
		const loc = languages[idx];
		languages = languages.filter((_, i) => i !== idx);
		levels = levels
			.map((level) => {
				const translations = { ...(level.translations ?? {}) };
				delete translations[loc];
				return { ...level, translations };
			})
			.filter((l) => !preset || Object.keys(l.translations ?? {}).length);
		refreshFallbacks();
	}

	function refreshFallbacks() {
		if (!preset) {
			levels = levels.map((l) => ({
				...l,
				name: l.translations?.[languages[0]]?.name ?? l.name ?? ''
			}));
		}
		commit();
	}

	const chipClass = (active: boolean) =>
		`flex flex-col items-start rounded-md border px-3 py-1.5 text-left transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
			active
				? 'border-primary-500 bg-primary-50-950 shadow-sm'
				: 'border-surface-200-800 hover:border-surface-400-600'
		}`;
</script>

<div class="space-y-3" data-testid="score-scale-editor">
	<div>
		<h3 class="font-semibold text-sm">{m.scoreScale()}</h3>
		<p class="text-xs text-surface-600-400">{helpText}</p>
	</div>

	{#if !scoringEnabled}
		<p class="flex gap-2 text-xs text-surface-500 italic" data-testid="score-scale-scoring-hidden">
			<i class="fa-solid fa-eye-slash mt-0.5"></i>
			<span>{m.scoreScaleScoringHidden({ section: m.fieldVisibility() })}</span>
		</p>
	{:else}
		{#if isScaleBound}
			<div
				class="flex gap-2 rounded-md border border-warning-500 bg-warning-50-950 px-3 py-2 text-xs"
				role="note"
			>
				<i class="fa-solid fa-lock mt-0.5"></i>
				<span>{m.scoreScaleBoundToFramework()}</span>
			</div>
		{:else if rangeLocked}
			<div
				class="flex gap-2 rounded-md border border-surface-200-800 bg-surface-50-950 px-3 py-2 text-xs text-surface-700-300"
				role="note"
			>
				<i class="fa-solid fa-lock mt-0.5"></i>
				<span>{m.scoreScaleRangeLockedOnceScored()}</span>
			</div>
		{/if}

		<div class="flex flex-wrap gap-2" role="radiogroup" aria-label={m.scoreScale()}>
			<button
				type="button"
				role="radio"
				aria-checked={selection === 'default'}
				disabled={rangeLocked && selection !== 'default'}
				class={chipClass(selection === 'default')}
				data-testid="score-scale-default"
				onclick={() => select('default')}
			>
				{#if defaultScale}
					<span class="text-sm font-medium">{m.scoreScaleDefault()}</span>
					<span class="text-xs text-surface-600-400"
						><span class="font-mono">{defaultScale.min_score}–{defaultScale.max_score}</span>
						·
						{defaultScale.source === 'instance'
							? m.scoreScaleSourceInstance()
							: m.scoreScaleSourceFramework()}</span
					>
				{:else}
					<span class="text-sm font-medium">{m.scoreScaleNoDefault()}</span>
					<span class="text-xs text-surface-600-400">{m.scoreScaleNoDefaultHint()}</span>
				{/if}
			</button>
			{#each SCORE_SCALE_PRESETS as p}
				<button
					type="button"
					role="radio"
					aria-checked={selection === p.id}
					disabled={isScaleBound || (rangeLocked && selection !== p.id)}
					class={chipClass(selection === p.id)}
					data-testid={`score-scale-${p.id}`}
					onclick={() => select(p.id)}
				>
					<span class="text-sm font-medium font-mono">{p.min}–{p.max}</span>
					<span class="text-xs text-surface-600-400">{p.label()}</span>
				</button>
			{/each}
			<button
				type="button"
				role="radio"
				aria-checked={selection === 'custom'}
				disabled={isScaleBound || (rangeLocked && selection !== 'custom')}
				class={chipClass(selection === 'custom')}
				data-testid="score-scale-custom"
				onclick={() => select('custom')}
			>
				<span class="text-sm font-medium">{m.custom()}</span>
				<span class="text-xs text-surface-600-400">{m.scoreScaleCustomHint()}</span>
			</button>
		</div>

		{#if selection !== 'default' && declaredRange && !rangeLocked}
			<div
				class="flex gap-2 rounded-md border border-surface-200-800 bg-surface-50-950 px-3 py-2 text-xs text-surface-700-300"
				role="note"
			>
				<i class="fa-solid fa-circle-info mt-0.5"></i>
				<span
					>{m.scoreScaleOverridesFramework({
						min: declaredRange.min,
						max: declaredRange.max
					})}</span
				>
			</div>
		{/if}

		{#if pendingSelection}
			<div
				class="flex flex-wrap items-center gap-2 rounded-md border border-warning-500 bg-warning-50-950 px-3 py-2 text-xs"
				role="alert"
				data-testid="score-scale-discard-warning"
			>
				<i class="fa-solid fa-triangle-exclamation"></i>
				<span class="flex-1">{m.scoreScaleDiscardWording()}</span>
				<button
					type="button"
					class="btn btn-sm preset-filled-warning-500"
					onclick={confirmPending}
					data-testid="score-scale-discard-confirm">{m.scoreScaleDiscardConfirm()}</button
				>
				<button
					type="button"
					class="btn btn-sm preset-tonal-surface"
					onclick={() => (pendingSelection = null)}>{m.scoreScaleKeepEditing()}</button
				>
			</div>
		{/if}

		{#if selection === 'default' && defaultScale}
			<p class="text-xs text-surface-600-400" data-testid="score-scale-default-preview">
				{#if defaultPreview.length}
					<span class="font-medium">{m.scoreScaleLevels()}</span>
					{#each defaultPreview as level, idx}
						<span class="font-mono text-surface-500">{level.score}</span>
						{level.name}{idx < defaultPreview.length - 1 ? ' · ' : ''}
					{/each}
				{:else}
					<span class="italic">{m.scoreScaleNoLabels()}</span>
				{/if}
			</p>
		{/if}

		{#if selection === 'custom'}
			<div class="flex items-end gap-3">
				<label class="block">
					<span class="text-xs text-surface-600-400">{m.minScore()}</span>
					<input
						type="number"
						step="1"
						class="input w-24 text-sm"
						value={min}
						disabled={rangeLocked}
						onchange={(e) => setRange(parseInt(e.currentTarget.value) || 0, max)}
						data-testid="score-scale-custom-min"
					/>
				</label>
				<label class="block">
					<span class="text-xs text-surface-600-400">{m.maxScore()}</span>
					<input
						type="number"
						step="1"
						class="input w-24 text-sm"
						value={max}
						disabled={rangeLocked}
						onchange={(e) => setRange(min, parseInt(e.currentTarget.value) || 0)}
						data-testid="score-scale-custom-max"
					/>
				</label>
			</div>
			{#if rangeError}
				<p class="text-xs text-error-500">{m.scoreScaleRangeError()}</p>
			{/if}
		{/if}

		{#if selection !== 'default' && !rangeError}
			{#if scores.length > 0}
				<div class="max-w-4xl space-y-1.5">
					<div class="flex items-center justify-between">
						<span class="text-xs font-medium text-surface-600-400">{m.scoreScaleLevels()}</span>
						<button
							type="button"
							class="btn btn-sm preset-tonal-primary"
							onclick={addLanguage}
							disabled={unusedLocales.length === 0}
							data-testid="score-scale-add-language"
						>
							<i class="fa-solid fa-plus mr-1"></i>{m.addTranslation()}
						</button>
					</div>
					<div class="overflow-x-auto rounded-md border border-surface-200-800">
						<table class="w-full text-sm">
							<thead class="bg-surface-50-950">
								<tr>
									<th class="w-10 px-2 py-1 text-right font-mono text-xs text-surface-500">#</th>
									{#each languages as loc, idx (loc)}
										<th class="min-w-40 px-2 py-1 text-left font-normal">
											<div class="flex items-center gap-1">
												<select
													class="select w-auto py-0.5 text-xs"
													value={loc}
													onchange={(e) => changeLanguage(idx, e.currentTarget.value)}
													aria-label={m.language()}
												>
													{#each [loc, ...unusedLocales] as l}
														<option value={l}
															>{(defaultLangLabels as Record<string, string>)[l] ?? l}</option
														>
													{/each}
												</select>
												{#if idx === 0 && !preset}
													<i
														class="fa-solid fa-star text-[10px] text-primary-500"
														title={m.scoreScaleFallbackHelp()}
														aria-label={m.scoreScaleFallback()}
													></i>
												{/if}
												{#if languages.length > 1}
													<button
														type="button"
														class="ml-auto text-surface-500 hover:text-error-500"
														title={m.remove()}
														aria-label={m.remove()}
														onclick={() => removeLanguage(idx)}
													>
														<i class="fa-solid fa-xmark text-xs"></i>
													</button>
												{/if}
											</div>
										</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each scores as score (score)}
									<tr class="border-t border-surface-200-800">
										<td class="px-2 py-1 text-right font-mono text-xs text-surface-600-400"
											>{score}</td
										>
										{#each languages as loc (loc)}
											<td class="px-1 py-1">
												<div
													class="relative rounded-md {isOverridden(score, loc)
														? 'ring-2 ring-primary-400'
														: ''}"
													title={isOverridden(score, loc) ? m.scoreScaleYourWording() : undefined}
												>
													<input
														type="text"
														class="input w-full py-0.5 text-sm {isOverridden(score, loc)
															? 'pr-6'
															: ''}"
														value={cellValue(score, loc)}
														placeholder={!preset && loc !== languages[0]
															? cellValue(score, languages[0])
															: m.builderScaleNamePlaceholder()}
														onchange={(e) => setCell(score, loc, e.currentTarget.value)}
														data-testid={`score-scale-level-${score}-${loc}`}
													/>
													{#if isOverridden(score, loc)}
														<button
															type="button"
															class="absolute right-1.5 top-1/2 -translate-y-1/2 text-xs text-surface-500 hover:text-primary-500"
															title={m.scoreScaleResetWording()}
															aria-label={m.scoreScaleResetWording()}
															onclick={() => setCell(score, loc, '')}
														>
															<i class="fa-solid fa-rotate-left"></i>
														</button>
													{/if}
												</div>
											</td>
										{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
					<p class="text-xs text-surface-500">
						{preset ? m.scoreScalePresetWordingHelp() : m.scoreScaleFallbackHelp()}
					</p>
				</div>
			{:else}
				<p class="text-xs text-surface-500 italic">
					{m.scoreScaleContinuous({ count: MAX_LABELLED_LEVELS })}
				</p>
			{/if}
		{/if}
	{/if}
</div>
