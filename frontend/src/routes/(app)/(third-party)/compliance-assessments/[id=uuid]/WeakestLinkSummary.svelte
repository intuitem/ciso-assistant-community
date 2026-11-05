<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { ruleLabel } from '#lib/components/QuickForms/rule-label.js';
	import { getLocale } from '#paraglide/runtime.js';
	import Anchor from '#lib/components/Anchor/Anchor.svelte';
	import type { WeakestLinkResult } from './weakest-link';

	interface Props {
		result: WeakestLinkResult;
		rule: Record<string, any>;
	}

	let { result, rule }: Props = $props();

	const COLUMNS = ['compliant', 'partially_compliant', 'non_compliant', 'not_assessed'] as const;
	const COLOR: Record<string, string> = {
		compliant: 'text-success-600-400',
		partially_compliant: 'text-warning-600-400',
		non_compliant: 'text-error-600-400',
		not_assessed: 'text-surface-500',
		not_applicable: 'text-surface-400-600'
	};

	const label = (r: string) =>
		rule.translations?.[getLocale()]?.[`result_label_${r}`] ||
		rule.result_labels?.[r] ||
		safeTranslate(r);
	const unit = $derived(
		rule.translations?.[getLocale()]?.section_label || rule.section_label || m.staircaseSections()
	);
	const annotation = $derived(rule.translations?.[getLocale()]?.annotation || rule.annotation);
	const percent = (score: number | null) => (score === null ? '—' : `${Math.round(score * 100)}%`);
</script>

<div class="space-y-4">
	<div
		class="flex items-center gap-4 rounded-xl border border-surface-200-800 bg-surface-100-900 p-4"
	>
		<div
			class="flex items-center justify-center min-w-16 h-12 px-2 rounded-xl bg-primary-500 text-white text-xl font-bold tabular-nums shrink-0"
		>
			{percent(result.score)}
		</div>
		<div class="flex flex-col">
			<span class="text-xs uppercase tracking-wide text-surface-600-400"
				>{ruleLabel(rule, rule.ref_id)}</span
			>
			{#if result.sections.length > 1}
				<span class="text-sm text-surface-700-300"
					>{m.weakestLinkOverall({ count: result.sections.length, unit })}</span
				>
			{/if}
			{#if annotation}
				<span class="text-xs text-surface-600-400">{annotation}</span>
			{/if}
		</div>
	</div>

	<div class="overflow-x-auto">
		<table class="w-full text-sm" data-testid="weakest-link-table">
			<thead>
				<tr class="text-left text-xs uppercase tracking-wide text-surface-600-400">
					<th class="py-2 pr-3 font-medium"></th>
					{#each COLUMNS as column (column)}
						<th class="py-2 px-2 font-medium text-center">{label(column)}</th>
					{/each}
					<th class="py-2 pl-3 font-medium text-right">%</th>
				</tr>
			</thead>
			<tbody>
				{#each result.sections as section (section.urn)}
					<tr class="border-t border-surface-200-800 align-top">
						<td class="py-2 pr-3">
							<details>
								<summary class="cursor-pointer font-medium text-surface-900-50">
									{section.name ?? ruleLabel(rule, rule.ref_id)}
								</summary>
								<ul class="mt-2 space-y-1.5">
									{#each section.nodes as node (node.urn)}
										<li class="text-xs">
											<div class="flex items-baseline gap-2">
												<span class="font-semibold {COLOR[node.rating]}">{label(node.rating)}</span>
												<span class="text-surface-800-200"
													>{[node.ref_id, node.name].filter(Boolean).join(' · ')}</span
												>
											</div>
											{#if node.drivers.length && node.rating !== 'compliant'}
												<div class="ml-4 mt-0.5 flex flex-wrap gap-x-3 text-surface-600-400">
													<span>{m.weakestLinkDrivers({ count: node.drivers.length })}</span>
													{#each node.drivers as driver (driver.id)}
														<Anchor
															breadcrumbAction="push"
															href={`/requirement-assessments/${driver.id}`}
															class="anchor">{driver.ref_id ?? driver.name ?? driver.urn}</Anchor
														>
													{/each}
												</div>
											{/if}
										</li>
									{/each}
								</ul>
							</details>
						</td>
						{#each COLUMNS as column (column)}
							<td
								class="py-2 px-2 text-center tabular-nums {section.counts[column]
									? COLOR[column]
									: 'text-surface-400-600'}"
							>
								{section.counts[column]}
							</td>
						{/each}
						<td class="py-2 pl-3 text-right font-semibold tabular-nums">{percent(section.score)}</td
						>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
