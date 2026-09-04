<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { taskStatusColor } from '$lib/utils/taskStatus';
	import { scheduleLabel, type TaskSchedule } from '$lib/utils/taskSchedule';

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
		schedule?: TaskSchedule | null;
		past?: Occurrence[];
		upcoming?: Occurrence[];
	}

	let { taskTemplateId, isRecurrent, schedule = null, past = [], upcoming = [] }: Props = $props();

	const cadence = $derived(scheduleLabel(schedule));

	// Statuses a real occurrence can hold; '_unset' is an analytics-only bucket.
	const HISTORY_STATUSES = ['pending', 'in_progress', 'completed', 'cancelled'];

	const byDueDate = (a: Occurrence, b: Occurrence) =>
		(a.due_date ?? '').localeCompare(b.due_date ?? '');

	const sortedPast = $derived([...past].sort(byDueDate));
	const sortedUpcoming = $derived([...upcoming].sort(byDueDate));
	const next = $derived(sortedUpcoming[0]);
	const laterCount = $derived(Math.max(sortedUpcoming.length - 1, 0));

	// Past occurrences alone give no "you are here": the current one is upcoming by
	// definition (due today counts as not yet past), so it was missing from the strip
	// entirely. Showing both makes the row a timeline that runs through today.
	const timeline = $derived([...sortedPast, ...sortedUpcoming]);

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

	// A bare row of squares reads as a shape with no when. Grouping by year puts the
	// date on the page instead of behind a hover, and keeps the strip legible in the
	// narrow widgets column.
	const historyByYear = $derived.by(() => {
		const years = new Map<string, Occurrence[]>();
		for (const occurrence of timeline) {
			const year = occurrence.due_date?.slice(0, 4) ?? '--';
			if (!years.has(year)) years.set(year, []);
			years.get(year)!.push(occurrence);
		}
		return [...years.entries()];
	});

	const dueLabel = $derived.by(() => {
		const days = daysUntil(next?.due_date ?? null);
		if (days === null) return '';
		if (days < 0) return m.overdue();
		if (days === 0) return m.today();
		return m.dueInDays({ count: days });
	});
</script>

<div class="card shadow-lg bg-surface-50-950 p-6 space-y-6">
	{#if !isRecurrent}
		<!-- A one-time task has exactly one occurrence; showing it as a list of one
		     makes the reader look for the others. -->
		{@const only = sortedUpcoming[0] ?? sortedPast[sortedPast.length - 1]}
		<!-- A one-time task has a due date, not a "next" anything, and nothing to
		     list: the eye button below already reaches its single occurrence. -->
		<p class="font-semibold">{m.dueDate()}</p>
		{#if only}
			<div class="flex flex-wrap items-center gap-x-6 gap-y-2">
				<span class="text-2xl font-semibold">{formatDate(only.due_date)}</span>
				<span class="badge preset-tonal inline-flex items-center gap-1.5">
					<span
						class="inline-block h-2 w-2 rounded-full"
						style="background-color: {taskStatusColor(only.status)};"
					></span>
					{safeTranslate(only.status)}
				</span>
				<Anchor
					href="/task-nodes/{only.id}"
					aria-label={m.view()}
					title={m.view()}
					class="btn-icon btn-sm preset-filled-primary-500 ml-auto"
					><i class="fa-solid fa-eye"></i></Anchor
				>
			</div>
		{:else}
			<p class="text-sm text-surface-600-400">{m.noOccurrenceHistory()}</p>
		{/if}
	{:else}
		<div class="space-y-3">
			<div class="flex items-center justify-between gap-4">
				<div>
					<p class="font-semibold">{m.nextOccurrence()}</p>
					{#if cadence}
						<p class="text-sm text-surface-600-400">{cadence}</p>
					{/if}
				</div>
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
					<span class="badge preset-tonal inline-flex items-center gap-1.5">
						<span
							class="inline-block h-2 w-2 rounded-full"
							style="background-color: {taskStatusColor(next.status)};"
						></span>
						{safeTranslate(next.status)}
					</span>
					{#if next.expected_evidence?.length}
						<span class="text-sm text-surface-600-400">
							<i class="fa-solid fa-paperclip mr-1"></i>
							{next.evidence_reviewed?.length ?? 0} / {next.expected_evidence.length}
							{m.expectedEvidence()}
						</span>
					{/if}
					<Anchor
						href="/task-nodes/{next.id}"
						aria-label={m.view()}
						title={m.view()}
						class="btn-icon btn-sm preset-filled-primary-500 ml-auto"
						><i class="fa-solid fa-eye"></i></Anchor
					>
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
			{#if timeline.length}
				<div class="space-y-1">
					{#each historyByYear as [year, occurrences] (year)}
						<div class="flex items-start gap-2">
							<span class="w-9 shrink-0 pt-0.5 text-xs tabular-nums text-surface-600-400"
								>{year}</span
							>
							<div class="flex flex-wrap gap-1">
								{#each occurrences as occurrence (occurrence.id)}
									{@const isCurrent = occurrence.id === next?.id}
									{@const isFuture = !isCurrent && (daysUntil(occurrence.due_date) ?? 0) > 0}
									<Anchor
										href="/task-nodes/{occurrence.id}"
										class="h-5 w-5 rounded-sm {isCurrent
											? 'ring-2 ring-offset-1 ring-surface-950-50'
											: ''} {isFuture ? 'opacity-40' : ''}"
										style="background-color: {taskStatusColor(occurrence.status)};"
										title="{formatDate(occurrence.due_date)} — {safeTranslate(
											occurrence.status
										)}{isCurrent ? ` (${m.nextOccurrence()})` : ''}"
									/>
								{/each}
							</div>
						</div>
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
