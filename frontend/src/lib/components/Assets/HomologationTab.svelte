<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import Anchor from '#lib/components/Anchor/Anchor.svelte';
	import AssessmentJourneyCard from '#lib/components/Assets/AssessmentJourneyCard.svelte';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import { complianceResultColorMap } from '#lib/utils/constants.js';
	import { formatDateOrDateTime } from '#lib/utils/datetime.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';
	import { getLocale } from '#paraglide/runtime.js';

	type Cycle = {
		id: string;
		str: string;
		status: string | null;
		category: string | null;
		commission_date: string | null;
		expiry_date: string | null;
	};
	type Journey = {
		response: { id: string; ref_id: string; status: string; quick_form: string } | null;
		risk_assessment: {
			id: string;
			str: string;
			scenarios: number;
			levels: {
				counts: { name: string; hexcolor?: string; count: number }[];
				unrated: number;
			};
		} | null;
		audit: {
			id: string;
			str: string;
			progress: number;
			results: { result: string; count: number }[];
		} | null;
		accreditation:
			| (Cycle & {
					open: boolean;
					frozen: boolean;
					deliverables: {
						risk_assessment: { id: string; str: string } | null;
						audit: { id: string; str: string } | null;
					} | null;
					authority: string | null;
					duration_months: number | null;
			  })
			| null;
		past_cycles: Cycle[];
		can_start: boolean;
	};

	interface Props {
		journey: Journey;
		assetId: string;
	}

	let { journey, assetId }: Props = $props();

	const toastStore = getToastStore();
	let busy = $state(false);

	// Start the next cycle, or freeze the deliverables of the one in progress.
	async function cycleStep(step: 'start' | 'freeze') {
		if (busy) return;
		busy = true;
		try {
			const res = await fetch(`/assets/${assetId}/accreditation-cycle`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ step })
			});
			const body = await res.json().catch(() => ({}));
			if (!res.ok) {
				toastStore.trigger({
					message: body.error ? safeTranslate(body.error) : m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				return;
			}
			await invalidateAll();
		} finally {
			busy = false;
		}
	}

	const cycle = $derived(journey.accreditation);
	const daysLeft = $derived(
		cycle?.expiry_date
			? Math.ceil((new Date(cycle.expiry_date).getTime() - Date.now()) / 86_400_000)
			: null
	);
	const auditTotal = $derived(
		(journey.audit?.results ?? []).reduce((total, r) => total + r.count, 0)
	);
	const date = (value: string | null) => (value ? formatDateOrDateTime(value, getLocale()) : '--');
</script>

<div class="space-y-4 px-2">
	<p class="text-xs text-surface-600-400">{m.homologationTabHelpText()}</p>

	{#if cycle}
		<section class="card p-4 bg-surface-50-950 border border-surface-200-800 space-y-4">
			<div class="flex flex-wrap items-center gap-2">
				<span class="text-xs uppercase text-surface-600-400"
					>{cycle.open ? m.currentCycle() : m.lastCycle()}</span
				>
				<Anchor href="/accreditations/{cycle.id}" class="anchor font-semibold">{cycle.str}</Anchor>
				{#if cycle.status}
					<span class="badge preset-tonal-primary">{safeTranslate(cycle.status)}</span>
				{/if}
				{#if cycle.category}
					<span class="text-sm text-surface-600-400">{safeTranslate(cycle.category)}</span>
				{/if}
			</div>
			<dl class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
				<div>
					<dt class="text-xs text-surface-600-400">{m.commissionDate()}</dt>
					<dd class="font-semibold">{date(cycle.commission_date)}</dd>
				</div>
				<div>
					<dt class="text-xs text-surface-600-400">{m.durationMonths()}</dt>
					<dd class="font-semibold">{cycle.duration_months ?? '--'}</dd>
				</div>
				<div>
					<dt class="text-xs text-surface-600-400">{m.expiryDate()}</dt>
					<dd class="font-semibold">
						{date(cycle.expiry_date)}
						{#if daysLeft !== null}
							<span class="font-normal text-surface-600-400"
								>· {daysLeft < 0 ? m.expired() : m.daysLeft({ count: daysLeft })}</span
							>
						{/if}
					</dd>
				</div>
				<div>
					<dt class="text-xs text-surface-600-400">{m.authority()}</dt>
					<dd class="font-semibold">{cycle.authority ?? '--'}</dd>
				</div>
			</dl>
			{#if cycle.open && !cycle.frozen}
				<div class="flex flex-wrap items-center justify-between gap-3">
					<p class="text-xs text-surface-600-400">{m.accreditationFollowsServiceHelpText()}</p>
					<button
						type="button"
						class="btn btn-sm preset-filled-primary-500"
						disabled={busy}
						onclick={() => cycleStep('freeze')}>{m.freezeDeliverables()}</button
					>
				</div>
			{:else if cycle.deliverables}
				<div class="space-y-1 text-sm">
					<p>
						<span class="font-semibold">{m.deliverablesFrozen()} :</span>
						{#if cycle.deliverables.risk_assessment}
							<Anchor
								href="/risk-assessments/{cycle.deliverables.risk_assessment.id}"
								class="anchor">{cycle.deliverables.risk_assessment.str}</Anchor
							>
						{/if}
						{#if cycle.deliverables.audit}
							·
							<Anchor href="/compliance-assessments/{cycle.deliverables.audit.id}" class="anchor"
								>{cycle.deliverables.audit.str}</Anchor
							>
						{/if}
					</p>
					{#if cycle.open}
						<p class="text-xs text-surface-600-400">{m.deliverablesFrozenHelpText()}</p>
					{/if}
				</div>
			{/if}
		</section>
	{/if}

	{#if journey.can_start}
		<div
			class="flex flex-wrap items-center justify-between gap-3 card p-4 border border-dashed border-surface-300-700"
		>
			<p class="text-sm text-surface-600-400">{m.noAccreditationHelpText()}</p>
			<button
				type="button"
				class="btn btn-sm preset-filled-primary-500"
				disabled={busy}
				onclick={() => cycleStep('start')}>{m.startAccreditation()}</button
			>
		</div>
	{/if}

	<h3 class="font-semibold text-sm pt-2">{m.theService()}</h3>

	<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
		<section class="card p-4 border border-surface-200-800 space-y-2">
			<h3 class="font-semibold text-sm">{m.framing()}</h3>
			{#if journey.response}
				<Anchor href="/quick-form-responses/{journey.response.id}" class="anchor text-sm"
					>{journey.response.ref_id || journey.response.quick_form}</Anchor
				>
				<span class="badge preset-tonal ml-1">{safeTranslate(journey.response.status)}</span>
			{:else}
				<p class="text-sm text-surface-600-400">{m.framingPreparesAccreditationHelpText()}</p>
			{/if}
			<AssessmentJourneyCard {assetId} />
		</section>

		<section class="card p-4 border border-surface-200-800 space-y-2">
			<h3 class="font-semibold text-sm">{m.audit()}</h3>
			{#if journey.audit}
				<Anchor href="/compliance-assessments/{journey.audit.id}" class="anchor text-sm block"
					>{journey.audit.str}</Anchor
				>
				{#if auditTotal > 0}
					<div class="flex h-2 w-full overflow-hidden rounded-full">
						{#each journey.audit.results as r (r.result)}
							<div
								title="{r.count} {safeTranslate(r.result)}"
								style="width: {(r.count / auditTotal) *
									100}%; background-color: {complianceResultColorMap[r.result] ?? '#d1d5db'}"
							></div>
						{/each}
					</div>
					<p class="flex flex-wrap gap-x-3 text-xs text-surface-600-400">
						{#each journey.audit.results as r (r.result)}
							<span>{r.count} {safeTranslate(r.result)}</span>
						{/each}
					</p>
				{/if}
				<p class="text-xs text-surface-600-400">{m.progress()} : {journey.audit.progress} %</p>
			{:else}
				<p class="text-sm text-surface-600-400">--</p>
			{/if}
		</section>

		<section class="card p-4 border border-surface-200-800 space-y-2">
			<h3 class="font-semibold text-sm">{m.riskAssessment()}</h3>
			{#if journey.risk_assessment}
				<Anchor href="/risk-assessments/{journey.risk_assessment.id}" class="anchor text-sm block"
					>{journey.risk_assessment.str}</Anchor
				>
				<p class="text-xs text-surface-600-400">
					{m.scenariosCount({ count: journey.risk_assessment.scenarios })}
				</p>
				<div class="flex flex-wrap gap-1.5">
					{#each journey.risk_assessment.levels.counts.filter((l) => l.count > 0) as level (level.name)}
						<span
							class="badge text-xs text-black"
							style="background-color: {level.hexcolor ?? '#d1d5db'}"
							>{level.count} {level.name}</span
						>
					{/each}
					{#if journey.risk_assessment.levels.unrated > 0}
						<span class="badge preset-tonal text-xs"
							>{m.scenariosNotRated({ count: journey.risk_assessment.levels.unrated })}</span
						>
					{/if}
				</div>
			{:else}
				<p class="text-sm text-surface-600-400">--</p>
			{/if}
		</section>
	</div>

	{#if journey.past_cycles.length > 0}
		<section class="space-y-2">
			<h3 class="font-semibold text-sm">{m.previousCycles()}</h3>
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead class="text-xs text-surface-600-400 text-left">
						<tr>
							<th class="py-1 pr-4">{m.accreditation()}</th>
							<th class="py-1 pr-4">{m.category()}</th>
							<th class="py-1 pr-4">{m.status()}</th>
							<th class="py-1 pr-4">{m.commissionDate()}</th>
							<th class="py-1">{m.expiryDate()}</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-surface-200-800">
						{#each journey.past_cycles as past (past.id)}
							<tr>
								<td class="py-1 pr-4"
									><Anchor href="/accreditations/{past.id}" class="anchor">{past.str}</Anchor></td
								>
								<td class="py-1 pr-4">{past.category ? safeTranslate(past.category) : '--'}</td>
								<td class="py-1 pr-4">{past.status ? safeTranslate(past.status) : '--'}</td>
								<td class="py-1 pr-4">{date(past.commission_date)}</td>
								<td class="py-1">{date(past.expiry_date)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}
</div>
