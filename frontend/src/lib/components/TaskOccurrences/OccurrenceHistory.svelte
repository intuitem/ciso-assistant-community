<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import { getLocale } from '#paraglide/runtime.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { formatOccurrenceDate as formatDate } from '#lib/utils/taskOccurrences.js';
	import { localIsoDate } from '#lib/utils/control-plan.js';
	import {
		OCCURRENCE_STYLES,
		aggregateStatus,
		countOccurrenceStates,
		isOccurrenceLate,
		occurrenceState,
		type OccurrenceState
	} from '#lib/utils/taskStatus.js';

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
		/** Added to the marked cell's tooltip, to say what the ring means. */
		markedLabel: string | null;
	}

	let { occurrences, markedId, markedLabel }: Props = $props();
	const uid = $props.id();

	// Statuses a real occurrence can hold; '_unset' is an analytics-only bucket.
	const HISTORY_STATUSES = ['pending', 'in_progress', 'completed', 'cancelled'];

	// One row per year and one cell per month, as the control plan draws its
	// calendar: months line up from one year to the next, and the date is on the
	// page instead of behind a hover.
	const MONTHS = Array.from({ length: 12 }, (_, index) => {
		const day = new Date(2000, index, 1);
		return {
			number: String(index + 1).padStart(2, '0'),
			initial: day.toLocaleDateString(getLocale(), { month: 'narrow' }),
			name: day.toLocaleDateString(getLocale(), { month: 'long' })
		};
	});

	// A month's key is 'YYYY-MM'; occurrences without a date go under ''.
	const monthKey = (occurrence: Occurrence) => occurrence.due_date?.slice(0, 7) ?? '';

	function monthLabel(key: string) {
		if (!key) return '--';
		const [year, month] = key.split('-').map(Number);
		const day = new Date(year, month - 1, 1);
		return day.toLocaleDateString(getLocale(), { month: 'long', year: 'numeric' });
	}

	const byMonth = $derived.by(() => {
		const months = new Map<string, Occurrence[]>();
		for (const occurrence of occurrences) {
			const month = monthKey(occurrence);
			if (!months.has(month)) months.set(month, []);
			months.get(month)!.push(occurrence);
		}
		return months;
	});
	const months = $derived([...byMonth.keys()].filter(Boolean).sort());
	const years = $derived([...new Set(months.map((month) => month.slice(0, 4)))]);
	const undated = $derived(byMonth.get('') ?? []);

	// The history runs from its first month to its last. In between, a month
	// without an occurrence is drawn empty; outside, nothing is known of a month
	// and nothing is drawn.
	const isCovered = (month: string) => months[0] < month && month < months[months.length - 1];

	const today = localIsoDate(new Date());
	const thisMonth = today.slice(0, 7);
	// Only a row of the current year can carry today's mark: no row, no mark.
	const showsToday = $derived(years.includes(today.slice(0, 4)));
	const todayLabel = `${m.today()} — ${formatDate(today)}`;

	// A month holding several occurrences cannot lead to one of them: it opens, and
	// its occurrences are listed in a panel under its year. A history without such
	// a month has nothing to open.
	const opens = $derived([...byMonth.values()].some((month) => month.length > 1));

	// The open month starts as the ringed occurrence's. A choice holds while the
	// same occurrence is ringed: on another occurrence's page the history follows
	// that one again. Closing the month is a choice too.
	let choice = $state<{ markedId: string | null; month: string | null } | null>(null);
	const openKey = $derived.by(() => {
		if (choice && choice.markedId === markedId) return choice.month;
		const marked = occurrences.find((occurrence) => occurrence.id === markedId);
		return marked ? monthKey(marked) : null;
	});
	const open = $derived.by(() => {
		const month = openKey === null ? undefined : byMonth.get(openKey);
		return openKey !== null && month && month.length > 1
			? { key: openKey, label: monthLabel(openKey), occurrences: month }
			: null;
	});

	function toggle(month: string) {
		choice = { markedId, month: month === openKey ? null : month };
	}

	const RING = 'ring-2 ring-offset-1 ring-surface-950-50';
	const TODAY_TINT = 'rounded-sm bg-violet-100/60 dark:bg-violet-900/30';

	// The open month and its panel are drawn as one region: one fill, one outline.
	// The outline is what tells the state: the fill alone is too faint for that.
	const REGION = 'border border-surface-600-400 bg-surface-100-900';
	// The tab stands where the cell's padding was (its border and padding add up to
	// it), and runs one pixel into the panel below, over the panel's top border.
	const TAB = `relative z-10 -mb-px rounded-t-sm border-b-0 px-px pt-px pb-[3px] ${REGION}`;

	// The states under the names the legend gives them.
	const stateLabel = (state: OccurrenceState) =>
		state === 'overdue' ? m.overdue() : safeTranslate(state === 'planned' ? 'pending' : state);

	const dayOf = (occurrence: Occurrence) =>
		occurrence.due_date ? String(Number(occurrence.due_date.slice(8, 10))) : '';
</script>

{#snippet square(occurrence: Occurrence, size: string, text: string)}
	<!-- Drawn as the control plan draws its cells: late takes over the status. -->
	{@const late = isOccurrenceLate(occurrence)}
	{@const marked = occurrence.id === markedId}
	{@const title = `${formatDate(occurrence.due_date)} — ${safeTranslate(occurrence.status)}${
		late ? ` · ${m.overdue()}` : ''
	}${marked && markedLabel ? ` (${markedLabel})` : ''}`}
	<!-- A plain link: no breadcrumb is stacked per occurrence opened. -->
	<a
		href="/task-nodes/{occurrence.id}"
		class="flex h-5 items-center justify-center rounded-sm text-[10px] font-semibold text-surface-900-100 {size} {OCCURRENCE_STYLES[
			occurrenceState(occurrence.status, late)
		]} {marked ? RING : ''}"
		{title}
		aria-label={title}
		aria-current={marked ? 'true' : undefined}
		data-late={late ? '' : undefined}>{text}</a
	>
{/snippet}

{#snippet panel(month: { key: string; label: string; occurrences: Occurrence[] })}
	<!-- Under the month's own year: nothing sits between a month and its occurrences. -->
	<tr>
		<td class="p-0"></td>
		<td colspan="12" class="p-0 pb-1">
			<!-- A corner the tab stands on is square. -->
			<div
				id="{uid}-month"
				class="flex flex-wrap items-center gap-1 rounded-sm px-2 py-1.5 text-xs text-surface-600-400 {REGION} {month.key ===
					'' || month.key.endsWith('-01')
					? 'rounded-tl-none'
					: ''} {month.key.endsWith('-12') ? 'rounded-tr-none' : ''}"
				data-testid="occurrence-history-month"
			>
				<span class="me-1">{month.label}</span>
				{#each month.occurrences as occurrence (occurrence.id)}
					{@render square(occurrence, 'w-5 shrink-0', dayOf(occurrence))}
				{/each}
			</div>
		</td>
	</tr>
{/snippet}

{#snippet monthCell(key: string)}
	{@const month = byMonth.get(key) ?? []}
	{#if month.length === 0}
		<div class="h-5 rounded-sm {OCCURRENCE_STYLES.none}"></div>
	{:else if month.length === 1}
		{@render square(month[0], '', '')}
	{:else}
		<!-- Drawn as the control plan draws a cell holding several occurrences. Its
		     tooltip says what the month is made of. -->
		{@const status = aggregateStatus(month.map((occurrence) => occurrence.status))}
		{@const late = month.some(isOccurrenceLate)}
		{@const marked = month.some((occurrence) => occurrence.id === markedId)}
		{@const isOpen = open?.key === key}
		{@const title = `${monthLabel(key)} — ${countOccurrenceStates(month)
			.map(([state, count]) => `${stateLabel(state)} ×${count}`)
			.join(' · ')}${marked && markedLabel ? ` (${markedLabel})` : ''}`}
		<div class={isOpen ? TAB : ''}>
			<!-- While the month is open the ring is on the occurrence itself, in the
			     panel right below: the cell carries it only when closed. -->
			<button
				type="button"
				class="@container flex h-5 w-full cursor-pointer flex-col items-center justify-center gap-px rounded-sm text-surface-900-100 {OCCURRENCE_STYLES[
					occurrenceState(status, late)
				]} {marked && !isOpen ? RING : ''}"
				{title}
				aria-label={title}
				aria-expanded={isOpen}
				aria-controls={isOpen ? `${uid}-month` : undefined}
				data-late={late ? '' : undefined}
				onclick={() => toggle(key)}
			>
				<!-- Shown where it fits: in a narrow panel the tooltip alone carries the
				     count, as in the control plan's compact view. -->
				<span class="hidden text-[10px] leading-none font-semibold @min-[20px]:inline"
					>×{month.length}</span
				>
				<!-- What tells a cell that opens from one that leads to its occurrence:
				     pointing down the month opens below, pointing up it closes. -->
				<span
					class="border-x-[3px] border-t-4 border-x-transparent border-t-current {isOpen
						? 'rotate-180'
						: ''}"
					aria-hidden="true"
				></span>
			</button>
		</div>
	{/if}
{/snippet}

<!-- As wide as it gets: narrower, the cells shrink with their container. -->
<table
	class="w-96 max-w-full table-fixed border-separate border-spacing-0"
	data-testid="occurrence-history"
>
	<thead>
		<tr>
			<td class="w-9 p-0"></td>
			{#each MONTHS as month (month.number)}
				{@const isCurrent = showsToday && thisMonth.endsWith(month.number)}
				<th
					scope="col"
					class="p-0.5 text-center text-[11px] font-normal text-surface-500"
					title={isCurrent ? todayLabel : month.name}
					aria-label={month.name}
					aria-current={isCurrent ? 'date' : undefined}
					data-testid={isCurrent ? 'occurrence-history-today' : undefined}
				>
					<span
						class="block rounded-sm {isCurrent
							? 'bg-violet-600 text-white dark:bg-violet-700'
							: ''}">{month.initial}</span
					>
				</th>
			{/each}
		</tr>
	</thead>
	<tbody>
		{#each years as year (year)}
			<tr>
				<th
					scope="row"
					class="p-0 pt-1 text-left align-top text-xs tabular-nums {thisMonth.startsWith(year)
						? 'font-semibold text-violet-700 dark:text-violet-300'
						: 'font-normal text-surface-600-400'}">{year}</th
				>
				{#each MONTHS as month (month.number)}
					{@const key = `${year}-${month.number}`}
					{@const isOpen = open?.key === key}
					<!-- The open month's tab fills the cell, in place of today's tint. -->
					<td
						class="align-top {isOpen ? 'p-0' : 'p-0.5'} {key === thisMonth && !isOpen
							? TODAY_TINT
							: ''}"
					>
						{#if byMonth.has(key) || isCovered(key)}
							{@render monthCell(key)}
						{/if}
					</td>
				{/each}
			</tr>
			{#if open?.key.startsWith(`${year}-`)}
				{@render panel(open)}
			{/if}
		{/each}
		{#if undated.length}
			<!-- Without a date there is no month to sit under: a row of its own. -->
			<tr>
				<th
					scope="row"
					class="p-0 pt-1 text-left align-top text-xs font-normal text-surface-600-400">--</th
				>
				<td class="align-top {open?.key === '' ? 'p-0' : 'p-0.5'}">{@render monthCell('')}</td>
			</tr>
			{#if open?.key === ''}
				{@render panel(open)}
			{/if}
		{/if}
	</tbody>
</table>
{#if opens && !open}
	<!-- What the carets are for, while no month is open. -->
	<p class="pt-1 text-xs text-surface-500" data-testid="occurrence-history-hint">
		{m.occurrenceHistorySelectMonth()}
	</p>
{/if}
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
	{#if showsToday}
		<span class="flex items-center gap-1.5">
			<span class="inline-block h-3 w-3 rounded-sm bg-violet-600 dark:bg-violet-700"></span>
			{m.today()}
		</span>
	{/if}
</div>
