<script lang="ts">
	import Anchor from '#lib/components/Anchor/Anchor.svelte';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import { gotoOrLoad } from '#lib/utils/breadcrumbs.js';
	import { formatDateOrDateTime } from '#lib/utils/datetime.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';
	import { getLocale } from '#paraglide/runtime.js';

	interface Props {
		assetId: string;
	}

	let { assetId }: Props = $props();

	type Option = { kind: 'form' | 'publication'; id: string; name: string };
	type Journey = {
		response: { id: string; ref_id: string; status: string; quick_form: string } | null;
		risk_assessment: { id: string; str: string; scenarios: number } | null;
		audit: { id: string; str: string; progress: number } | null;
		accreditation: {
			id: string;
			str: string;
			status: string;
			category: string;
			expiry_date: string | null;
		} | null;
		past_cycles: number;
	};

	let journey: Journey | null = $state(null);
	let options: Option[] = $state([]);
	let choosing = $state(false);
	let starting = $state(false);
	const toastStore = getToastStore();

	$effect(() => {
		// Aborted when the asset changes, so a late answer cannot land on another one.
		const controller = new AbortController();
		fetch(`/assets/${assetId}/assessment-journey`, { signal: controller.signal })
			.then((res) => (res.ok ? res.json() : { journey: null, options: [] }))
			.then((body) => {
				journey = body.journey;
				options = Array.isArray(body.options) ? body.options : [];
			})
			.catch(() => {});
		return () => controller.abort();
	});

	const draft = $derived(journey?.response?.status === 'draft');
	const startLabel = $derived(
		draft ? m.resumeFraming() : journey?.response ? m.newFraming() : m.startFraming()
	);

	function startFraming() {
		if (options.length === 1) start(options[0]);
		else choosing = !choosing;
	}

	// One start at a time: a double click must not open two drafts.
	async function start(option: Option) {
		if (starting) return;
		starting = true;
		try {
			const res = await fetch(`/assets/${assetId}/assessment-journey`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ kind: option.kind, id: option.id })
			});
			const body = await res.json().catch(() => ({}));
			if (!res.ok || !body.redirect) {
				toastStore.trigger({
					message: body.error ? safeTranslate(body.error) : m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				return;
			}
			await gotoOrLoad(body.redirect);
		} catch {
			toastStore.trigger({ message: m.anErrorOccurred(), background: 'preset-filled-error-500' });
		} finally {
			starting = false;
		}
	}
</script>

{#if journey && (journey.response || options.length > 0)}
	<div class="card p-4 bg-surface-50-950 shadow-xs space-y-3" data-testid="assessment-journey">
		<div>
			<h3 class="font-semibold">{m.assessmentJourney()}</h3>
			<p class="text-xs text-surface-600-400">{m.assessmentJourneyHelpText()}</p>
		</div>

		<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
			<dt class="text-surface-600-400">{m.framing()}</dt>
			<dd>
				{#if journey.response}
					<Anchor href="/quick-form-responses/{journey.response.id}" class="anchor"
						>{journey.response.ref_id || journey.response.quick_form}</Anchor
					>
					<span class="badge preset-tonal ml-1">{safeTranslate(journey.response.status)}</span>
				{:else}
					<span class="text-surface-600-400">{m.notFramedYet()}</span>
				{/if}
			</dd>

			{#if journey.risk_assessment}
				<dt class="text-surface-600-400">{m.riskAssessment()}</dt>
				<dd>
					<Anchor href="/risk-assessments/{journey.risk_assessment.id}" class="anchor"
						>{journey.risk_assessment.str}</Anchor
					>
					<span class="text-xs text-surface-600-400 ml-1"
						>{m.scenariosCount({ count: journey.risk_assessment.scenarios })}</span
					>
				</dd>
			{/if}

			{#if journey.audit}
				<dt class="text-surface-600-400">{m.audit()}</dt>
				<dd>
					<Anchor href="/compliance-assessments/{journey.audit.id}" class="anchor"
						>{journey.audit.str}</Anchor
					>
					<span class="text-xs text-surface-600-400 ml-1">{journey.audit.progress} %</span>
				</dd>
			{/if}

			{#if journey.accreditation}
				<dt class="text-surface-600-400">{m.accreditation()}</dt>
				<dd>
					<Anchor href="/accreditations/{journey.accreditation.id}" class="anchor"
						>{journey.accreditation.str}</Anchor
					>
					<span class="badge preset-tonal ml-1">{safeTranslate(journey.accreditation.status)}</span>
					<span class="text-xs text-surface-600-400 ml-1"
						>{safeTranslate(journey.accreditation.category)}{#if journey.accreditation.expiry_date}
							· {m.expiryDate()}
							{formatDateOrDateTime(journey.accreditation.expiry_date, getLocale())}{/if}</span
					>
					{#if journey.past_cycles > 0}
						<span class="block text-xs text-surface-600-400"
							>{m.pastCycles({ count: journey.past_cycles })}</span
						>
					{/if}
				</dd>
			{/if}
		</dl>

		{#if options.length > 0}
			<div class="space-y-2">
				<button
					type="button"
					class="btn btn-sm preset-filled-primary-500"
					disabled={starting}
					onclick={startFraming}
					data-testid="start-framing">{startLabel}</button
				>
				{#if choosing && options.length > 1}
					<ul class="space-y-1">
						{#each options as option (option.kind + option.id)}
							<li>
								<button type="button" class="anchor text-sm" onclick={() => start(option)}
									>{option.name}</button
								>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		{/if}
	</div>
{/if}
