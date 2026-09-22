<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import IssueTable from './IssueTable.svelte';
	import { SEVERITIES, aggregateIssuesByType, type SeverityKey } from './utils';

	interface Props {
		assessment: any;
		assessmentType: string;
		activeSeverities: Record<SeverityKey, boolean>;
	}

	let { assessment, assessmentType, activeSeverities }: Props = $props();

	const groups = $derived(
		SEVERITIES.filter(({ key }) => activeSeverities[key])
			.map((severity) => ({
				...severity,
				total: assessment?.quality_check?.[severity.key]?.length ?? 0,
				issues: aggregateIssuesByType(
					assessment?.quality_check?.[severity.key],
					assessmentType,
					assessment.object.id
				)
			}))
			.filter((group) => group.issues.length > 0)
	);
</script>

{#if groups.length > 0}
	<details class="group rounded-lg border border-surface-200-800 overflow-hidden">
		<summary
			class="flex items-center gap-3 px-4 py-3 cursor-pointer list-none bg-surface-100-900/60 hover:bg-surface-100-900 transition-colors"
		>
			<i
				class="fa-solid fa-chevron-right text-xs text-surface-500 transition-transform group-open:rotate-90"
			></i>
			<i
				class="fa-solid {assessmentType === 'risk-assessments'
					? 'fa-biohazard'
					: 'fa-list-check'} text-secondary-500"
			></i>
			<span class="font-semibold truncate text-secondary-950-50">{assessment.object.name}</span>
			<Anchor
				href="/{assessmentType}/{assessment.object.id}"
				label={assessment.object.name}
				stopPropagation
				class="anchor underline underline-offset-2 text-xs shrink-0 whitespace-nowrap"
			>
				<i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
				{m.xRaysView()}
			</Anchor>
			<div class="ml-auto flex items-center gap-1.5 shrink-0">
				{#each groups as group (group.key)}
					<span class="badge {group.preset} text-xs">
						<i class="fa-solid {group.icon}"></i>
						{group.total}
					</span>
				{/each}
			</div>
		</summary>

		<div class="bg-surface-50-950 px-4 py-4 space-y-5">
			{#each groups as group (group.key)}
				<section class="space-y-2">
					<div class="flex items-center gap-2">
						<i class="fa-solid {group.icon} {group.text} text-xs"></i>
						<span class="text-xs font-bold uppercase tracking-wide {group.text}">
							{group.label()}
						</span>
						<span class="text-xs text-surface-500">
							{group.issues.length}
							{group.issues.length === 1 ? m.xRaysIssue() : m.xRaysIssues()} · {group.total}
							{group.total === 1 ? m.xRaysOccurrence() : m.xRaysOccurrences()}
						</span>
						<div class="flex-1 border-t border-surface-200-800"></div>
					</div>

					{#each group.issues as issue (issue.msgid)}
						<details
							class="group/issue rounded-md border-l-4 {group.border} bg-surface-100-900/40 overflow-hidden"
						>
							<summary
								class="flex items-center gap-2 px-3 py-2 cursor-pointer list-none hover:bg-surface-200-800/40 transition-colors"
							>
								<i
									class="fa-solid fa-chevron-right text-[10px] text-surface-500 transition-transform group-open/issue:rotate-90"
								></i>
								<span class="text-sm font-medium">{safeTranslate(issue.msgid)}</span>
								<span class="ml-auto badge preset-tonal-surface text-xs shrink-0">
									{issue.occurrences.length}
								</span>
							</summary>
							<div class="bg-surface-50-950 px-2 pb-1">
								<IssueTable {issue} />
							</div>
						</details>
					{/each}
				</section>
			{/each}
		</div>
	</details>
{/if}
