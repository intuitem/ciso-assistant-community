<script lang="ts">
	import { formFieldProxy, type SuperValidated } from 'sveltekit-superforms';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
	}

	let { form }: Props = $props();

	const { value: onAccept, errors } = formFieldProxy(form, 'on_accept');
	const { value: quickFormId } = formFieldProxy(form, 'quick_form');

	const TIER_TARGET = 'entity.tier';

	type Threshold = { tier: string; min: number | null };
	type MappingRow = { outcome: string; tier: string };
	type Rule = { ref_id: string; kind?: string; label?: string; annotation?: string };
	type Tier = { id: string; name: string; rank: number; hexcolor: string };

	function tierEntry(): { target: string; config: Record<string, any> } | undefined {
		return (($onAccept as any[]) ?? []).find((e) => e?.target === TIER_TARGET);
	}

	const initial = tierEntry()?.config ?? {};
	let enabled = $state(!!tierEntry());
	let useBands = $state(!!initial.bands);
	let bandOutcome = $state<string>(initial.bands?.outcome ?? '');
	let thresholds = $state<Threshold[]>(
		(initial.bands?.thresholds ?? []).map((t: any) => ({
			tier: String(t.tier ?? ''),
			min: typeof t.min === 'number' ? t.min : null
		}))
	);
	let useMapping = $state(Array.isArray(initial.mapping) && initial.mapping.length > 0);
	let mapping = $state<MappingRow[]>(
		(initial.mapping ?? []).map((r: any) => ({
			outcome: String(r.outcome ?? ''),
			tier: String(r.tier ?? '')
		}))
	);

	let tiers = $state<Tier[]>([]);
	let rules = $state<Rule[]>([]);
	const numericRules = $derived(rules.filter((r) => r.kind === 'number'));
	const yesNoRules = $derived(rules.filter((r) => r.kind !== 'number'));

	$effect(() => {
		fetch('/tiers?is_visible=true')
			.then((res) => (res.ok ? res.json() : { results: [] }))
			.then((data) => (tiers = (data.results ?? data) as Tier[]));
	});

	$effect(() => {
		const id = $quickFormId;
		if (!id) {
			rules = [];
			return;
		}
		fetch(`/quick-forms/${id}`)
			.then((res) => (res.ok ? res.json() : {}))
			.then((data) => (rules = ((data as any).outcomes_definition ?? []) as Rule[]));
	});

	const ruleLabel = (rule: Rule) => rule.label ?? rule.annotation ?? rule.ref_id;

	// Writes the tier entry back, leaving any other target's entry untouched.
	function sync() {
		const others = (($onAccept as any[]) ?? []).filter((e) => e?.target !== TIER_TARGET);
		if (!enabled) {
			$onAccept = others;
			return;
		}
		const config: Record<string, unknown> = {};
		if (useBands) {
			config.bands = {
				outcome: bandOutcome,
				thresholds: thresholds.map((t) => (t.min === null ? { tier: t.tier } : t))
			};
		}
		if (useMapping) config.mapping = mapping;
		$onAccept = [...others, { target: TIER_TARGET, config }];
	}

	function addThreshold() {
		thresholds = [...thresholds, { tier: '', min: null }];
		sync();
	}

	function addMapping() {
		mapping = [...mapping, { outcome: '', tier: '' }];
		sync();
	}
</script>

<div
	class="rounded-lg border border-surface-200-800 p-3 flex flex-col gap-3"
	data-testid="on-accept-editor"
>
	<div>
		<p class="text-sm font-semibold">{m.onAcceptSection()}</p>
		<p class="text-xs text-surface-500">{m.onAcceptSectionHelpText()}</p>
	</div>

	<label class="flex items-center gap-2 text-sm">
		<input
			type="checkbox"
			class="checkbox"
			checked={enabled}
			onchange={(e) => {
				enabled = e.currentTarget.checked;
				sync();
			}}
			data-testid="on-accept-tier-toggle"
		/>
		{m.onAcceptSetEntityTier()}
	</label>

	{#if enabled}
		<div class="flex flex-col gap-3 pl-6">
			<label class="flex items-center gap-2 text-sm">
				<input
					type="checkbox"
					class="checkbox"
					checked={useBands}
					onchange={(e) => {
						useBands = e.currentTarget.checked;
						sync();
					}}
				/>
				{m.tierBands()}
			</label>
			{#if useBands}
				<div class="flex flex-col gap-2 pl-6">
					<label class="label">
						<span class="text-xs text-surface-600-400">{m.tierBandsValue()}</span>
						<select
							class="select text-sm"
							value={bandOutcome}
							onchange={(e) => {
								bandOutcome = e.currentTarget.value;
								sync();
							}}
						>
							<option value="">--</option>
							{#each numericRules as rule (rule.ref_id)}
								<option value={rule.ref_id}>{ruleLabel(rule)}</option>
							{/each}
						</select>
						{#if numericRules.length === 0}
							<span class="text-xs text-warning-700">{m.tierBandsNoNumericRule()}</span>
						{/if}
					</label>
					{#each thresholds as row, index (index)}
						<div class="flex flex-wrap items-center gap-2 text-sm">
							<select
								class="select text-sm w-40"
								value={row.tier}
								onchange={(e) => {
									thresholds[index].tier = e.currentTarget.value;
									sync();
								}}
							>
								<option value="">--</option>
								{#each tiers as tier (tier.id)}
									<option value={tier.id}>{safeTranslate(tier.name)}</option>
								{/each}
							</select>
							<span class="text-surface-500">{m.tierBandsFrom()}</span>
							<input
								type="number"
								step="any"
								class="input w-24 text-sm"
								value={row.min ?? ''}
								placeholder={index === thresholds.length - 1 ? m.tierBandsRest() : ''}
								onchange={(e) => {
									const v = e.currentTarget.value;
									thresholds[index].min = v === '' ? null : Number(v);
									sync();
								}}
							/>
							<button
								type="button"
								class="btn-icon btn-icon-sm text-error-500"
								aria-label={m.delete()}
								onclick={() => {
									thresholds = thresholds.filter((_, i) => i !== index);
									sync();
								}}><i class="fa-solid fa-trash"></i></button
							>
						</div>
					{/each}
					<button type="button" class="btn btn-sm preset-tonal w-fit" onclick={addThreshold}>
						<i class="fa-solid fa-plus mr-1"></i>{m.tierBandsAdd()}
					</button>
					<p class="text-xs text-surface-500">{m.tierBandsHelpText()}</p>
				</div>
			{/if}

			<label class="flex items-center gap-2 text-sm">
				<input
					type="checkbox"
					class="checkbox"
					checked={useMapping}
					onchange={(e) => {
						useMapping = e.currentTarget.checked;
						sync();
					}}
				/>
				{m.tierMapping()}
			</label>
			{#if useMapping}
				<div class="flex flex-col gap-2 pl-6">
					{#each mapping as row, index (index)}
						<div class="flex flex-wrap items-center gap-2 text-sm">
							<select
								class="select text-sm w-56"
								value={row.outcome}
								onchange={(e) => {
									mapping[index].outcome = e.currentTarget.value;
									sync();
								}}
							>
								<option value="">--</option>
								{#each yesNoRules as rule (rule.ref_id)}
									<option value={rule.ref_id}>{ruleLabel(rule)}</option>
								{/each}
							</select>
							<span class="text-surface-500">→</span>
							<select
								class="select text-sm w-40"
								value={row.tier}
								onchange={(e) => {
									mapping[index].tier = e.currentTarget.value;
									sync();
								}}
							>
								<option value="">--</option>
								{#each tiers as tier (tier.id)}
									<option value={tier.id}>{safeTranslate(tier.name)}</option>
								{/each}
							</select>
							<button
								type="button"
								class="btn-icon btn-icon-sm text-error-500"
								aria-label={m.delete()}
								onclick={() => {
									mapping = mapping.filter((_, i) => i !== index);
									sync();
								}}><i class="fa-solid fa-trash"></i></button
							>
						</div>
					{/each}
					<button type="button" class="btn btn-sm preset-tonal w-fit" onclick={addMapping}>
						<i class="fa-solid fa-plus mr-1"></i>{m.tierMappingAdd()}
					</button>
					<p class="text-xs text-surface-500">{m.tierMappingHelpText()}</p>
				</div>
			{/if}
			<p class="text-xs text-surface-500">{m.tierHighestWins()}</p>
		</div>
	{/if}

	{#if $errors}
		<ul class="text-xs text-error-500">
			{#each [$errors].flat() as error}
				<li>{safeTranslate(String(error).split(':').pop() ?? '')}</li>
			{/each}
		</ul>
	{/if}
</div>
