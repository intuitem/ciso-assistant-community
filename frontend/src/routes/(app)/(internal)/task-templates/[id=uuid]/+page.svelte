<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import CommitmentPanel from '$lib/components/CommitmentPanel/CommitmentPanel.svelte';
	import CommentsPanel from '$lib/components/CommentsPanel/CommentsPanel.svelte';
	import TaskOccurrencesPanel from '$lib/components/TaskOccurrences/TaskOccurrencesPanel.svelte';
	import { page } from '$app/state';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// The commitment lives in its own panel; this model has no detailViewFields, so
	// without this the four raw fields would show up as unlabelled read-only rows.
	const COMMITMENT_FIELDS = [
		'commitment_state',
		'committed_eta',
		'committed_by',
		'commitment_notes'
	];

	const commitmentEnabled = $derived(
		!!page.data?.featureflags?.commitment_management && !data.data.is_recurrent
	);
</script>

<DetailView
	{data}
	exclude={[
		// The occurrences panel now carries the schedule state, so leaving these in
		// the field list would repeat it a column away.
		...(data.data.is_recurrent
			? [
					'observation',
					'status',
					'next_occurrence',
					'next_occurrence_status',
					'last_occurrence_status'
				]
			: ['last_occurrence_status', 'next_occurrence', 'next_occurrence_status', 'task_date']),
		...COMMITMENT_FIELDS
	]}
>
	{#snippet widgets()}
		<div class="flex flex-col gap-4">
			{#if commitmentEnabled}
				<CommitmentPanel urlModel="task-templates" object={data.data} />
			{/if}
			<TaskOccurrencesPanel
				taskTemplateId={data.data.id}
				isRecurrent={data.data.is_recurrent}
				schedule={data.data.schedule}
				past={data.pastOccurrences}
				upcoming={data.upcomingOccurrences}
				upcomingCount={data.upcomingCount}
			/>
		</div>
	{/snippet}
</DetailView>

{#if page.data?.featureflags?.comments}
	<div class="mt-4">
		<CommentsPanel parentType="task_template" parentId={data.data.id} />
	</div>
{/if}
