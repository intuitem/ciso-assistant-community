<script lang="ts">
	import { getTranslation, withTranslation, type OutcomeRule } from './builder-state';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';

	interface Props {
		rule: OutcomeRule;
		activeLanguage?: string | null;
		onchange: (rule: OutcomeRule) => void;
	}

	let { rule, activeLanguage = null, onchange }: Props = $props();

	function update(patch: Partial<OutcomeRule>) {
		const next: OutcomeRule = { ...rule, ...patch };
		for (const key of Object.keys(patch) as (keyof OutcomeRule)[]) {
			if (patch[key] === undefined || patch[key] === '') delete next[key];
		}
		onchange(next);
	}

	const RESULTS = ['compliant', 'partially_compliant', 'non_compliant'] as const;
	const WEIGHTS = { compliant: 1, partially_compliant: 0.5, non_compliant: 0 };
	const name = (r: (typeof RESULTS)[number]) => rule.result_labels?.[r] || safeTranslate(r);

	function setResultLabel(r: (typeof RESULTS)[number], value: string) {
		const labels = { ...(rule.result_labels ?? {}) };
		if (value.trim()) labels[r] = value.trim();
		else delete labels[r];
		update({ result_labels: Object.keys(labels).length ? labels : undefined });
	}

	const TEXTS = [
		['label', () => m.builderRatingLabel()],
		['annotation', () => m.description()],
		['section_label', () => m.builderStaircaseSectionLabel()]
	] as const;
</script>

<div class="space-y-3 text-sm" data-testid="weakest-link-rule-editor">
	<div
		class="rounded-lg border border-primary-200-800 bg-primary-50-950 p-3 space-y-1.5"
		data-testid="weakest-link-how"
	>
		<p class="text-xs font-semibold text-primary-800-200">{m.builderWeakestLinkHowTitle()}</p>
		<p>{m.builderWeakestLinkHowRate({ depth: rule.rated_depth ?? 1 })}</p>
		<ul class="list-disc ml-5 space-y-0.5 text-surface-700-300">
			<li>{m.builderWeakestLinkHowNotAssessed()}</li>
			<li>
				{m.builderWeakestLinkHowWorst({
					worst: name('non_compliant'),
					middle: name('partially_compliant'),
					best: name('compliant')
				})}
			</li>
		</ul>
		<p>
			{rule.per === 'depth_1'
				? m.builderWeakestLinkHowPer({ unit: rule.section_label || m.staircaseSections() })
				: m.builderWeakestLinkHowWhole()}
			{RESULTS.map((r) => `${name(r)} ${rule.result_weights?.[r] ?? WEIGHTS[r]}`).join(', ')}.
		</p>
		<p class="text-xs text-surface-600-400">{m.builderWeakestLinkHowUnassessed()}</p>
	</div>

	{#each TEXTS as [key, title] (key)}
		{#if key !== 'section_label' || rule.per === 'depth_1'}
			<div class="flex flex-wrap gap-3">
				<label class="flex flex-col gap-1">
					<span class="text-xs text-surface-600-400">{title()}</span>
					<input
						class="input {key === 'annotation' ? 'w-[28rem] max-w-full' : 'w-56'} text-sm py-1"
						value={rule[key] ?? ''}
						data-testid="weakest-link-{key}"
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

	<label class="flex flex-col gap-1">
		<span class="text-xs text-surface-600-400">{m.builderWeakestLinkDepth()}</span>
		<input
			type="number"
			min={rule.per === 'depth_1' ? 2 : 1}
			step="1"
			class="input w-24 text-sm py-1"
			value={rule.rated_depth ?? 1}
			data-testid="weakest-link-depth"
			onchange={(e) => {
				const depth = Math.max(rule.per === 'depth_1' ? 2 : 1, Math.round(+e.currentTarget.value));
				update({ rated_depth: depth });
			}}
		/>
		<span class="text-xs text-surface-500">{m.builderWeakestLinkDepthHint()}</span>
	</label>

	<label class="flex items-start gap-2">
		<input
			type="checkbox"
			class="checkbox mt-0.5"
			checked={rule.per === 'depth_1'}
			data-testid="weakest-link-per-section"
			onchange={(e) =>
				update(
					e.currentTarget.checked
						? { per: 'depth_1', rated_depth: Math.max(2, rule.rated_depth ?? 2) }
						: { per: undefined }
				)}
		/>
		<span>
			{m.builderWeakestLinkPerSection()}
			<span class="block text-xs text-surface-500">{m.builderWeakestLinkPerSectionHint()}</span>
		</span>
	</label>

	<div role="group" aria-label={m.builderWeakestLinkResultLabels()}>
		<p class="text-xs font-semibold text-surface-600-400">{m.builderWeakestLinkResultLabels()}</p>
		<div class="flex flex-wrap gap-3 mt-1">
			{#each RESULTS as r (r)}
				<label class="flex flex-col gap-1">
					<span class="text-xs text-surface-500">{safeTranslate(r)}</span>
					<input
						class="input w-44 text-sm py-1"
						value={rule.result_labels?.[r] ?? ''}
						data-testid="weakest-link-label-{r}"
						onblur={(e) => setResultLabel(r, e.currentTarget.value)}
					/>
				</label>
				{#if activeLanguage}
					<label class="flex flex-col gap-1">
						<span class="text-xs text-blue-500">{activeLanguage.toUpperCase()}</span>
						<input
							class="input w-44 text-sm py-1 border-blue-100"
							value={getTranslation(rule.translations, activeLanguage, `result_label_${r}`)}
							onblur={(e) =>
								update({
									translations: withTranslation(
										rule.translations,
										activeLanguage!,
										`result_label_${r}`,
										e.currentTarget.value
									)
								})}
						/>
					</label>
				{/if}
			{/each}
		</div>
	</div>
</div>
