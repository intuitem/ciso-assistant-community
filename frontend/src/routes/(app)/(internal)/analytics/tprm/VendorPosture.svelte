<script lang="ts">
	import TierBadge from '#lib/components/ModelTable/field/TierBadge.svelte';
	import {
		latestPerVendor,
		postureOf,
		type Missing,
		type PostureMetric
	} from '#lib/utils/vendor-posture.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';

	interface Props {
		assessments: any[];
		tiers: any[];
		noTier: string;
		onSelectTier: (key: string) => void;
	}

	let { assessments, tiers, noTier, onSelectTier }: Props = $props();

	// Past this, a zone ends with "+n more", which filters the cards below.
	const MAX_CHIPS = 6;
	// Dots stacked per side in a lane; deeper ones overlap rather than leave it.
	const MAX_STACK = 3;

	let view = $state<'list' | 'lanes' | 'quadrant'>('list');
	// Tier key the act-first group ends at; null = the second tier of the scale.
	let actFrom = $state<string | null>(null);
	let metric = $state<PostureMetric>('compliance');

	interface Vendor {
		id: string;
		name: string;
		value: number;
		completion: number;
		gap: number | null;
	}

	const missingLabel: Record<Missing, () => string> = {
		notAssessed: m.notAssessed,
		noScore: m.noScore,
		hidden: m.resultHidden
	};

	const rows = $derived.by(() => {
		const vendors = latestPerVendor(assessments);
		const byTier = new Map<string, any[]>();
		for (const assessment of vendors) {
			const key = assessment.tier?.id ?? noTier;
			if (!byTier.has(key)) byTier.set(key, []);
			byTier.get(key)!.push(assessment);
		}
		const scale = tiers
			.filter((tier) => tier.is_visible || byTier.has(tier.id))
			.map((tier) => ({ key: tier.id, tier, target: tier.compliance_target ?? null }));
		if (byTier.has(noTier)) scale.push({ key: noTier, tier: null, target: null });

		return scale.map(({ key, tier, target: complianceTarget }) => {
			// Targets are compliance shares: a score is never held against one.
			const target = metric === 'compliance' ? complianceTarget : null;
			const known: Vendor[] = [];
			const missing: { id: string; name: string; why: string }[] = [];
			for (const assessment of byTier.get(key) ?? []) {
				const posture =
					!assessment.compliance_overview && assessment.compliance_assessment_id !== '#'
						? ({ missing: 'hidden' } as const)
						: postureOf(assessment.compliance_overview, metric);
				if ('missing' in posture) {
					missing.push({
						id: assessment.entity_assessment_id,
						name: assessment.provider,
						why: missingLabel[posture.missing]()
					});
				} else {
					known.push({
						id: assessment.entity_assessment_id,
						name: assessment.provider,
						value: posture.value,
						completion: assessment.completion ?? 0,
						gap: target == null ? null : posture.value - target
					});
				}
			}
			known.sort((a, b) => a.value - b.value);
			const below = known.filter((vendor) => vendor.gap != null && vendor.gap < 0);
			return {
				key,
				tier,
				target,
				known,
				missing,
				below,
				meets: known.filter((vendor) => vendor.gap == null || vendor.gap >= 0)
			};
		});
	});

	const belowCount = $derived(rows.reduce((sum, row) => sum + row.below.length, 0));

	const tiered = $derived(rows.filter((row) => row.tier));
	const cutIndex = $derived(
		Math.max(
			0,
			rows.findIndex((row) => row.key === (actFrom ?? tiered[Math.min(1, tiered.length - 1)]?.key))
		)
	);
	const notPlotted = $derived(rows.flatMap((row) => row.missing));

	// Close dots stack above and below the axis instead of hiding each other.
	function swarm(vendors: Vendor[]) {
		const bins = new Map<number, number>();
		return vendors.map((vendor) => {
			const bin = Math.round(vendor.value / 3);
			const index = (bins.get(bin) ?? -1) + 1;
			bins.set(bin, index);
			const level = Math.min(Math.ceil(index / 2), MAX_STACK);
			const offset = index === 0 ? 0 : (index % 2 ? -1 : 1) * level * 14;
			return { vendor, offset };
		});
	}

	const signed = (gap: number) => (gap > 0 ? `+${gap}` : `${gap}`);
	const segment = (active: boolean) =>
		`btn btn-sm ${active ? 'bg-surface-50-950 text-primary-700-300 shadow-sm ring-1 ring-surface-300-700 font-semibold' : 'text-surface-600-400'}`;
</script>

{#snippet gapPill(gap: number)}
	<span
		class="inline-flex items-center gap-1 rounded-full px-1.5 text-[11px] font-bold leading-4 tabular-nums {gap <
		0
			? 'preset-filled-error-500'
			: 'bg-success-100-900 text-success-800-200'}"
	>
		<i class="fa-solid {gap < 0 ? 'fa-arrow-down' : 'fa-check'} text-[9px]" aria-hidden="true"></i>
		{signed(gap)}
	</span>
{/snippet}

{#snippet chip(vendor: Vendor)}
	<a
		href="/entity-assessments/{vendor.id}"
		class="flex w-56 flex-col gap-0.5 rounded-lg border border-surface-200-800 bg-surface-50-950 px-2.5 py-1.5 hover:border-primary-500"
		title={vendor.name}
		data-testid="posture-chip"
	>
		<span class="truncate text-xs font-semibold text-surface-950-50">{vendor.name}</span>
		<span class="flex items-center gap-1.5 text-xs tabular-nums">
			<span class="text-sm font-bold text-surface-950-50">{vendor.value}%</span>
			{#if vendor.gap != null}
				{@render gapPill(vendor.gap)}
			{/if}
			{#if vendor.completion < 100}
				<span class="ml-auto whitespace-nowrap text-surface-600-400">
					{vendor.completion === 0
						? m.notStarted()
						: m.answeredPercent({ value: vendor.completion })}</span
				>
			{/if}
		</span>
	</a>
{/snippet}

{#snippet zone(vendors: Vendor[], key: string)}
	{#each vendors.slice(0, MAX_CHIPS) as vendor (vendor.id)}
		{@render chip(vendor)}
	{:else}
		<span class="text-xs text-surface-500">–</span>
	{/each}
	{#if vendors.length > MAX_CHIPS}
		<button
			type="button"
			class="w-56 rounded-lg border border-dashed border-surface-400-600 px-2.5 py-1.5 text-left text-xs font-semibold text-surface-700-300 hover:border-primary-500"
			onclick={() => onSelectTier(key)}
		>
			{m.moreCount({ count: vendors.length - MAX_CHIPS })}
		</button>
	{/if}
{/snippet}

{#snippet dot(vendor: Vendor, offset: number, label: boolean, drop: boolean)}
	<a
		href="/entity-assessments/{vendor.id}"
		class="group absolute size-4 rounded-full ring-2 ring-surface-50-950 hover:z-20 hover:ring-primary-500 focus-visible:z-20 {vendor.gap ==
		null
			? 'bg-surface-500'
			: vendor.gap < 0
				? 'bg-error-500'
				: 'border-[3px] border-success-600-400 bg-surface-50-950'}"
		style="left: calc({vendor.value}% - 8px); top: calc(50% - 8px + {offset}px)"
		aria-label="{vendor.name} {vendor.value}%"
		data-testid="posture-dot"
	>
		<!-- Instant, unlike `title`; flips near the edges since the scroll box clips overflow. -->
		<span
			class="pointer-events-none absolute hidden flex-col gap-1 whitespace-nowrap rounded-md bg-surface-900-100 px-2.5 py-1.5 text-xs text-surface-50-950 shadow-lg group-hover:flex group-focus-visible:flex {drop
				? 'top-full mt-2'
				: 'bottom-full mb-2'} {vendor.value > 70
				? 'right-0'
				: vendor.value < 15
					? 'left-0'
					: 'left-1/2 -translate-x-1/2'}"
			role="tooltip"
		>
			<span class="font-semibold">{vendor.name}</span>
			<span class="flex items-center gap-1.5 tabular-nums">
				<span class="font-bold">{vendor.value}%</span>
				{#if vendor.gap != null}{@render gapPill(vendor.gap)}{/if}
				{#if vendor.completion < 100}
					<span class="opacity-75"
						>{vendor.completion === 0
							? m.notStarted()
							: m.answeredPercent({ value: vendor.completion })}</span
					>
				{/if}
			</span>
		</span>
		{#if label}
			<span
				class="pointer-events-none absolute left-full top-1/2 ml-1.5 max-w-40 -translate-y-1/2 truncate text-xs font-semibold text-surface-950-50"
				>{vendor.name}</span
			>
		{/if}
	</a>
{/snippet}

{#snippet tierLabel(row: (typeof rows)[number])}
	<div class="flex flex-col gap-1">
		{#if row.tier}
			<TierBadge cell={row.tier} />
		{:else}
			<span class="text-sm font-semibold text-surface-600-400">{m.untiered()}</span>
		{/if}
		<span class="text-xs text-surface-600-400">
			{row.target == null ? m.noTarget() : m.targetPercent({ target: row.target })}
		</span>
		<span
			class="text-xs {row.below.length
				? 'font-bold text-error-700-300'
				: 'font-semibold text-surface-700-300'}"
		>
			{row.target == null || !row.known.length
				? m.assessedCount({ count: row.known.length })
				: m.belowOfTotal({ below: row.below.length, total: row.known.length })}
		</span>
	</div>
{/snippet}

<section
	class="card mx-6 mt-4 flex flex-col gap-4 border border-surface-200-800 bg-surface-50-950 p-5"
	data-testid="vendor-posture"
>
	<div class="flex flex-wrap items-start justify-between gap-4">
		<div class="flex max-w-3xl flex-col gap-1">
			<p class="text-sm text-surface-600-400">
				{metric === 'compliance' ? m.vendorPostureComplianceHelp() : m.vendorPostureScoreHelp()}
			</p>
		</div>
		<div class="flex flex-wrap gap-3">
			<div
				role="group"
				aria-label={m.postureView()}
				class="flex gap-0.5 rounded-lg bg-surface-200-800 p-0.5"
			>
				<button
					type="button"
					class={segment(view === 'list')}
					aria-pressed={view === 'list'}
					onclick={() => (view = 'list')}
				>
					<i class="fa-solid fa-layer-group"></i>{m.tierList()}
				</button>
				<button
					type="button"
					class={segment(view === 'lanes')}
					aria-pressed={view === 'lanes'}
					onclick={() => (view = 'lanes')}
				>
					<i class="fa-solid fa-chart-simple fa-rotate-90"></i>{m.lanes()}
				</button>
				<button
					type="button"
					class={segment(view === 'quadrant')}
					aria-pressed={view === 'quadrant'}
					onclick={() => (view = 'quadrant')}
				>
					<i class="fa-solid fa-table-cells-large"></i>{m.quadrant()}
				</button>
			</div>
			<div
				role="group"
				aria-label={m.postureMetric()}
				class="flex gap-0.5 rounded-lg bg-surface-200-800 p-0.5"
			>
				<button
					type="button"
					class={segment(metric === 'compliance')}
					aria-pressed={metric === 'compliance'}
					onclick={() => (metric = 'compliance')}
				>
					{m.compliance()}
				</button>
				<button
					type="button"
					class={segment(metric === 'score')}
					aria-pressed={metric === 'score'}
					onclick={() => (metric = 'score')}
				>
					{m.score()}
				</button>
			</div>
		</div>
	</div>

	{#if view === 'list'}
		<div class="flex flex-col gap-2 overflow-x-auto" data-testid="posture-tier-list">
			<div
				class="grid min-w-[56rem] grid-cols-[10rem_9rem_1fr_1fr] gap-2 text-xs font-semibold uppercase tracking-wider text-surface-600-400"
			>
				<span>{m.tier()}</span>
				<span>{m.notAvailableShort()}</span>
				<span class="flex items-center gap-1.5"
					><i class="fa-solid fa-arrow-down text-error-600-400" aria-hidden="true"
					></i>{m.belowTarget()}</span
				>
				<span class="flex items-center gap-1.5"
					><i class="fa-solid fa-check text-success-600-400" aria-hidden="true"
					></i>{m.meetsTarget()}</span
				>
			</div>
			{#each rows as row (row.key)}
				<div
					class="grid min-w-[56rem] grid-cols-[10rem_9rem_1fr_1fr] gap-2"
					data-testid="posture-row"
				>
					{@render tierLabel(row)}
					<div
						class="flex flex-col justify-center gap-1 rounded-lg border p-2 {row.missing.length
							? 'border-dashed border-surface-400-600'
							: 'border-surface-200-800'}"
					>
						{#each row.missing as vendor (vendor.id)}
							<a
								href="/entity-assessments/{vendor.id}"
								class="flex flex-col hover:text-primary-500"
							>
								<span class="truncate text-xs font-semibold">{vendor.name}</span>
								<span class="text-xs text-surface-600-400">{vendor.why}</span>
							</a>
						{:else}
							<span class="text-xs text-surface-500">–</span>
						{/each}
					</div>
					{#if row.target == null}
						<div
							class="col-span-2 flex flex-wrap content-center gap-1.5 rounded-lg border border-surface-200-800 p-2"
						>
							{@render zone(row.meets, row.key)}
						</div>
					{:else}
						<div
							class="flex flex-wrap content-center gap-1.5 rounded-lg border p-2 {row.below.length
								? 'border-error-300-700 bg-error-500/10'
								: 'border-surface-200-800'}"
						>
							{@render zone(row.below, row.key)}
						</div>
						<div
							class="flex flex-wrap content-center gap-1.5 rounded-lg border border-surface-200-800 p-2"
						>
							{@render zone(row.meets, row.key)}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{:else if view === 'quadrant'}
		<div class="flex flex-col gap-3" data-testid="posture-quadrant">
			<label class="flex items-center gap-2 self-start text-sm font-semibold text-surface-700-300">
				{m.actFirstFrom()}
				<select
					class="select w-auto py-1 text-sm"
					value={rows[cutIndex]?.key}
					onchange={(event) => (actFrom = event.currentTarget.value)}
				>
					{#each tiered as row (row.key)}
						<option value={row.key}>{safeTranslate(row.tier.name)}</option>
					{/each}
				</select>
			</label>
			<div class="overflow-x-auto">
				<div class="min-w-[40rem]">
					{#each rows as row, index (row.key)}
						{@const act = index <= cutIndex && row.tier != null}
						{@const groupStart = index === 0 || index === cutIndex + 1}
						{@const previous = rows[index - 1]?.target ?? null}
						<div class="grid grid-cols-[10rem_1fr] items-center gap-3">
							{@render tierLabel(row)}
							<div
								class="relative h-28 {index === cutIndex + 1
									? 'border-t-[3px] border-surface-950-50'
									: index
										? 'border-t border-surface-200-800'
										: ''}"
								data-testid="posture-band"
							>
								{#if row.target != null}
									<div
										class="absolute inset-y-0 left-0 {act
											? 'bg-error-500/10'
											: 'bg-surface-500/10'}"
										style="width: {row.target}%"
									></div>
									{#if act}
										<div
											class="absolute inset-y-0 right-0 bg-success-500/10"
											style="left: {row.target}%"
										></div>
									{/if}
									<div
										class="absolute inset-y-0 border-l-2 border-dashed border-surface-500"
										style="left: {row.target}%"
									></div>
									<!-- Staircase step joining this tier's target to the previous one. -->
									{#if previous != null && index !== cutIndex + 1}
										<div
											class="absolute top-0 border-t-2 border-dashed border-surface-500"
											style="left: {Math.min(previous, row.target)}%; width: {Math.abs(
												previous - row.target
											)}%"
										></div>
									{/if}
								{/if}
								{#if groupStart && row.tier}
									<span
										class="pointer-events-none absolute left-2 top-1.5 text-[11px] font-bold uppercase tracking-wider {act
											? 'text-error-700-300'
											: 'text-surface-600-400'}"
									>
										{act ? m.actFirst() : m.improveWhenDue()}
									</span>
									<span
										class="pointer-events-none absolute right-2 top-1.5 text-[11px] font-bold uppercase tracking-wider {act
											? 'text-success-700-300'
											: 'text-surface-600-400'}"
									>
										{act ? m.maintain() : m.lowConcern()}
									</span>
								{/if}
								{#each swarm(row.known) as { vendor, offset } (vendor.id)}
									{@render dot(
										vendor,
										offset,
										act && vendor.gap != null && vendor.gap < 0,
										index === 0
									)}
								{/each}
							</div>
						</div>
					{/each}
					<div
						class="grid grid-cols-[10rem_1fr] gap-3 border-t border-surface-200-800 pt-1 text-xs font-semibold text-surface-600-400"
					>
						<span></span>
						<span class="flex justify-between tabular-nums"
							><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span
							></span
						>
					</div>
				</div>
			</div>
			{#if notPlotted.length}
				<p class="text-xs text-surface-600-400">
					<span class="font-semibold">{m.notPlotted()}:</span>
					{#each notPlotted as vendor, index (vendor.id)}
						<a href="/entity-assessments/{vendor.id}" class="hover:text-primary-500"
							>{vendor.name} ({vendor.why})</a
						>{index < notPlotted.length - 1 ? ', ' : ''}
					{/each}
				</p>
			{/if}
		</div>
	{:else}
		<div class="flex flex-col gap-4 lg:flex-row" data-testid="posture-lanes">
			<div class="min-w-0 flex-1 overflow-x-auto">
				<div class="min-w-[40rem]">
					<div
						class="grid grid-cols-[10rem_3.5rem_1fr] gap-3 border-b border-surface-200-800 pb-1 text-xs font-semibold text-surface-600-400"
					>
						<span class="uppercase tracking-wider">{m.tier()}</span>
						<span class="uppercase tracking-wider">{m.notAvailableShort()}</span>
						<span class="flex justify-between tabular-nums"
							><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span
							></span
						>
					</div>
					{#each rows as row, index (row.key)}
						<div
							class="grid grid-cols-[10rem_3.5rem_1fr] items-center gap-3 border-b border-surface-100-900"
						>
							{@render tierLabel(row)}
							<button
								type="button"
								class="group relative rounded-md py-1 text-center text-sm font-bold {row.missing
									.length
									? 'border border-dashed border-surface-400-600'
									: 'text-surface-500'}"
								disabled={!row.missing.length}
								onclick={() => onSelectTier(row.key)}
							>
								{row.missing.length || '–'}
								{#if row.missing.length}
									<span
										class="pointer-events-none absolute left-0 z-20 hidden {index === 0
											? 'top-full mt-1'
											: 'bottom-full mb-1'} flex-col gap-0.5 whitespace-nowrap rounded-md bg-surface-900-100 px-2.5 py-1.5 text-left text-xs font-normal text-surface-50-950 shadow-lg group-hover:flex group-focus-visible:flex"
										role="tooltip"
									>
										{#each row.missing as vendor (vendor.id)}
											<span><b>{vendor.name}</b> · {vendor.why}</span>
										{/each}
									</span>
								{/if}
							</button>
							<div class="relative h-28">
								{#if row.target != null}
									<div
										class="absolute inset-y-3 right-0 rounded-md bg-success-500/10"
										style="left: {row.target}%"
									></div>
									<div
										class="absolute inset-y-1.5 border-l-2 border-dashed border-surface-500"
										style="left: {row.target}%"
									></div>
								{/if}
								<div class="absolute inset-x-0 top-1/2 h-px bg-surface-200-800"></div>
								{#each swarm(row.known) as { vendor, offset } (vendor.id)}
									{@render dot(vendor, offset, false, index === 0)}
								{/each}
							</div>
						</div>
					{/each}
				</div>
			</div>
			<aside
				class="flex w-full flex-col gap-3 rounded-lg border border-surface-200-800 p-4 lg:w-72"
				data-testid="posture-below-list"
			>
				<div class="flex items-baseline justify-between">
					<h3 class="text-sm font-bold text-error-700-300">{m.belowTarget()}</h3>
					<span class="text-xs font-semibold text-surface-600-400 tabular-nums">{belowCount}</span>
				</div>
				{#each rows.filter((row) => row.below.length) as row (row.key)}
					<div class="flex flex-col gap-1">
						{#if row.tier}<TierBadge cell={row.tier} />{/if}
						{#each row.below as vendor (vendor.id)}
							<a
								href="/entity-assessments/{vendor.id}"
								class="flex justify-between gap-2 border-b border-surface-100-900 py-1 text-sm hover:text-primary-500"
							>
								<span class="truncate">{vendor.name}</span>
								<span class="flex items-center gap-1.5 whitespace-nowrap tabular-nums">
									{vendor.value}%
									{@render gapPill(vendor.gap ?? 0)}
								</span>
							</a>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-surface-600-400">
						{metric === 'compliance' ? m.noVendorBelowTarget() : m.noTarget()}
					</p>
				{/each}
			</aside>
		</div>
	{/if}
</section>
