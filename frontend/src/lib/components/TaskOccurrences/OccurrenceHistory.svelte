<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import { getLocale } from '#paraglide/runtime.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { daysUntil, formatOccurrenceDate as formatDate } from '#lib/utils/taskOccurrences.js';
	import { localIsoDate } from '#lib/utils/control-plan.js';
	import { OCCURRENCE_STYLES, isOccurrenceLate, occurrenceState } from '#lib/utils/taskStatus.js';

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

	// Squares are occurrences, not days: today sits between two of them, after
	// the last one already due and before the first one still to come. Across a
	// year change, the marker stays on the row of the current year.
	const today = $derived.by((): { before: string } | { after: string } | null => {
		const firstUpcoming = occurrences.findIndex(
			(occurrence) => (daysUntil(occurrence.due_date) ?? 0) > 0
		);
		const upcoming = firstUpcoming === -1 ? undefined : occurrences[firstUpcoming];
		const lastDue = firstUpcoming === -1 ? occurrences.at(-1) : occurrences[firstUpcoming - 1];
		const thisYear = String(new Date().getFullYear());
		const yearOf = (occurrence: Occurrence) => occurrence.due_date?.slice(0, 4);

		// Only a row of the current year can carry it: elsewhere it would mislabel that year.
		if (upcoming && yearOf(upcoming) === thisYear) return { before: upcoming.id };
		if (lastDue && yearOf(lastDue) === thisYear) return { after: lastDue.id };
		return null;
	});
	// Squares are occurrences, not months: naming the first and last month of each
	// row says which part of the year it covers.
	function monthOf(occurrence: Occurrence | undefined) {
		if (!occurrence?.due_date) return '';
		const day = new Date(`${occurrence.due_date.slice(0, 10)}T00:00:00`);
		return day.toLocaleDateString(getLocale(), { month: 'short' });
	}

	const todayLabel = $derived(`${m.today()} — ${formatDate(localIsoDate(new Date()))}`);
</script>

{#snippet todayMarker()}
	<span
		role="img"
		data-testid="occurrence-history-today"
		class="-my-0.5 h-6 w-0.5 shrink-0 rounded-full bg-violet-600 dark:bg-violet-400"
		title={todayLabel}
		aria-label={todayLabel}
	></span>
{/snippet}

<!-- w-fit: rows align within the widest year rather than the panel width. -->
<div class="space-y-1 w-fit max-w-full" data-testid="occurrence-history">
	{#each historyByYear as [year, yearOccurrences] (year)}
		<div class="flex items-start gap-2">
			<span class="w-9 shrink-0 pt-0.5 text-xs tabular-nums text-surface-600-400">{year}</span>
			<span
				class="w-8 shrink-0 pt-0.5 text-right text-[11px] text-surface-500"
				data-testid="occurrence-history-first-month">{monthOf(yearOccurrences[0])}</span
			>
			<div class="flex flex-wrap gap-1">
				{#each yearOccurrences as occurrence (occurrence.id)}
					{@const isMarked = occurrence.id === markedId}
					<!-- Drawn as the control plan draws its cells: late takes over the status. -->
					{@const isLate = isOccurrenceLate(occurrence)}
					{@const state = occurrenceState(occurrence.status, isLate)}
					{@const href = `/task-nodes/${occurrence.id}`}
					{@const squareClass = `h-5 w-5 rounded-sm ${OCCURRENCE_STYLES[state]} ${
						isMarked ? 'ring-2 ring-offset-1 ring-surface-950-50' : ''
					}`}
					{@const title = `${formatDate(occurrence.due_date)} — ${safeTranslate(occurrence.status)}${
						isLate ? ` · ${m.overdue()}` : ''
					}${isMarked && markedLabel ? ` (${markedLabel})` : ''}`}
					{#if today && 'before' in today && today.before === occurrence.id}
						{@render todayMarker()}
					{/if}
					<!-- A plain link: no breadcrumb is stacked per occurrence opened. -->
					<a
						{href}
						class={squareClass}
						{title}
						aria-label={title}
						aria-current={isMarked ? 'true' : undefined}
						data-late={isLate ? '' : undefined}
					></a>
					{#if today && 'after' in today && today.after === occurrence.id}
						{@render todayMarker()}
					{/if}
				{/each}
			</div>
			{#if yearOccurrences.length > 1}
				<span class="shrink-0 pt-0.5 text-[11px] text-surface-500"
					>{monthOf(yearOccurrences.at(-1))}</span
				>
			{/if}
		</div>
	{/each}
</div>
<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-surface-600-400 pt-1">
	{#each HISTORY_STATUSES as status (status)}
		<span class="flex items-center gap-1.5">
			<span
				class="inline-block h-3 w-3 rounded-sm {OCCURRENCE_STYLES[occurrenceState(status, false)]}"
			></span>
			{safeTranslate(status)}
		</span>
	{/each}
	<span class="flex items-center gap-1.5">
		<span class="inline-block h-3 w-3 rounded-sm {OCCURRENCE_STYLES.overdue}"></span>
		{m.overdue()}
	</span>
	{#if today}
		<span class="flex items-center gap-1.5">
			<span class="inline-block h-3 w-0.5 rounded-full bg-violet-600 dark:bg-violet-400"></span>
			{m.today()}
		</span>
	{/if}
</div>
