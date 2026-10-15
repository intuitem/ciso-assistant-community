<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import IssueSections from './IssueSections.svelte';
	import { severityGroups, type SeverityKey } from './utils';

	interface Props {
		assessment: any;
		assessmentType: string;
		activeSeverities: Record<SeverityKey, boolean>;
	}

	let { assessment, assessmentType, activeSeverities }: Props = $props();

	const groups = $derived(
		severityGroups(
			assessment?.quality_check,
			activeSeverities,
			assessmentType,
			assessment.object.id
		)
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
				{assessmentType === 'risk-assessments' ? m.xRaysOpenRiskAssessment() : m.xRaysOpenAudit()}
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

		<div class="bg-surface-50-950 px-4 py-4">
			<IssueSections {groups} />
		</div>
	</details>
{/if}
