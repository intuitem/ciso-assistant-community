<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { SECTION_ICON, SECTION_TITLE } from './section-style';
	import type { OutcomeRule } from './builder-state';

	type Entry = { target: string; config: Record<string, any> };
	type Threshold = { tier: string; min?: number };
	type MappingRow = { outcome: string; tier: string };
	type Tier = { id: string; key: string; name: string };

	interface Props {
		value: Entry[];
		rules: OutcomeRule[];
		/** Model of the form's subject question, e.g. "entity"; null without one. */
		subjectModel: string | null;
		onupdate: (value: Entry[]) => void;
		/** Adds a vendor question and makes it the subject. */
		onaddvendorsubject?: () => void;
		/** Whether any question gives points: without, the form score is always 0. */
		scored?: boolean;
	}

	let { value, rules, subjectModel, onupdate, onaddvendorsubject, scored = true }: Props = $props();

	const TIER_TARGET = 'entity.tier';
	// The select's value for the form score; a rule ref_id never starts with '@'.
	const FORM_SCORE = '@score';

	let tiers = $state<Tier[]>([]);
	$effect(() => {
		const controller = new AbortController();
		fetch('/tiers?is_visible=true', { signal: controller.signal })
			.then((res) => (res.ok ? res.json() : { results: [] }))
			.then((data) => {
				const rows = data?.results ?? data;
				tiers = Array.isArray(rows) ? (rows as Tier[]) : [];
			})
			.catch(() => {
				if (!controller.signal.aborted) tiers = [];
			});
		return () => controller.abort();
	});

	const entry = $derived((value ?? []).find((e) => e?.target === TIER_TARGET));
	const config = $derived(entry?.config ?? {});
	const thresholds = $derived<Threshold[]>(config.bands?.thresholds ?? []);
	const mapping = $derived<MappingRow[]>(config.mapping ?? []);
	const numericRules = $derived(rules.filter((r) => r.kind === 'number'));
	const yesNoRules = $derived(rules.filter((r) => r.kind !== 'number'));
	const knownKeys = $derived(new Set(tiers.map((t) => t.key)));
	const forVendors = $derived(subjectModel === 'entity');

	const ruleLabel = (rule: OutcomeRule) =>
		(rule as OutcomeRule & { label?: string }).label || rule.annotation || rule.ref_id;

	// The tier entry replaced, any other target's entry left as it is.
	function write(next: Record<string, any> | null) {
		const others = (value ?? []).filter((e) => e?.target !== TIER_TARGET);
		onupdate(next === null ? others : [...others, { target: TIER_TARGET, config: next }]);
	}

	const bandSource = $derived(
		config.bands?.source === 'score' ? FORM_SCORE : (config.bands?.outcome ?? '')
	);
	const bandRuleMissing = $derived(
		bandSource !== '' &&
			bandSource !== FORM_SCORE &&
			!numericRules.some((r) => r.ref_id === bandSource)
	);

	function setBandSource(source: string) {
		const { source: _, outcome: __, ...bands } = config.bands ?? {};
		write({
			...config,
			bands: source === FORM_SCORE ? { ...bands, source: 'score' } : { ...bands, outcome: source }
		});
	}

	function setBands(patch: Record<string, any> | null) {
		const { bands, ...rest } = config;
		write(patch === null ? rest : { ...rest, bands: { ...bands, ...patch } });
	}

	function setMapping(rows: MappingRow[] | null) {
		const { mapping: _, ...rest } = config;
		write(rows === null ? rest : { ...rest, mapping: rows });
	}

	// One band per tier, most critical first, the last catching the rest: the
	// shape almost every setup takes, left to the author to score.
	function defaultBands() {
		return { source: 'score', thresholds: tiers.map((tier) => ({ tier: tier.key })) };
	}

	function enable(on: boolean) {
		if (!on) return write(null);
		write({ bands: defaultBands() });
	}

	function updateThreshold(index: number, patch: Partial<Threshold>) {
		const rows = thresholds.map((row, i) => {
			if (i !== index) return row;
			const next = { ...row, ...patch };
			if (next.min === undefined || Number.isNaN(next.min)) delete next.min;
			return next;
		});
		setBands({ thresholds: rows });
	}
</script>

{#snippet tierSelect(current: string, onchange: (key: string) => void)}
	<select
		class="select text-sm w-40"
		value={current}
		onchange={(e) => onchange(e.currentTarget.value)}
		data-testid="on-accept-tier-select"
	>
		<option value="">--</option>
		{#each tiers as tier (tier.id)}
			<option value={tier.key}>{safeTranslate(tier.name)}</option>
		{/each}
		{#if current && !knownKeys.has(current)}
			<option value={current}>{current}</option>
		{/if}
	</select>
	{#if current && tiers.length && !knownKeys.has(current)}
		<span
			class="text-xs text-warning-700 dark:text-warning-400"
			data-testid="on-accept-unknown-tier"
		>
			<i class="fa-solid fa-triangle-exclamation mr-1"></i>{m.tierKeyNotOnScale({ key: current })}
		</span>
	{/if}
{/snippet}

<div class="space-y-2" data-testid="on-accept-editor">
	<div>
		<span class={SECTION_TITLE}
			><i class="{SECTION_ICON} fa-circle-check" aria-hidden="true"></i>{m.onAcceptSection()}</span
		>
		<p class="text-xs text-surface-500">{m.onAcceptSectionHelpText()}</p>
	</div>

	<label class="flex items-center gap-2 text-sm">
		<input
			type="checkbox"
			class="checkbox"
			checked={!!entry}
			disabled={!entry && !forVendors}
			onchange={(e) => enable(e.currentTarget.checked)}
			data-testid="on-accept-tier-toggle"
		/>
		{m.onAcceptSetEntityTier()}
	</label>
	{#if !forVendors}
		<div class="flex flex-wrap items-center gap-2 pl-6">
			<p class="text-xs text-surface-500">{m.onAcceptNeedsVendorSubject()}</p>
			{#if onaddvendorsubject}
				<button
					type="button"
					class="btn btn-sm preset-tonal-primary"
					onclick={onaddvendorsubject}
					data-testid="on-accept-add-vendor-subject"
				>
					<i class="fa-solid fa-plus mr-1"></i>{m.onAcceptAddVendorSubject()}
				</button>
			{/if}
		</div>
	{/if}

	{#if entry}
		<div class="flex flex-col gap-3 pl-6">
			<label class="flex items-center gap-2 text-sm">
				<input
					type="checkbox"
					class="checkbox"
					checked={!!config.bands}
					onchange={(e) => setBands(e.currentTarget.checked ? defaultBands() : null)}
				/>
				{m.tierBands()}
			</label>
			{#if config.bands}
				<div class="flex flex-col gap-2 pl-6">
					<label class="label">
						<span class="text-xs text-surface-600-400">{m.tierBandsValue()}</span>
						<select
							class="select text-sm"
							value={bandSource}
							onchange={(e) => setBandSource(e.currentTarget.value)}
							data-testid="on-accept-band-source"
						>
							{#if bandSource === ''}
								<option value="" disabled>--</option>
							{/if}
							<option value={FORM_SCORE}>{m.tierBandsFormScore()}</option>
							{#if numericRules.length}
								<optgroup label={m.tierBandsNumberRules()}>
									{#each numericRules as rule (rule.ref_id)}
										<option value={rule.ref_id}>{ruleLabel(rule)}</option>
									{/each}
								</optgroup>
							{/if}
							{#if bandRuleMissing}
								<option value={bandSource}>{bandSource}</option>
							{/if}
						</select>
						{#if bandRuleMissing}
							<span class="text-xs text-warning-700 dark:text-warning-400"
								>{m.tierBandsRuleMissing()}</span
							>
						{:else if bandSource === FORM_SCORE && !scored}
							<span
								class="text-xs text-warning-700 dark:text-warning-400"
								data-testid="on-accept-no-points">{m.tierBandsNoPoints()}</span
							>
						{/if}
					</label>
					{#each thresholds as row, index (index)}
						<div class="flex flex-wrap items-center gap-2 text-sm">
							{@render tierSelect(row.tier, (key) => updateThreshold(index, { tier: key }))}
							<span class="text-surface-500">{m.tierBandsFrom()}</span>
							<input
								type="number"
								step="any"
								class="input w-28 text-sm"
								value={row.min ?? ''}
								placeholder={index === thresholds.length - 1 ? m.tierBandsRest() : ''}
								onchange={(e) => {
									const v = e.currentTarget.value;
									updateThreshold(index, { min: v === '' ? undefined : Number(v) });
								}}
							/>
							<button
								type="button"
								class="btn-icon btn-icon-sm text-error-500"
								aria-label={m.delete()}
								onclick={() => setBands({ thresholds: thresholds.filter((_, i) => i !== index) })}
								><i class="fa-solid fa-trash"></i></button
							>
						</div>
					{/each}
					<button
						type="button"
						class="btn btn-sm preset-tonal w-fit"
						onclick={() => setBands({ thresholds: [...thresholds, { tier: '' }] })}
					>
						<i class="fa-solid fa-plus mr-1"></i>{m.tierBandsAdd()}
					</button>
					<p class="text-xs text-surface-500">{m.tierBandsHelpText()}</p>
				</div>
			{/if}

			<label class="flex items-center gap-2 text-sm">
				<input
					type="checkbox"
					class="checkbox"
					checked={Array.isArray(config.mapping)}
					onchange={(e) => setMapping(e.currentTarget.checked ? [] : null)}
				/>
				{m.tierMapping()}
			</label>
			{#if Array.isArray(config.mapping)}
				<div class="flex flex-col gap-2 pl-6">
					{#each mapping as row, index (index)}
						<div class="flex flex-wrap items-center gap-2 text-sm">
							<select
								class="select text-sm w-56"
								value={row.outcome}
								onchange={(e) => {
									const outcome = e.currentTarget.value;
									setMapping(mapping.map((r, i) => (i === index ? { ...r, outcome } : r)));
								}}
							>
								<option value="">--</option>
								{#each yesNoRules as rule (rule.ref_id)}
									<option value={rule.ref_id}>{ruleLabel(rule)}</option>
								{/each}
							</select>
							<span class="text-surface-500">→</span>
							{@render tierSelect(row.tier, (tier) =>
								setMapping(mapping.map((r, i) => (i === index ? { ...r, tier } : r)))
							)}
							<button
								type="button"
								class="btn-icon btn-icon-sm text-error-500"
								aria-label={m.delete()}
								onclick={() => setMapping(mapping.filter((_, i) => i !== index))}
								><i class="fa-solid fa-trash"></i></button
							>
						</div>
					{/each}
					<button
						type="button"
						class="btn btn-sm preset-tonal w-fit"
						onclick={() => setMapping([...mapping, { outcome: '', tier: '' }])}
					>
						<i class="fa-solid fa-plus mr-1"></i>{m.tierMappingAdd()}
					</button>
					<p class="text-xs text-surface-500">{m.tierMappingHelpText()}</p>
				</div>
			{/if}
			<p class="text-xs text-surface-500">{m.tierHighestWins()}</p>
		</div>
	{/if}
</div>
