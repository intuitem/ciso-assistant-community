<script lang="ts">
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { getLocale } from '#paraglide/runtime.js';
	import { formatDateOrDateTime } from '#lib/utils/datetime.js';
	import { taskStatusColor } from '#lib/utils/taskStatus.js';

	interface Occurrence {
		id: string;
		due_date: string | null;
		status: string;
	}

	interface Props {
		/** Oldest first. */
		occurrences: Occurrence[];
		/** The occurrence to ring: the next one on the task, the viewed one on an occurrence. */
		markedId: string | null;
		/** Added to the marked square's tooltip, to say what the ring means. */
		markedLabel: string | null;
	}

	let { occurrences, markedId, markedLabel }: Props = $props();

	// Statuses a real occurrence can hold; '_unset' is an analytics-only bucket.
	const HISTORY_STATUSES = ['pending', 'in_progress', 'completed', 'cancelled'];

	function formatDate(value: string | null) {
		return formatDateOrDateTime(value, getLocale()) ?? '--';
	}

	function daysUntil(value: string | null) {
		if (!value) return null;
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		// A date-only string is parsed as UTC midnight, which is the previous day in
		// time zones west of UTC; anchoring with a local time keeps the calendar date.
		const due = new Date(value.includes('T') ? value : `${value}T00:00:00`);
		due.setHours(0, 0, 0, 0);
		return Math.round((due.getTime() - today.getTime()) / 86400000);
	}

	// A bare row of squares reads as a shape with no when. Grouping by year puts the
	// date on the page instead of behind a hover, and keeps the strip legible in the
	// narrow widgets column.
	const historyByYear = $derived.by(() => {
		const years = new Map<string, Occurrence[]>();
		for (const occurrence of occurrences) {
			const year = occurrence.due_date?.slice(0, 4) ?? '--';
			if (!years.has(year)) years.set(year, []);
			years.get(year)!.push(occurrence);
		}
		return [...years.entries()];
	});
</script>

<!-- w-fit: rows align within the widest year rather than the panel width. -->
<div class="space-y-1 w-fit max-w-full" data-testid="occurrence-history">
	{#each historyByYear as [year, yearOccurrences], yearIndex (year)}
		<div class="flex items-start gap-2">
			<span class="w-9 shrink-0 pt-0.5 text-xs tabular-nums text-surface-600-400">{year}</span>
			<!-- The window truncates the start of the oldest year, so its squares
			     sit flush right — the tail of that year running into the next row —
			     instead of reading as January-onward. -->
			<div
				class="flex flex-wrap gap-1 grow {yearIndex === 0 && historyByYear.length > 1
					? 'justify-end'
					: ''}"
			>
				{#each yearOccurrences as occurrence (occurrence.id)}
					{@const isMarked = occurrence.id === markedId}
					{@const isFuture = !isMarked && (daysUntil(occurrence.due_date) ?? 0) > 0}
					{@const href = `/task-nodes/${occurrence.id}`}
					{@const squareClass = `h-5 w-5 rounded-sm ${
						isMarked ? 'ring-2 ring-offset-1 ring-surface-950-50' : ''
					} ${isFuture ? 'opacity-40' : ''}`}
					{@const style = `background-color: ${taskStatusColor(occurrence.status)};`}
					{@const title = `${formatDate(occurrence.due_date)} — ${safeTranslate(occurrence.status)}${
						isMarked && markedLabel ? ` (${markedLabel})` : ''
					}`}
					<!-- A plain link: no breadcrumb is stacked per occurrence opened. -->
					<a
						{href}
						class={squareClass}
						{style}
						{title}
						aria-label={title}
						aria-current={isMarked ? 'true' : undefined}
					></a>
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
