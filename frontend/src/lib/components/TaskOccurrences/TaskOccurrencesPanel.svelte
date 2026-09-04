<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { taskStatusColor } from '$lib/utils/taskStatus';

	interface Occurrence {
		id: string;
		due_date: string | null;
		status: string;
		expected_evidence?: { id: string; str: string }[];
		evidence_reviewed?: string[];
	}

	interface Props {
		taskTemplateId: string;
		isRecurrent: boolean;
		past?: Occurrence[];
		upcoming?: Occurrence[];
	}

	let { taskTemplateId, isRecurrent, past = [], upcoming = [] }: Props = $props();

	const toastStore = getToastStore();
	let busy = $state(false);

	// Statuses a real occurrence can hold; '_unset' is an analytics-only bucket.
	const HISTORY_STATUSES = ['pending', 'in_progress', 'completed', 'cancelled'];

	const byDueDate = (a: Occurrence, b: Occurrence) =>
		(a.due_date ?? '').localeCompare(b.due_date ?? '');

	const sortedPast = $derived([...past].sort(byDueDate));
	const sortedUpcoming = $derived([...upcoming].sort(byDueDate));
	const next = $derived(sortedUpcoming[0]);
	const laterCount = $derived(Math.max(sortedUpcoming.length - 1, 0));

	function formatDate(value: string | null) {
		return value ? new Date(value).toLocaleDateString() : '--';
	}

	function daysUntil(value: string | null) {
		if (!value) return null;
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		const due = new Date(value);
		due.setHours(0, 0, 0, 0);
		return Math.round((due.getTime() - today.getTime()) / 86400000);
	}

	const dueLabel = $derived.by(() => {
		const days = daysUntil(next?.due_date ?? null);
		if (days === null) return '';
		if (days < 0) return m.overdue();
		if (days === 0) return m.today();
		return m.dueInDays({ count: days });
	});

	async function markDone(occurrence: Occurrence) {
		busy = true;
		try {
			const response = await fetch('?/setOccurrenceStatus', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', 'x-sveltekit-action': 'true' },
				body: JSON.stringify({ id: occurrence.id, status: 'completed' })
			});
			if (!response.ok) throw new Error(String(response.status));
			toastStore.trigger({ message: m.occurrenceDone(), preset: 'success' });
			await invalidateAll();
		} catch {
			toastStore.trigger({ message: m.occurrenceUpdateFailed(), preset: 'error' });
		} finally {
			busy = false;
		}
	}
</script>

<div class="card shadow-lg bg-surface-50-950 p-6 space-y-6">
	{#if !isRecurrent}
		<!-- A one-time task has exactly one occurrence; showing it as a list of one
		     makes the reader look for the others. -->
		{@const only = sortedUpcoming[0] ?? sortedPast[sortedPast.length - 1]}
		<div class="flex items-center justify-between gap-4">
			<p class="font-semibold">{m.nextOccurrence()}</p>
			{#if only}
				<Anchor href="/task-nodes/{only.id}" class="text-sm anchor">{m.viewAll()}</Anchor>
			{/if}
		</div>
		{#if only}
			<div class="flex flex-wrap items-center gap-x-6 gap-y-2">
				<span class="text-2xl font-semibold">{formatDate(only.due_date)}</span>
				<span class="badge preset-tonal">{safeTranslate(only.status)}</span>
				{#if only.status !== 'completed'}
					<button
						type="button"
						class="btn btn-sm preset-filled-primary-500"
						disabled={busy}
						onclick={() => markDone(only)}
					>
						<i class="fa-solid fa-check mr-1"></i>{m.markAsDone()}
					</button>
				{/if}
			</div>
		{:else}
			<p class="text-sm text-surface-600-400">{m.noOccurrenceHistory()}</p>
		{/if}
	{:else}
		<div class="space-y-3">
			<div class="flex items-center justify-between gap-4">
				<p class="font-semibold">{m.nextOccurrence()}</p>
				<Anchor href="/task-nodes?task_template={taskTemplateId}" class="text-sm anchor"
					>{m.allOccurrences()}</Anchor
				>
			</div>
			{#if next}
				<div class="flex flex-wrap items-center gap-x-6 gap-y-3">
					<div>
						<span class="text-2xl font-semibold">{formatDate(next.due_date)}</span>
						<span class="ml-2 text-sm text-surface-600-400">{dueLabel}</span>
					</div>
					<span class="badge preset-tonal">{safeTranslate(next.status)}</span>
					{#if next.expected_evidence?.length}
						<span class="text-sm text-surface-600-400">
							<i class="fa-solid fa-paperclip mr-1"></i>
							{next.evidence_reviewed?.length ?? 0} / {next.expected_evidence.length}
							{m.expectedEvidence()}
						</span>
					{/if}
					<div class="flex gap-2 ml-auto">
						<button
							type="button"
							class="btn btn-sm preset-filled-primary-500"
							disabled={busy}
							onclick={() => markDone(next)}
						>
							<i class="fa-solid fa-check mr-1"></i>{m.markAsDone()}
						</button>
						<Anchor href="/task-nodes/{next.id}" class="btn btn-sm preset-tonal"
							>{m.details()}</Anchor
						>
					</div>
				</div>
				{#if laterCount > 0}
					<p class="text-sm text-surface-600-400">{m.moreUpcoming({ count: laterCount })}</p>
				{/if}
			{:else}
				<p class="text-sm text-surface-600-400">{m.noDataAvailable()}</p>
			{/if}
		</div>

		<div class="space-y-2">
			<p class="font-semibold">{m.occurrenceHistory()}</p>
			{#if sortedPast.length}
				<div class="flex flex-wrap gap-1">
					{#each sortedPast as occurrence (occurrence.id)}
						<Anchor
							href="/task-nodes/{occurrence.id}"
							class="h-5 w-5 rounded-sm"
							style="background-color: {taskStatusColor(occurrence.status)};"
							title="{formatDate(occurrence.due_date)} — {safeTranslate(occurrence.status)}"
						/>
					{/each}
				</div>
				<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-surface-600-400 pt-1">
					{#each HISTORY_STATUSES as status (status)}
						<span class="flex items-center gap-1.5">
							<span
								class="inline-block h-2.5 w-2.5 rounded-sm"
								style="background-color: {taskStatusColor(status)};"
							></span>
							{safeTranslate(status)}
						</span>
					{/each}
				</div>
			{:else}
				<p class="text-sm text-surface-600-400">{m.noOccurrenceHistory()}</p>
			{/if}
		</div>
	{/if}
</div>
