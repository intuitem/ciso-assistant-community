<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import IssueTable from './IssueTable.svelte';
	import { occurrenceLabel, type Issue } from './utils';

	interface Props {
		groups: {
			key: string;
			label: () => string;
			border: string;
			text: string;
			icon: string;
			total: number;
			issues: Issue[];
		}[];
	}

	let { groups }: Props = $props();
</script>

<div class="space-y-5">
	{#each groups as group (group.key)}
		<section class="space-y-2">
			<div class="flex items-center gap-2">
				<i class="fa-solid {group.icon} {group.text} text-xs"></i>
				<span class="text-xs font-bold uppercase tracking-wide {group.text}">
					{group.label()}
				</span>
				<span class="text-xs text-surface-700-300">
					{group.issues.length}
					{group.issues.length === 1 ? m.xRaysIssue() : m.xRaysIssues()} · {group.total}
					{group.total === 1 ? m.xRaysOccurrence() : m.xRaysOccurrences()}
				</span>
				<div class="flex-1 border-t border-surface-200-800"></div>
			</div>

			{#each group.issues as issue (issue.msgid)}
				<details class="group/issue border-l-4 {group.border} pl-3">
					<summary
						class="flex items-center gap-2 py-1.5 cursor-pointer list-none hover:text-primary-600-400 transition-colors"
					>
						<i
							class="fa-solid fa-chevron-right text-[10px] text-surface-500 transition-transform group-open/issue:rotate-90"
						></i>
						<span class="text-sm font-medium">{safeTranslate(issue.msgid)}</span>
						<span class="ml-auto text-xs text-surface-700-300 shrink-0 whitespace-nowrap">
							{occurrenceLabel(issue.objType, issue.occurrences.length)}
						</span>
					</summary>
					<div class="pb-2">
						<IssueTable {issue} />
					</div>
				</details>
			{/each}
		</section>
	{/each}
</div>
