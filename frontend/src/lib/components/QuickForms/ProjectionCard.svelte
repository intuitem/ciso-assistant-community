<script lang="ts">
	import { ruleLabel as labelOf } from './rule-label';
	import TierBadge from '$lib/components/ModelTable/field/TierBadge.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	type Row = {
		target: string;
		label: string;
		ok: boolean;
		reason: string;
		proposed: string | null;
		value: number | null;
		extra?: { hexcolor?: string; band?: string; outcomes?: string[] };
	};
	type Rule = { ref_id: string; label?: string; annotation?: string };

	interface Props {
		rows: Row[];
		rules?: Rule[];
		note?: string;
		// Inside another card, a bordered panel instead of a card of its own.
		nested?: boolean;
	}

	let { rows, rules = [], note, nested = false }: Props = $props();

	// Nothing resolved yet is the normal state of a form being filled, not an error.
	const PENDING = new Set(['projectionPending', 'noTierResolved', 'valueMissing']);

	const ruleLabel = (refId: string) =>
		labelOf(
			rules.find((r) => r.ref_id === refId),
			refId
		);
	const format = (value: number) => (Number.isInteger(value) ? String(value) : value.toFixed(2));
</script>

<div
	class={nested
		? 'rounded-lg border border-surface-200-800 p-3 max-w-sm'
		: 'card bg-surface-50-950 shadow-sm p-4'}
	data-testid="projection-card"
>
	{#if note}
		<p class="mb-2 text-[11px] text-surface-500">{note}</p>
	{/if}
	<div class="space-y-3">
		{#each rows as row (row.target)}
			<div class="space-y-1">
				<div class="flex items-center justify-between gap-3 text-sm">
					<span class="font-medium">{m.projectedTarget({ label: safeTranslate(row.label) })}</span>
					{#if row.ok && row.extra?.hexcolor !== undefined}
						<TierBadge cell={{ name: row.proposed ?? '', hexcolor: row.extra.hexcolor }} />
					{:else if row.ok}
						<span class="font-semibold">{safeTranslate(row.proposed ?? '')}</span>
					{:else}
						<span class="text-xs text-surface-500">—</span>
					{/if}
				</div>
				{#if row.ok}
					<p class="text-xs text-surface-500">
						{[
							...(row.extra?.band_source === 'score' && row.value !== null
								? [m.projectionFromScore({ value: format(row.value) })]
								: row.extra?.band && row.value !== null
									? [
											m.projectionFrom({
												rule: ruleLabel(row.extra.band),
												value: format(row.value)
											})
										]
									: []),
							...(row.extra?.outcomes ?? []).map(ruleLabel)
						].join(' · ')}
					</p>
				{:else}
					<p class="text-xs text-surface-500">
						{PENDING.has(row.reason) ? m.projectionPending() : safeTranslate(row.reason)}
					</p>
				{/if}
			</div>
		{/each}
	</div>
</div>
