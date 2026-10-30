<script lang="ts">
	import { enhance } from '$app/forms';
	import Anchor from '#lib/components/Anchor/Anchor.svelte';
	import { complianceResultColorMap } from '#lib/utils/constants.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';

	interface Ref {
		id: string;
		str: string;
	}

	interface RelatedRequirement {
		id: string;
		requirement: string;
		description: string | null;
		result: string;
		status: string;
		compliance_assessment: Ref;
		threats: Ref[];
	}

	interface SuggestedControl {
		control: Ref & { status: string };
		target: 'existing' | 'planned';
		via: { id: string; requirement: string; compliance_assessment: Ref }[];
	}

	interface SuggestedLikelihood {
		audit: Ref;
		threat: Ref;
		probability: number;
		name: string;
	}

	interface Props {
		relatedRequirements: RelatedRequirement[];
		suggestedControls: SuggestedControl[];
		suggestedLikelihood?: SuggestedLikelihood[];
		currentProba?: number;
		canEdit: boolean;
	}

	let {
		relatedRequirements,
		suggestedControls,
		suggestedLikelihood = [],
		currentProba = -1,
		canEdit
	}: Props = $props();

	const resultOrder = [
		'non_compliant',
		'partially_compliant',
		'not_assessed',
		'compliant',
		'not_applicable'
	];
	const GAPS = ['non_compliant', 'partially_compliant'];

	// One block per audit: its requirements, worst first, and what it says about the likelihood.
	const audits = $derived.by(() => {
		const byAudit = new Map<string, { audit: Ref; items: RelatedRequirement[] }>();
		for (const item of relatedRequirements) {
			const key = item.compliance_assessment.id;
			if (!byAudit.has(key)) byAudit.set(key, { audit: item.compliance_assessment, items: [] });
			byAudit.get(key)!.items.push(item);
		}
		return [...byAudit.values()].map(({ audit, items }) => {
			const sorted = [...items].sort(
				(a, b) => resultOrder.indexOf(a.result) - resultOrder.indexOf(b.result)
			);
			const counts = resultOrder
				.map((result) => ({ result, count: items.filter((i) => i.result === result).length }))
				.filter((c) => c.count > 0);
			const threats = [...new Map(items.flatMap((i) => i.threats).map((t) => [t.id, t])).values()];
			return {
				audit,
				sorted,
				counts,
				threats,
				gaps: sorted.filter((i) => GAPS.includes(i.result)),
				likelihood: suggestedLikelihood.filter((l) => l.audit.id === audit.id)
			};
		});
	});
	const manyThreats = $derived(
		new Set(relatedRequirements.flatMap((i) => i.threats.map((t) => t.id))).size > 1
	);
	const gapCount = $derived(audits.reduce((n, group) => n + group.gaps.length, 0));
	let expanded: Record<string, boolean> = $state({});
</script>

<details class="group card bg-surface-50-950 shadow-lg overflow-hidden">
	<summary class="flex flex-wrap items-center gap-2 px-4 py-3 cursor-pointer list-none">
		<i
			class="fa-solid fa-chevron-right text-xs text-surface-500 transition-transform group-open:rotate-90"
		></i>
		<span class="font-semibold">{m.relatedRequirements()}</span>
		<span class="badge preset-tonal text-xs">{relatedRequirements.length}</span>
		<span class="ml-auto flex flex-wrap items-center gap-1.5">
			{#if gapCount > 0}
				<span class="badge preset-tonal-error text-xs">{m.gaps()} {gapCount}</span>
			{/if}
			{#each suggestedLikelihood as suggestion (suggestion.audit.id + suggestion.threat.id)}
				<span class="badge preset-tonal-secondary text-xs">{m.likelihood()} {suggestion.name}</span>
			{/each}
			{#if suggestedControls.length > 0}
				<span class="badge preset-tonal-primary text-xs"
					>{m.suggestedControls()} {suggestedControls.length}</span
				>
			{/if}
		</span>
	</summary>

	<div class="space-y-4 px-4 pb-4">
		<p class="text-xs text-surface-600-400">{m.relatedRequirementsHelpText()}</p>

		{#if audits.length === 0}
			<p class="text-sm text-surface-600-400">{m.noRelatedRequirements()}</p>
		{/if}

		{#each audits as group (group.audit.id)}
			{@const shown = expanded[group.audit.id] ? group.sorted : group.gaps}
			<div class="space-y-2">
				<div class="flex flex-wrap items-center gap-3 text-sm">
					<Anchor
						href="/compliance-assessments/{group.audit.id}"
						class="anchor font-semibold truncate"
						title={group.threats.map((t) => t.str).join(', ')}>{group.audit.str}</Anchor
					>
					<div class="flex h-1.5 w-32 shrink-0 overflow-hidden rounded-full">
						{#each group.counts as c (c.result)}
							<div
								title="{c.count} {safeTranslate(c.result)}"
								style="width: {(c.count / group.sorted.length) *
									100}%; background-color: {complianceResultColorMap[c.result] ?? '#d1d5db'}"
							></div>
						{/each}
					</div>
					<span class="text-xs text-surface-600-400"
						>{m.gaps()} {group.gaps.length} / {group.sorted.length}</span
					>
					{#each group.likelihood as suggestion (suggestion.threat.id)}
						<span class="ml-auto inline-flex items-center gap-2 text-xs">
							{m.likelihoodFromTheseRequirements()}
							<span class="badge preset-tonal-secondary">{suggestion.name}</span>
							{#if manyThreats}
								<span class="text-surface-600-400">{suggestion.threat.str}</span>
							{/if}
							{#if canEdit && suggestion.probability !== currentProba}
								<form method="POST" action="?/applySuggestedLikelihood" use:enhance>
									<input type="hidden" name="audit" value={suggestion.audit.id} />
									<button type="submit" class="btn btn-sm preset-tonal-primary">{m.apply()}</button>
								</form>
							{/if}
						</span>
					{/each}
				</div>

				{#if shown.length === 0}
					<p class="text-xs text-surface-600-400">{m.noGapsFound()}</p>
				{:else}
					<ul class="divide-y divide-surface-200-800 text-sm">
						{#each shown as item (item.id)}
							<li class="flex items-center justify-between gap-3 py-1">
								<span class="min-w-0">
									<Anchor
										href="/requirement-assessments/{item.id}"
										class="anchor"
										title={item.description ?? ''}>{item.requirement}</Anchor
									>
									{#if manyThreats}
										<span class="block text-xs text-surface-600-400"
											>{item.threats.map((t) => t.str).join(', ')}</span
										>
									{/if}
								</span>
								<span
									class="badge shrink-0 text-xs"
									style="background-color: {(complianceResultColorMap[item.result] ?? '#d1d5db') +
										'44'}">{safeTranslate(item.result)}</span
								>
							</li>
						{/each}
					</ul>
				{/if}
				{#if group.sorted.length > group.gaps.length}
					<button
						type="button"
						class="anchor text-xs"
						onclick={() => (expanded[group.audit.id] = !expanded[group.audit.id])}
						>{expanded[group.audit.id]
							? m.showGapsOnly()
							: m.showAllRequirements({ count: group.sorted.length })}</button
					>
				{/if}
			</div>
		{/each}

		{#if suggestedControls.length > 0}
			<div class="space-y-2 border-t border-surface-200-800 pt-3">
				<div class="flex flex-wrap items-start justify-between gap-2">
					<div>
						<p class="font-semibold">{m.suggestedControls()}</p>
						<p class="text-sm text-surface-600-400">{m.suggestedControlsHelpText()}</p>
					</div>
					{#if canEdit && suggestedControls.length > 1}
						<form method="POST" action="?/confirmSuggestedControls" use:enhance>
							{#each suggestedControls as suggestion (suggestion.control.id)}
								<input type="hidden" name="id" value={suggestion.control.id} />
							{/each}
							<button type="submit" class="btn btn-sm preset-filled-primary-500">
								{m.confirmAll()}
							</button>
						</form>
					{/if}
				</div>
				<ul class="space-y-2">
					{#each suggestedControls as suggestion (suggestion.control.id)}
						<li class="flex flex-wrap items-center justify-between gap-2 text-sm">
							<div class="flex flex-col">
								<span>
									<Anchor href="/applied-controls/{suggestion.control.id}" class="anchor"
										>{suggestion.control.str}</Anchor
									>
									<span class="badge preset-tonal-secondary ml-1">
										{suggestion.target === 'existing'
											? m.existingControls()
											: m.additionalControls()}
									</span>
								</span>
								{#each suggestion.via as via (via.id)}
									<span class="text-xs text-surface-600-400">
										{m.viaRequirement({
											requirement: via.requirement,
											audit: via.compliance_assessment.str
										})}
									</span>
								{/each}
							</div>
							{#if canEdit}
								<form method="POST" action="?/confirmSuggestedControls" use:enhance>
									<input type="hidden" name="id" value={suggestion.control.id} />
									<button type="submit" class="btn btn-sm preset-tonal-primary">
										{m.confirm()}
									</button>
								</form>
							{/if}
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	</div>
</details>
