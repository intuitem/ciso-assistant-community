<script lang="ts">
	import { getTranslation, withTranslation, type OutcomeRule } from './builder-state';
	import { m } from '#paraglide/messages.js';

	// One staircase outcome (core/staircase.py): the implementation groups that are its
	// levels, lowest first, and whether each top-level section gets its own level.
	interface Props {
		rule: OutcomeRule;
		groups: { id: string; label: string }[];
		activeLanguage?: string | null;
		onchange: (rule: OutcomeRule) => void;
	}

	let { rule, groups, activeLanguage = null, onchange }: Props = $props();

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
			levels: groups.map((g) => g.id).filter((g) => picked.includes(g)) as OutcomeRule['levels']
		});
	}

	const TEXTS = [
		['label', () => m.builderRatingLabel()],
		['unit_label', () => m.builderStaircaseUnitLabel()],
		['floor_label', () => m.builderStaircaseFloorLabel()]
	] as const;
</script>

<div class="space-y-3 text-sm" data-testid="staircase-rule-editor">
	{#each TEXTS as [key, title] (key)}
		{#if key !== 'unit_label' || rule.per === 'depth_1'}
			<div class="flex flex-wrap gap-3">
				<label class="flex flex-col gap-1">
					<span class="text-xs text-surface-600-400">{title()}</span>
					<input
						class="input w-56 text-sm py-1"
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
		<p class="text-xs text-surface-500 mt-1">{m.builderStaircaseLevelsHint()}</p>
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
