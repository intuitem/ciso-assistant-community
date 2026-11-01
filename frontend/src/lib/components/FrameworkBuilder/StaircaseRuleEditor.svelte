<script lang="ts">
	import {
		getTranslation,
		staircaseCoverage,
		withTranslation,
		type BuilderNode,
		type OutcomeRule
	} from './builder-state';
	import { m } from '#paraglide/messages.js';

	// One staircase outcome (core/staircase.py): the implementation groups that are its
	// levels, lowest first, and whether each top-level section gets its own level.
	interface Props {
		rule: OutcomeRule;
		groups: { id: string; label: string }[];
		activeLanguage?: string | null;
		/** The framework's tree, to say what each level holds. */
		nodes?: BuilderNode[];
		onchange: (rule: OutcomeRule) => void;
	}

	let { rule, groups, activeLanguage = null, nodes = [], onchange }: Props = $props();

	const levels = $derived(((rule.levels ?? []) as unknown[]).map(String));

	function update(patch: Partial<OutcomeRule>) {
		const next: OutcomeRule = { ...rule, ...patch };
		for (const key of Object.keys(patch) as (keyof OutcomeRule)[]) {
			if (patch[key] === undefined || patch[key] === '') delete next[key];
		}
		onchange(next);
	}

	// shortcut: levels follow the order of the implementation groups, reorder those to change it.
	function toggleLevel(id: string) {
		const picked = levels.includes(id) ? levels.filter((l) => l !== id) : [...levels, id];
		update({
			levels: groups
				.map((g) => g.id)
				.filter((g) => picked.includes(g)) as unknown as OutcomeRule['levels']
		});
	}

	const coverage = $derived(staircaseCoverage(rule, nodes));
	const nameOf = (id: string) => groups.find((g) => g.id === id)?.label ?? id;
	const tagsOf = (index: number) =>
		(rule.cumulative ? levels.slice(0, index + 1) : [levels[index]]).map(nameOf).join(', ');

	const TEXTS = [
		['label', () => m.builderRatingLabel()],
		['annotation', () => m.description()],
		['unit_label', () => m.builderStaircaseUnitLabel()],
		['floor_label', () => m.builderStaircaseFloorLabel()]
	] as const;
</script>

<div class="space-y-3 text-sm" data-testid="staircase-rule-editor">
	{#if levels.length}
		<div
			class="rounded-lg border border-primary-200-800 bg-primary-50-950 p-3 space-y-1.5"
			data-testid="staircase-how"
		>
			<p class="text-xs font-semibold text-primary-800-200">{m.builderStaircaseHowTitle()}</p>
			<p>
				{rule.per === 'depth_1'
					? m.builderStaircaseHowPer({
							count: coverage.sections,
							unit: rule.unit_label || m.staircaseSections(),
							max: levels.length
						})
					: m.builderStaircaseHowWhole({ max: levels.length })}
			</p>
			<ol class="space-y-0.5">
				<li class="text-surface-700-300">
					<span class="font-semibold tabular-nums">0</span>
					{rule.floor_label ? `· ${rule.floor_label}` : ''}: {m.builderStaircaseHowZero()}
				</li>
				{#each levels as level, index (level)}
					<li class="text-surface-700-300">
						<span class="font-semibold tabular-nums">{index + 1}</span> · {nameOf(level)}:
						{index === 0
							? m.builderStaircaseHowFirst({ tags: tagsOf(index) })
							: m.builderStaircaseHowNext({ tags: tagsOf(index), previous: index })}
						{#if coverage.counts[index]}
							<span class="text-xs text-surface-500"
								>({m.builderStaircaseHowCount({ count: coverage.counts[index] })})</span
							>
						{:else}
							<span class="text-xs text-error-600 dark:text-error-400"
								>({m.builderStaircaseHowEmpty()})</span
							>
						{/if}
					</li>
				{/each}
			</ol>
			<p class="text-xs text-surface-600-400">{m.builderStaircaseHowPass()}</p>
			<p class="text-xs text-surface-600-400">{m.builderStaircaseHowTags()}</p>
		</div>
	{/if}

	{#each TEXTS as [key, title] (key)}
		{#if key !== 'unit_label' || rule.per === 'depth_1'}
			<div class="flex flex-wrap gap-3">
				<label class="flex flex-col gap-1">
					<span class="text-xs text-surface-600-400">{title()}</span>
					<input
						class="input {key === 'annotation' ? 'w-[28rem] max-w-full' : 'w-56'} text-sm py-1"
						value={rule[key] ?? ''}
						data-testid="staircase-{key}"
						onblur={(e) => update({ [key]: e.currentTarget.value.trim() } as Partial<OutcomeRule>)}
					/>
				</label>
				{#if activeLanguage}
					<label class="flex flex-col gap-1">
						<span class="text-xs text-blue-500">{activeLanguage.toUpperCase()}</span>
						<input
							class="input w-56 text-sm py-1 border-blue-100"
							value={getTranslation(rule.translations, activeLanguage, key)}
							onblur={(e) =>
								update({
									translations: withTranslation(
										rule.translations,
										activeLanguage!,
										key,
										e.currentTarget.value
									)
								})}
						/>
					</label>
				{/if}
			</div>
		{/if}
	{/each}

	<div role="group" aria-label={m.builderStaircaseLevels()}>
		<p class="text-xs font-semibold text-surface-600-400">{m.builderStaircaseLevels()}</p>
		<div class="flex flex-wrap gap-1 mt-1" data-testid="staircase-levels">
			{#each groups as group (group.id)}
				{@const index = levels.indexOf(group.id)}
				<button
					type="button"
					aria-pressed={index >= 0}
					class="text-xs px-2 py-0.5 rounded-full border {index >= 0
						? 'border-primary-500 bg-primary-100-900 text-primary-800-200'
						: 'border-surface-200-800 text-surface-600-400 hover:bg-surface-100-900'}"
					onclick={() => toggleLevel(group.id)}
				>
					{#if index >= 0}<span class="font-semibold tabular-nums">{index + 1}</span> ·{/if}
					{group.label}
				</button>
			{/each}
		</div>
		{#if !levels.length}
			<p class="text-xs text-error-600 dark:text-error-400 mt-1">
				{m.builderStaircaseNoLevels()}
			</p>
		{/if}
	</div>

	<label class="flex items-start gap-2">
		<input
			type="checkbox"
			class="checkbox mt-0.5"
			checked={rule.per === 'depth_1'}
			data-testid="staircase-per-section"
			onchange={(e) => update({ per: e.currentTarget.checked ? 'depth_1' : undefined })}
		/>
		<span>
			{m.builderStaircasePerSection()}
			<span class="block text-xs text-surface-500">{m.builderStaircasePerSectionHint()}</span>
		</span>
	</label>

	<label class="flex items-start gap-2">
		<input
			type="checkbox"
			class="checkbox mt-0.5"
			checked={!!rule.cumulative}
			data-testid="staircase-cumulative"
			onchange={(e) => update({ cumulative: e.currentTarget.checked || undefined })}
		/>
		<span>
			{m.builderStaircaseCumulative()}
			<span class="block text-xs text-surface-500">{m.builderStaircaseCumulativeHint()}</span>
		</span>
	</label>
</div>
