<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import CommitmentPanel from '$lib/components/CommitmentPanel/CommitmentPanel.svelte';
	import CommentsPanel from '$lib/components/CommentsPanel/CommentsPanel.svelte';
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
	displayModelTable={data.data.is_recurrent}
	exclude={[
		...(data.data.is_recurrent
			? ['observation', 'status']
			: ['last_occurrence_status', 'next_occurrence']),
		...COMMITMENT_FIELDS
	]}
	widgetsEnabled={commitmentEnabled}
>
	{#snippet widgets()}
		{#if commitmentEnabled}
			<CommitmentPanel urlModel="task-templates" object={data.data} />
		{/if}
	{/snippet}
</DetailView>

{#if page.data?.featureflags?.comments}
	<div class="mt-4">
		<CommentsPanel parentType="task_template" parentId={data.data.id} />
	</div>
{/if}
