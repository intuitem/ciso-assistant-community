<script lang="ts">
	import { pageTitle } from '#lib/utils/stores.js';
	import { goto } from '$app/navigation';
	import { onMount, untrack } from 'svelte';
	import { get } from 'svelte/store';
	import { SvelteSet } from 'svelte/reactivity';
	import { m } from '#paraglide/messages.js';
	import { getLocale } from '#paraglide/runtime.js';
	import Anchor from '#lib/components/Anchor/Anchor.svelte';
	import AutocompleteSelect from '#lib/components/Forms/AutocompleteSelect.svelte';
	import FolderTreeSelect from '#lib/components/Forms/FolderTreeSelect.svelte';
	import {
		GROUPINGS,
		OPTIONAL_COLUMNS,
		moveColumn,
		PANE_WIDTH,
		clampPaneWidth,
		defaultViewSettings,
		flattenTasks,
		groupRows,
		isCurrentBucket,
		isOutstanding,
		joinLabels,
		localIsoDate,
		monthBands,
		parseViewSettings,
		sameWindow,
		sortRows,
		yearWindow,
		type Bucket,
		type NamedRef,
		type BucketStatus,
		type Granularity,
		type ColumnId,
		type Grouping,
		type MonthWindow,
		type OptionalColumn,
		type ReviewFolder,
		type SortKey,
		type TaskRow,
		type ViewSettings
	} from '#lib/utils/control-plan.js';
	import { formatDateOrDateTime } from '#lib/utils/datetime.js';
	import { scheduleLabel } from '#lib/utils/taskSchedule.js';
	import {
		OCCURRENCE_STYLES,
		occurrenceState,
		type OccurrenceState
	} from '#lib/utils/taskStatus.js';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { countMasked } from '#lib/utils/related-visibility.js';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	interface Review {
		folders: ReviewFolder[];
		buckets: Bucket[];
		granularity: Granularity;
		/** The day the API worked the overdue flags out for. */
		today?: string;
	}

	let { data }: Props = $props();
	pageTitle.set(m.tasksReview());

	let filtersExpanded = $state(true);
	let outstandingOnly = $state(false);

	// ── View settings ──────────────────────────────────────────────────────
	// How the grid is laid out is a personal preference: it stays in this
	// browser, while the filters travel in the URL.

	const VIEW_STORAGE_KEY = 'controlPlanView';

	let view: ViewSettings = $state(defaultViewSettings());

	// Read after hydration, so the server and the first client render agree.
	// Storage can be unavailable (blocked, private window, full): the view then
	// keeps its defaults, or its changes for as long as the page stays open.
	onMount(() => {
		try {
			view = parseViewSettings(localStorage.getItem(VIEW_STORAGE_KEY));
		} catch {
			// Defaults stay.
		}
	});

	function saveView() {
		try {
			localStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify(view));
		} catch {
			// Not remembered, still applied.
		}
	}

	function updateView(patch: Partial<ViewSettings>) {
		view = { ...view, ...patch };
		saveView();
	}

	function toggleSort(key: SortKey) {
		const descending = view.sort.key === key ? !view.sort.descending : false;
		updateView({ sort: { key, descending } });
	}

	function toggleColumn(column: OptionalColumn) {
		const shown = new Set(view.columns);
		if (shown.has(column)) shown.delete(column);
		else shown.add(column);
		updateView({ columns: OPTIONAL_COLUMNS.filter((name) => shown.has(name)) });
	}

	const GROUPING_LABELS: Record<Grouping, () => string> = {
		none: m.controlPlanNoGrouping,
		domain: m.domain,
		frequency: m.frequency,
		assignee: m.assignedTo
	};

	interface Column {
		id: ColumnId;
		sortKey: SortKey;
		label: () => string;
		/**
		 * Grid track: free text shares the room, short values are capped. The name
		 * keeps a floor, so a narrow pane squeezes the other columns first.
		 */
		track: string;
	}

	const COLUMNS: Record<ColumnId, Omit<Column, 'id'>> = {
		ref: { sortKey: 'ref', label: m.refId, track: 'minmax(0, 64px)' },
		name: { sortKey: 'name', label: m.name, track: 'minmax(120px, 3fr)' },
		frequency: { sortKey: 'frequency', label: m.frequency, track: 'minmax(0, 100px)' },
		assignee: { sortKey: 'assignee', label: m.assignedTo, track: 'minmax(0, 1.5fr)' },
		appliedControl: {
			sortKey: 'appliedControl',
			label: m.appliedControl,
			track: 'minmax(0, 2fr)'
		},
		nextDue: { sortKey: 'nextDue', label: m.nextOccurrence, track: 'minmax(0, 88px)' },
		domain: { sortKey: 'domain', label: m.domain, track: 'minmax(0, 1.5fr)' }
	};

	// Every column, shown or not, in the order the user gave them.
	const orderedColumns: Column[] = $derived(view.columnOrder.map((id) => ({ id, ...COLUMNS[id] })));

	function resetColumns() {
		const { columns, columnOrder } = defaultViewSettings();
		updateView({ columns, columnOrder });
	}

	// Reordering: drag a header onto another one to take its place. Pointer
	// events rather than native drag and drop, which buttons do not all support.
	let columnDrag: { column: ColumnId; target: ColumnId | null } | null = $state(null);
	// The click that ends a drag must not sort.
	let columnDragEnded = false;

	function startColumnDrag(event: PointerEvent, column: ColumnId) {
		if (event.button !== 0) return;
		const header = event.currentTarget as HTMLElement;
		const headers = header.parentElement as HTMLElement;
		const startX = event.clientX;
		header.setPointerCapture(event.pointerId);

		const move = (moveEvent: PointerEvent) => {
			// A few pixels of slack: a click is not a drag.
			if (!columnDrag && Math.abs(moveEvent.clientX - startX) < 5) return;
			const candidates = [...headers.querySelectorAll<HTMLElement>('[data-column]')];
			// The gap between two headers belongs to the one on its right.
			const over =
				candidates.find((el) => moveEvent.clientX <= el.getBoundingClientRect().right) ??
				candidates.at(-1);
			const target = over?.dataset.column as ColumnId | undefined;
			columnDrag = { column, target: target && target !== column ? target : null };
		};
		const release = () => {
			header.removeEventListener('pointermove', move);
			header.removeEventListener('pointerup', drop);
			header.removeEventListener('pointercancel', release);
			if (columnDrag) {
				columnDragEnded = true;
				setTimeout(() => (columnDragEnded = false));
			}
			columnDrag = null;
		};
		const drop = () => {
			const target = columnDrag?.target;
			if (target) updateView({ columnOrder: moveColumn(view.columnOrder, column, target) });
			release();
		};
		header.addEventListener('pointermove', move);
		header.addEventListener('pointerup', drop);
		header.addEventListener('pointercancel', release);
	}
	// Checkbox menus (columns, statuses): one open at a time, closed by a click
	// elsewhere or Escape.
	type Menu = 'columns' | 'statuses';
	let openMenu: Menu | null = $state(null);

	function toggleMenu(menu: Menu) {
		openMenu = openMenu === menu ? null : menu;
	}

	function closeMenu(event: Event) {
		if (!openMenu) return;
		const inside = (event.target as Element | null)?.closest?.(`[data-menu="${openMenu}"]`);
		if (!inside || (event instanceof KeyboardEvent && event.key === 'Escape')) {
			openMenu = null;
		}
	}
	// Collapsed groups, keyed by grouping so each grouping remembers its own.
	const collapsedGroups = new SvelteSet<string>();

	function toggleGroup(id: string) {
		if (collapsedGroups.has(id)) collapsedGroups.delete(id);
		else collapsedGroups.add(id);
	}

	// Task pane resizing: drag the handle on its right edge.
	let containerWidth = $state(0);
	// Always leave some of the calendar visible, whatever the stored width.
	const paneWidth = $derived(
		containerWidth
			? Math.max(PANE_WIDTH.min, Math.min(view.paneWidth, containerWidth - 160))
			: view.paneWidth
	);

	function startResize(event: PointerEvent) {
		const handle = event.currentTarget as HTMLElement;
		const startX = event.clientX;
		const startWidth = paneWidth;
		handle.setPointerCapture(event.pointerId);
		event.preventDefault();

		const move = (moveEvent: PointerEvent) => {
			view = { ...view, paneWidth: clampPaneWidth(startWidth + moveEvent.clientX - startX) };
		};
		const stop = () => {
			handle.removeEventListener('pointermove', move);
			handle.removeEventListener('pointerup', stop);
			handle.removeEventListener('pointercancel', stop);
			saveView();
		};
		handle.addEventListener('pointermove', move);
		handle.addEventListener('pointerup', stop);
		handle.addEventListener('pointercancel', stop);
	}

	function resizeWithKeyboard(event: KeyboardEvent) {
		const step = { ArrowLeft: -16, ArrowRight: 16 }[event.key];
		if (!step) return;
		event.preventDefault();
		updateView({ paneWidth: clampPaneWidth(paneWidth + step) });
	}

	const now = new Date();
	const currentYear = now.getFullYear();

	function getMonthName(monthIndex: number): string {
		const monthNames = [
			m.januaryShort(),
			m.februaryShort(),
			m.marchShort(),
			m.aprilShort(),
			m.mayShort(),
			m.juneShort(),
			m.julyShort(),
			m.augustShort(),
			m.septemberShort(),
			m.octoberShort(),
			m.novemberShort(),
			m.decemberShort()
		];
		return monthNames[monthIndex];
	}

	function toMonthFormat(year: number, month: number): string {
		return `${year}-${String(month).padStart(2, '0')}`;
	}

	function parseMonthFormat(value: string): { year: number; month: number } | null {
		if (!value || !value.includes('-')) return null;
		const [year, month] = value.split('-').map(Number);
		if (
			!year ||
			!month ||
			isNaN(year) ||
			isNaN(month) ||
			month < 1 ||
			month > 12 ||
			year < 1900 ||
			year > 2100
		) {
			return null;
		}
		return { year, month };
	}

	function getBucketLabel(bucket: Bucket, granularity: Granularity): string {
		const suffix = bucket.key.split('-')[1];
		if (granularity === 'monthly') return getMonthName(parseInt(suffix) - 1);
		if (granularity === 'quarterly') return m.controlPlanQuarterLabel({ number: suffix.slice(1) });
		if (granularity === 'semiannual')
			return m.controlPlanSemesterLabel({ number: suffix.slice(1) });
		// Weekly: the month row above carries the context, the week number is enough.
		return String(parseInt(suffix.slice(1)));
	}

	const GRANULARITY_LABELS: Record<Granularity, () => string> = {
		monthly: m.monthly,
		weekly: m.weekly,
		quarterly: m.quarterly,
		semiannual: m.semiannual
	};

	// ── Filters ────────────────────────────────────────────────────────────
	// The URL is the single source of truth: every control reads from `data`
	// and writes by navigating, so a change applies at once and stays shareable.

	interface Filters {
		/** null follows today with the rolling window; otherwise an explicit range. */
		period: MonthWindow | null;
		granularity: Granularity;
		folder: string;
		/** Whether the selected domain also covers its sub-domains. */
		include_subfolders: boolean;
		assigned_to: string;
		applied_controls: string;
		/** Empty means every status. */
		statuses: string[];
	}
	type ScalarFilter = Exclude<keyof Filters, 'period' | 'statuses' | 'include_subfolders'>;

	const shownWindow: MonthWindow = $derived({
		startYear: data.startYear,
		startMonth: data.startMonth,
		endYear: data.endYear,
		endMonth: data.endMonth
	});

	const urlFilters: Filters = $derived({
		period: data.rolling ? null : shownWindow,
		granularity: data.selectedGranularity,
		folder: data.selectedFolder,
		include_subfolders: data.includeSubfolders,
		assigned_to: data.selectedAssignedTo,
		applied_controls: data.selectedAppliedControls,
		statuses: data.selectedStatuses
	});

	// A change is shown at once and the next one builds on it: two statuses
	// ticked in quick succession would otherwise both start from the URL as it
	// was, and the second would undo the first.
	let pendingFilters = $state.raw<Filters | null>(null);
	const filters: Filters = $derived(pendingFilters ?? urlFilters);

	function buildUrl(next: Filters): string {
		const params = new URLSearchParams();
		if (next.period) {
			params.set('start_month', next.period.startMonth.toString());
			params.set('start_year', next.period.startYear.toString());
			params.set('end_month', next.period.endMonth.toString());
			params.set('end_year', next.period.endYear.toString());
		}
		if (next.granularity !== 'monthly') params.set('granularity', next.granularity);
		if (next.folder) params.set('folder', next.folder);
		// Sub-domains are the default: only the opt-out is carried.
		if (!next.include_subfolders) params.set('include_subfolders', 'false');
		if (next.assigned_to) params.set('assigned_to', next.assigned_to);
		if (next.applied_controls) params.set('applied_controls', next.applied_controls);
		for (const status of next.statuses) params.append('status', status);
		const query = params.toString();
		return query ? `/tasks-review?${query}` : '/tasks-review';
	}

	function applyFilters(next: Filters) {
		pendingFilters = next;
		// Stay where we are: same history entry, same scroll position, same focus.
		goto(buildUrl(next), { replace: true, reset: false })
			.catch(() => {})
			.finally(() => {
				// The URL has caught up, unless a later change took over meanwhile.
				if (pendingFilters === next) pendingFilters = null;
			});
	}

	function setFilter(name: ScalarFilter, value: string) {
		if (filters[name] === value) return;
		applyFilters({ ...filters, [name]: value });
	}

	const STATUS_OPTIONS = [
		{ value: 'overdue', label: m.overdue },
		{ value: 'completed', label: m.completed },
		{ value: 'in_progress', label: m.inProgress },
		{ value: 'pending', label: m.pending },
		{ value: 'cancelled', label: m.cancelled }
	] as const;

	function toggleStatus(status: string) {
		const selected = new Set(filters.statuses);
		if (selected.has(status)) selected.delete(status);
		else selected.add(status);
		applyFilters({
			...filters,
			statuses: STATUS_OPTIONS.map((option) => option.value).filter((value) => selected.has(value))
		});
	}

	const statusSummary = $derived(
		filters.statuses.length === 0
			? m.allStatuses()
			: STATUS_OPTIONS.filter((option) => filters.statuses.includes(option.value))
					.map((option) => option.label())
					.join(', ')
	);

	function setPeriod(period: MonthWindow | null) {
		applyFilters({ ...filters, period });
	}

	function setPeriodBound(bound: 'start' | 'end', value: string) {
		const parsed = parseMonthFormat(value);
		if (!parsed) return;
		const period = { ...(filters.period ?? shownWindow) };
		if (bound === 'start') {
			period.startYear = parsed.year;
			period.startMonth = parsed.month;
		} else {
			period.endYear = parsed.year;
			period.endMonth = parsed.month;
		}
		// Keep the range ordered: a bound moved past the other one takes it along.
		const startIndex = period.startYear * 12 + period.startMonth;
		const endIndex = period.endYear * 12 + period.endMonth;
		if (startIndex > endIndex) {
			if (bound === 'start') {
				period.endYear = period.startYear;
				period.endMonth = period.startMonth;
			} else {
				period.startYear = period.endYear;
				period.startMonth = period.endMonth;
			}
		}
		setPeriod(period);
	}

	const PERIOD_PRESETS = [
		{ id: 'rolling', label: m.controlPlanRolling, period: () => null },
		{ id: 'thisYear', label: m.controlPlanThisYear, period: () => yearWindow(currentYear) },
		{ id: 'lastYear', label: m.controlPlanLastYear, period: () => yearWindow(currentYear - 1) }
	] as const;

	const activePreset = $derived.by(() => {
		if (data.rolling) return 'rolling';
		if (sameWindow(shownWindow, yearWindow(currentYear))) return 'thisYear';
		if (sameWindow(shownWindow, yearWindow(currentYear - 1))) return 'lastYear';
		return null;
	});

	// The pickers that load their own options are form components: the domain
	// tree (as in focus mode) and the applied controls, searched server-side
	// instead of fetching the whole collection up front.
	const pickerFilterSchema = z.object({
		domain: z.string().optional().nullable(),
		applied_controls: z.array(z.string()).optional().nullable()
	});
	const pickerFilterForm = superForm(
		defaults(
			{
				domain: data.selectedFolder || null,
				applied_controls: data.selectedAppliedControls ? [data.selectedAppliedControls] : []
			},
			zod(pickerFilterSchema)
		),
		{
			SPA: true,
			validators: zod(pickerFilterSchema),
			dataType: 'json',
			invalidateAll: false,
			applyAction: false,
			resetForm: false,
			taintedMessage: false,
			validationMethod: 'auto'
		}
	);

	// The pickers hold their own value. When the URL changes behind their back
	// (the sidebar link back to the unfiltered plan, say), bring them in line.
	// The applied control picker reads its value when it mounts, so it is
	// remounted when its value had to be corrected.
	let pickerEpoch = $state(0);
	$effect(() => {
		const domain = data.selectedFolder || null;
		const appliedControl = data.selectedAppliedControls;
		untrack(() => {
			const current = get(pickerFilterForm.form);
			const domainMoved = (current.domain || null) !== domain;
			const controlMoved = (current.applied_controls?.[0] ?? '') !== appliedControl;
			if (!domainMoved && !controlMoved) return;
			pickerFilterForm.form.update(
				(formData) => {
					formData.domain = domain;
					formData.applied_controls = appliedControl ? [appliedControl] : [];
					return formData;
				},
				{ taint: false }
			);
			if (controlMoved) pickerEpoch += 1;
		});
	});

	function resetFilters() {
		pickerFilterForm.form.update((formData) => {
			formData.domain = null;
			formData.applied_controls = [];
			return formData;
		});
		outstandingOnly = false;
		pendingFilters = null;
		goto('/tasks-review', { replace: true, reset: false });
	}

	let activeFilterCount = $derived(
		[
			filters.folder,
			filters.assigned_to,
			filters.applied_controls,
			filters.statuses.length > 0
		].filter(Boolean).length
	);

	// ── Review data ────────────────────────────────────────────────────────
	// Keep showing the last result while the next one loads, so changing a
	// filter does not blank the table.

	let review = $state.raw<Review | null>(null);
	let loading = $state(true);

	$effect(() => {
		const pending = data.reviewData as Promise<Review>;
		let stale = false;
		loading = true;
		pending.then((result) => {
			if (stale) return;
			review = result;
			loading = false;
		});
		return () => {
			stale = true;
		};
	});

	const buckets = $derived(review?.buckets ?? []);
	const granularity: Granularity = $derived(review?.granularity ?? 'monthly');
	// The API's day, so the current period and what is outstanding agree with its
	// overdue flags when the browser and the server are on either side of midnight.
	const today = $derived(review?.today ?? localIsoDate(now));
	const currentBucketKey = $derived(
		buckets.find((bucket) => isCurrentBucket(bucket, today))?.key ?? null
	);
	const showBucketYear = $derived(
		granularity === 'quarterly' ||
			granularity === 'semiannual' ||
			(granularity === 'monthly' && (buckets.length > 12 || data.startYear !== data.endYear))
	);
	// Re-centre on the current period only when the time axis itself changes.
	const axisKey = $derived(`${granularity}:${buckets[0]?.key}:${buckets[buckets.length - 1]?.key}`);

	const allRows = $derived(flattenTasks(review?.folders ?? []));
	const outstandingRows = $derived(
		allRows.filter((row) => isOutstanding(row.task, currentBucketKey))
	);
	const outstandingCount = $derived(outstandingRows.length);

	const rows = $derived(sortRows(outstandingOnly ? outstandingRows : allRows, view.sort));
	const groups = $derived(
		groupRows(rows, view.grouping, { unassigned: m.unassigned(), frequency: scheduleLabel })
	);

	const hasRefs = $derived(allRows.some((row) => row.task.ref_id));
	const visibleColumns = $derived(
		orderedColumns.filter((column) => {
			if (column.id === 'name') return true;
			if (!view.columns.includes(column.id)) return false;
			// Nothing to show: no task has a reference, or the group header says it already.
			if (column.id === 'ref') return hasRefs;
			if (column.id === 'domain' || column.id === 'frequency') return view.grouping !== column.id;
			return true;
		})
	);
	const gridTemplate = $derived(visibleColumns.map((column) => column.track).join(' '));

	// Period columns share the room left by the task pane, down to a minimum
	// width below which the calendar scrolls sideways instead.
	const PERIOD_MIN_WIDTH: Record<Granularity, { detailed: number; compact: number }> = {
		weekly: { detailed: 30, compact: 22 },
		monthly: { detailed: 40, compact: 28 },
		quarterly: { detailed: 56, compact: 40 },
		semiannual: { detailed: 56, compact: 40 }
	};
	const periodMinWidth = $derived(
		PERIOD_MIN_WIDTH[granularity][view.compact ? 'compact' : 'detailed']
	);
	const tableMinWidth = $derived(paneWidth + buckets.length * periodMinWidth);

	/** The linked objects the user can see, then how many they cannot. */
	function linkedLabels(refs: NamedRef[] | undefined): string {
		const hidden = countMasked(refs ?? []);
		const note = hidden ? m.objectsNotVisible({ count: hidden }) : '';
		return [joinLabels(refs), note].filter(Boolean).join(' · ');
	}

	function cellValue(column: OptionalColumn, row: TaskRow): string {
		switch (column) {
			case 'ref':
				return row.task.ref_id ?? '';
			case 'frequency':
				return scheduleLabel(row.task.schedule) ?? '';
			case 'assignee':
				return linkedLabels(row.task.assigned_to);
			case 'appliedControl':
				return linkedLabels(row.task.applied_controls);
			case 'nextDue':
				return formatDateOrDateTime(row.task.next_occurrence ?? null, getLocale()) ?? '';
			case 'domain':
				return row.folderName;
		}
	}

	const CELL_LABELS: Record<OccurrenceState, () => string> = {
		none: m.noData,
		completed: m.completed,
		in_progress: m.inProgress,
		planned: m.planned,
		overdue: m.overdue,
		cancelled: m.cancelled
	};

	function cellState(bucket: BucketStatus | undefined): OccurrenceState {
		return occurrenceState(bucket?.status, bucket?.overdue === true);
	}

	/** Bring the current period into view when the table scrolls sideways. */
	function scrollToCurrentPeriod(node: HTMLElement, _axisKey: string) {
		const run = () => {
			const current = node.querySelector<HTMLElement>('th[data-current-period]');
			if (!current) return;
			const pinned = node.querySelector<HTMLElement>('th[data-task-header]')?.offsetWidth ?? 0;
			const room = node.clientWidth - pinned - current.offsetWidth;
			node.scrollLeft = Math.max(0, current.offsetLeft - pinned - room / 2);
		};
		run();
		return { update: run };
	}
</script>

<svelte:window
	onclick={closeMenu}
	onkeydown={(event) => event.key === 'Escape' && closeMenu(event)}
/>

{#snippet taskHeader(rowspan: number)}
	<th
		data-task-header
		{rowspan}
		class="sticky left-0 z-30 p-0 align-bottom bg-surface-50-950 border-b border-r border-surface-200-800"
	>
		<div
			class="grid items-center gap-x-2 px-3 {view.compact ? 'py-1' : 'py-2.5'}"
			class:cursor-grabbing={columnDrag}
			style:grid-template-columns={gridTemplate}
		>
			{#each visibleColumns as column, index (column.id)}
				{@const sorted = view.sort.key === column.sortKey}
				{@const dragged = columnDrag?.column === column.id}
				{@const landing = columnDrag?.target === column.id}
				{@const draggedIndex = visibleColumns.findIndex((other) => other.id === columnDrag?.column)}
				<button
					type="button"
					data-testid="control-plan-sort-{column.id}"
					data-column={column.id}
					class="relative flex items-center gap-1 min-w-0 text-left text-[11px] font-semibold uppercase tracking-wider transition-colors hover:text-violet-700
						{sorted ? 'text-violet-700' : 'text-surface-500'}
						{columnDrag ? 'cursor-grabbing' : ''}
						{dragged ? 'opacity-40' : ''}"
					title="{m.sortBy()} {column.label()} · {m.dragToReorder()}"
					onpointerdown={(event) => startColumnDrag(event, column.id)}
					onclick={() => {
						if (!columnDragEnded) toggleSort(column.sortKey);
					}}
				>
					<span class="truncate">{column.label()}</span>
					{#if sorted}
						<i class="fa-solid {view.sort.descending ? 'fa-arrow-down' : 'fa-arrow-up'} text-[9px]"
						></i>
					{/if}
					{#if landing}
						<!-- Where the dragged column will land: on the far side of this one -->
						<span
							data-testid="control-plan-column-landing"
							class="absolute -inset-y-1 w-0.5 rounded bg-violet-500
								{index > draggedIndex ? '-right-1' : '-left-1'}"
						></span>
					{/if}
				</button>
			{/each}
		</div>
		<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
		<div
			role="separator"
			aria-orientation="vertical"
			aria-label={m.controlPlanResizeTaskPane()}
			aria-valuemin={PANE_WIDTH.min}
			aria-valuemax={PANE_WIDTH.max}
			aria-valuenow={paneWidth}
			tabindex="0"
			data-testid="control-plan-pane-resizer"
			title={m.controlPlanResizeTaskPane()}
			class="absolute inset-y-0 -right-1 w-2 cursor-col-resize touch-none transition-colors hover:bg-violet-400/60 focus-visible:bg-violet-400/60 focus:outline-none"
			onpointerdown={startResize}
			ondblclick={() => updateView({ paneWidth: PANE_WIDTH.initial })}
			onkeydown={resizeWithKeyboard}
		></div>
	</th>
{/snippet}

<div class="space-y-5 p-6">
	<!-- Header bar -->
	<div class="flex flex-wrap items-start justify-between gap-4">
		<div class="flex flex-wrap items-center gap-2">
			<div
				class="flex items-center gap-2 bg-surface-50-950/90 border border-surface-200-800 rounded-lg px-3 py-1.5 shadow-sm"
			>
				<span class="text-sm font-semibold text-surface-800-200">
					{getMonthName(data.startMonth - 1)}
					{data.startYear}
				</span>
				<i class="fa-solid fa-arrow-right text-[10px] text-surface-500"></i>
				<span class="text-sm font-semibold text-surface-800-200">
					{getMonthName(data.endMonth - 1)}
					{data.endYear}
				</span>
				{#if filters.granularity !== 'monthly'}
					<span
						class="inline-flex items-center text-[10px] font-bold uppercase tracking-wider bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded"
						>{GRANULARITY_LABELS[filters.granularity]()}</span
					>
				{/if}
			</div>
			<div
				class="inline-flex rounded-lg border border-surface-200-800 overflow-hidden shadow-sm"
				role="group"
				aria-label={m.previewPeriod()}
			>
				{#each PERIOD_PRESETS as preset (preset.id)}
					<button
						type="button"
						data-testid="control-plan-preset-{preset.id}"
						aria-pressed={activePreset === preset.id}
						class="px-3 py-1.5 text-xs font-medium border-l first:border-l-0 border-surface-200-800 transition-colors duration-150
							{activePreset === preset.id
							? 'bg-violet-50 text-violet-700'
							: 'bg-surface-50-950 text-surface-600-400 hover:text-violet-700'}"
						onclick={() => setPeriod(preset.period())}
					>
						{preset.label()}
					</button>
				{/each}
			</div>
			{#if loading && review}
				<i class="fa-solid fa-spinner fa-spin text-xs text-surface-500" aria-label={m.loading()}
				></i>
			{/if}
		</div>
		<div class="flex flex-wrap items-center gap-2">
			<label
				class="flex items-center gap-1.5 pl-3 text-xs font-medium rounded-lg border border-surface-200-800 bg-surface-50-950 text-surface-600-400"
			>
				<i class="fa-solid fa-layer-group text-[10px]"></i>
				<span>{m.controlPlanGroupBy()}</span>
				<select
					data-testid="control-plan-group-by"
					value={view.grouping}
					onchange={(event) => updateView({ grouping: event.currentTarget.value as Grouping })}
					class="py-1.5 pl-1 pr-7 text-xs font-semibold border-0 rounded-lg bg-transparent text-surface-800-200 focus:outline-none focus:ring-2 focus:ring-violet-400"
				>
					{#each GROUPINGS as grouping (grouping)}
						<option value={grouping}>{GROUPING_LABELS[grouping]()}</option>
					{/each}
				</select>
			</label>
			<div class="relative" data-menu="columns">
				<button
					type="button"
					data-testid="control-plan-columns-toggle"
					aria-haspopup="true"
					aria-expanded={openMenu === 'columns'}
					class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150
						{openMenu === 'columns'
						? 'bg-violet-50 border-violet-300 text-violet-700'
						: 'bg-surface-50-950 border-surface-200-800 text-surface-600-400 hover:border-surface-300-700'}"
					title={m.showHideColumns()}
					onclick={() => toggleMenu('columns')}
				>
					<i class="fa-solid fa-table-columns text-[10px]"></i>
					<span>{m.controlPlanColumns()}</span>
				</button>
				{#if openMenu === 'columns'}
					<div
						class="absolute right-0 top-full z-40 mt-1 min-w-52 p-1.5 rounded-lg border border-surface-200-800 bg-surface-50-950 shadow-lg"
					>
						{#each orderedColumns as column, index (column.id)}
							{@const id = column.id}
							<div class="flex items-center rounded hover:bg-surface-100-900">
								<label
									class="flex flex-1 items-center gap-2 px-2 py-1.5 text-xs text-surface-800-200
										{id === 'name' ? '' : 'cursor-pointer'}"
								>
									<!-- The name is what a row is: it moves, it does not hide -->
									<input
										type="checkbox"
										class="checkbox"
										data-testid="control-plan-column-{id}"
										checked={id === 'name' || view.columns.includes(id)}
										disabled={id === 'name'}
										onchange={() => id !== 'name' && toggleColumn(id)}
									/>
									{column.label()}
								</label>
								{#each [{ step: -1, label: m.moveUp(), icon: 'fa-chevron-up', testid: 'up' }, { step: 1, label: m.moveDown(), icon: 'fa-chevron-down', testid: 'down' }] as move (move.step)}
									{@const neighbour = orderedColumns[index + move.step]}
									<button
										type="button"
										data-testid="control-plan-column-{id}-{move.testid}"
										class="px-1.5 py-1.5 text-[9px] text-surface-500 transition-colors hover:text-violet-700 disabled:opacity-30 disabled:hover:text-surface-500"
										title={move.label}
										aria-label="{move.label} · {column.label()}"
										disabled={!neighbour}
										onclick={() =>
											neighbour &&
											updateView({
												columnOrder: moveColumn(view.columnOrder, id, neighbour.id)
											})}
									>
										<i class="fa-solid {move.icon}"></i>
									</button>
								{/each}
							</div>
						{/each}
						<button
							type="button"
							data-testid="control-plan-columns-reset"
							class="mt-1 w-full border-t border-surface-200-800 px-2 pt-2 pb-1 text-left text-xs text-surface-600-400 transition-colors hover:text-violet-700"
							onclick={resetColumns}
						>
							<i class="fa-solid fa-rotate-left mr-1 text-[10px]"></i>
							{m.resetToDefault()}
						</button>
					</div>
				{/if}
			</div>
			<button
				type="button"
				data-testid="control-plan-outstanding-toggle"
				aria-pressed={outstandingOnly}
				class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150
					{outstandingOnly
					? 'bg-red-50 border-red-300 text-red-700'
					: 'bg-surface-50-950 border-surface-200-800 text-surface-600-400 hover:bg-surface-50-950 hover:border-surface-300-700'}"
				onclick={() => (outstandingOnly = !outstandingOnly)}
			>
				<i class="fa-solid fa-triangle-exclamation text-[10px]"></i>
				<span>{m.controlPlanOutstanding()}</span>
				{#if outstandingCount > 0}
					<span
						class="inline-flex items-center justify-center min-w-4 h-4 px-1 text-[9px] font-bold rounded-full bg-red-600 text-white"
						>{outstandingCount}</span
					>
				{/if}
			</button>
			<button
				type="button"
				data-testid="control-plan-compact-toggle"
				aria-pressed={view.compact}
				class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150
					{view.compact
					? 'bg-violet-50 border-violet-300 text-violet-700'
					: 'bg-surface-50-950 border-surface-200-800 text-surface-600-400 hover:bg-surface-50-950 hover:border-surface-300-700'}"
				onclick={() => updateView({ compact: !view.compact })}
			>
				<!-- A toggle like its neighbours: the label names the mode, the highlight says it is on -->
				<i class="fa-solid fa-compress text-[10px]"></i>
				<span>{m.compactView()}</span>
			</button>
			<button
				type="button"
				class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150
					{filtersExpanded
					? 'bg-violet-50 border-violet-300 text-violet-700'
					: 'bg-surface-50-950 border-surface-200-800 text-surface-600-400 hover:bg-surface-50-950 hover:border-surface-300-700'}"
				onclick={() => (filtersExpanded = !filtersExpanded)}
			>
				<i class="fa-solid fa-sliders text-[10px]"></i>
				<span>{m.filters()}</span>
				{#if activeFilterCount > 0}
					<span
						class="inline-flex items-center justify-center w-4 h-4 text-[9px] font-bold rounded-full bg-violet-600 dark:bg-violet-700 text-white"
						>{activeFilterCount}</span
					>
				{/if}
			</button>
		</div>
	</div>

	<!-- Collapsible filters: each one applies as soon as it changes -->
	{#if filtersExpanded}
		<div
			class="bg-surface-50-950/80 border border-surface-200-800 rounded-xl p-4 transition-all duration-200"
		>
			<div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-10 gap-3 items-end">
				<div>
					<label
						for="start-period-filter"
						class="block text-[11px] font-semibold uppercase tracking-wider text-surface-500 mb-1"
						>{m.startPeriod()}</label
					>
					<input
						id="start-period-filter"
						type="month"
						value={toMonthFormat(data.startYear, data.startMonth)}
						onchange={(event) => setPeriodBound('start', event.currentTarget.value)}
						class="w-full px-2.5 py-1.5 text-sm border border-surface-200-800 rounded-lg bg-surface-50-950 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
					/>
				</div>
				<div>
					<label
						for="end-period-filter"
						class="block text-[11px] font-semibold uppercase tracking-wider text-surface-500 mb-1"
						>{m.endPeriod()}</label
					>
					<input
						id="end-period-filter"
						type="month"
						value={toMonthFormat(data.endYear, data.endMonth)}
						onchange={(event) => setPeriodBound('end', event.currentTarget.value)}
						class="w-full px-2.5 py-1.5 text-sm border border-surface-200-800 rounded-lg bg-surface-50-950 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
					/>
				</div>
				<div>
					<label
						for="granularity-filter"
						class="block text-[11px] font-semibold uppercase tracking-wider text-surface-500 mb-1"
						>{m.granularity()}</label
					>
					<select
						id="granularity-filter"
						value={filters.granularity}
						onchange={(event) => setFilter('granularity', event.currentTarget.value)}
						class="w-full px-2.5 py-1.5 text-sm border border-surface-200-800 rounded-lg bg-surface-50-950 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
					>
						<option value="weekly">{m.weekly()}</option>
						<option value="monthly">{m.monthly()}</option>
						<option value="quarterly">{m.quarterly()}</option>
						<option value="semiannual">{m.semiannual()}</option>
					</select>
				</div>

				<!-- No selection means every domain, so Global is not offered -->
				<div class="col-span-2">
					<div class="flex items-center justify-between gap-2 mb-1">
						<label class="text-sm font-semibold" for="folder-tree-select-btn-domain"
							>{m.folder()}</label
						>
						<label
							class="flex items-center gap-1 text-[11px] text-surface-600-400 whitespace-nowrap cursor-pointer"
						>
							<input
								type="checkbox"
								class="checkbox size-3.5"
								data-testid="control-plan-include-subdomains"
								checked={filters.include_subfolders}
								onchange={(event) =>
									applyFilters({ ...filters, include_subfolders: event.currentTarget.checked })}
							/>
							{m.controlPlanIncludeSubdomains()}
						</label>
					</div>
					<FolderTreeSelect
						form={pickerFilterForm}
						field="domain"
						nullable={true}
						contentTypes={['DO']}
						writePermission={null}
						onChange={(value) => setFilter('folder', value || '')}
					/>
				</div>

				<!-- Assignees — streamed -->
				{#await data.filterData}
					<div class="flex items-end">
						<div class="flex items-center gap-2 text-xs text-surface-500 py-2">
							<i class="fa-solid fa-spinner fa-spin"></i>
							{m.loading()}...
						</div>
					</div>
				{:then filterOptions}
					<div>
						<label
							for="assigned-to-filter"
							class="block text-[11px] font-semibold uppercase tracking-wider text-surface-500 mb-1"
							>{m.assignedTo()}</label
						>
						<select
							id="assigned-to-filter"
							value={filters.assigned_to}
							onchange={(event) => setFilter('assigned_to', event.currentTarget.value)}
							class="w-full px-2.5 py-1.5 text-sm border border-surface-200-800 rounded-lg bg-surface-50-950 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
						>
							<option value="">{m.allActors()}</option>
							{#each filterOptions.allActors as actor}
								<option value={actor.id}>{actor.str || actor.name}</option>
							{/each}
						</select>
					</div>
				{/await}

				<div class="col-span-2">
					<!-- With a domain selected, offer only the controls its plan covers;
					     the picker loads its options once, so remount it on change -->
					{#key `${filters.folder}:${filters.include_subfolders}:${pickerEpoch}`}
						<AutocompleteSelect
							form={pickerFilterForm}
							field="applied_controls"
							label={m.appliedControl()}
							optionsEndpoint="applied-controls"
							lazy={true}
							optionsDetailedUrlParameters={filters.folder
								? [
										['recurrent_task_folder', filters.folder],
										['include_subfolders', String(filters.include_subfolders)]
									]
								: []}
							optionsExtraFields={[['folder', 'str']]}
							portalDropdown={true}
							onChange={(value) => {
								const selected = Array.isArray(value) ? value[0] : value;
								setFilter('applied_controls', selected || '');
							}}
						/>
					{/key}
				</div>

				<div class="relative" data-menu="statuses">
					<span
						id="status-filter-label"
						class="block text-[11px] font-semibold uppercase tracking-wider text-surface-500 mb-1"
						>{m.aggregatedStatus()}</span
					>
					<button
						type="button"
						data-testid="control-plan-status-toggle"
						aria-labelledby="status-filter-label"
						aria-haspopup="true"
						aria-expanded={openMenu === 'statuses'}
						class="flex w-full items-center justify-between gap-2 px-2.5 py-1.5 text-sm text-left border border-surface-200-800 rounded-lg bg-surface-50-950 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
						title={statusSummary}
						onclick={() => toggleMenu('statuses')}
					>
						<span class="truncate">{statusSummary}</span>
						<i class="fa-solid fa-chevron-down text-[10px] text-surface-500"></i>
					</button>
					{#if openMenu === 'statuses'}
						<div
							class="absolute left-0 top-full z-40 mt-1 min-w-full p-1.5 rounded-lg border border-surface-200-800 bg-surface-50-950 shadow-lg"
						>
							<!-- "All" is a visible choice, not an empty menu: it is ticked
							     whenever no specific status is, and ticking it clears them -->
							<label
								class="flex items-center gap-2 px-2 py-1.5 text-xs rounded cursor-pointer whitespace-nowrap text-surface-800-200 hover:bg-surface-100-900"
							>
								<input
									type="checkbox"
									class="checkbox"
									data-testid="control-plan-status-all"
									checked={filters.statuses.length === 0}
									onchange={(event) => {
										// Already "all": there is nothing to fall back to, keep it ticked.
										event.currentTarget.checked = true;
										if (filters.statuses.length > 0) applyFilters({ ...filters, statuses: [] });
									}}
								/>
								{m.allStatuses()}
							</label>
							<div class="my-1 border-t border-surface-200-800"></div>
							{#each STATUS_OPTIONS as option (option.value)}
								<label
									class="flex items-center gap-2 px-2 py-1.5 text-xs rounded cursor-pointer whitespace-nowrap text-surface-800-200 hover:bg-surface-100-900"
								>
									<input
										type="checkbox"
										class="checkbox"
										data-testid="control-plan-status-{option.value}"
										checked={filters.statuses.includes(option.value)}
										onchange={() => toggleStatus(option.value)}
									/>
									{option.label()}
								</label>
							{/each}
						</div>
					{/if}
				</div>

				<div>
					<button
						type="button"
						onclick={resetFilters}
						class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-surface-600-400 bg-surface-50-950 border border-surface-200-800 rounded-lg hover:bg-surface-50-950 hover:border-surface-300-700 focus:outline-none focus:ring-2 focus:ring-gray-300 transition-all duration-150"
					>
						<i class="fa-solid fa-rotate-left text-xs"></i>
						<span>{m.reset()}</span>
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Review data — streamed; the previous result stays up while the next loads -->
	{#if !review}
		<div class="border border-surface-200-800 rounded-xl overflow-hidden animate-pulse">
			<div class="p-4 space-y-3">
				{#each [1, 2, 3, 4, 5, 6] as _}
					<div class="flex gap-3 items-center">
						<div class="h-4 w-64 bg-surface-100-900 rounded"></div>
						<div class="flex-1 flex gap-2">
							{#each [1, 2, 3, 4, 5, 6] as __}
								<div class="h-5 flex-1 bg-surface-50-950 rounded"></div>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{:else}
		{#if rows.length > 0}
			<!-- One table for every domain: grouping is a view choice, not a layout -->
			<div
				class="border border-surface-200-800 rounded-xl overflow-hidden bg-surface-50-950 shadow-sm transition-opacity duration-150"
				class:opacity-60={loading}
			>
				<div
					class="overflow-auto max-h-[75vh]"
					bind:clientWidth={containerWidth}
					use:scrollToCurrentPeriod={axisKey}
				>
					<table
						data-testid="control-plan-grid"
						class="table-fixed border-separate border-spacing-0"
						style:width="max(100%, {tableMinWidth}px)"
					>
						<colgroup>
							<col style:width="{paneWidth}px" />
							{#each buckets as bucket (bucket.key)}
								<col />
							{/each}
						</colgroup>
						<!-- Opaque rows: a backdrop filter on a row would paint over the row-spanning task header -->
						<thead class="sticky top-0 z-20">
							{#if granularity === 'weekly'}
								<tr class="bg-surface-50-950">
									{@render taskHeader(2)}
									{#each monthBands(buckets) as band (band.key)}
										<th
											colspan={band.span}
											class="px-1.5 pb-0.5 text-left text-[11px] font-semibold uppercase tracking-wider text-surface-500 border-l border-surface-200-800 whitespace-nowrap overflow-hidden
												{view.compact ? 'pt-1' : 'pt-2.5'}"
										>
											{getMonthName(band.month - 1)}
											{#if band.span > 1}
												<span class="font-normal text-surface-400">{band.year}</span>
											{/if}
										</th>
									{/each}
								</tr>
							{/if}
							<tr class="bg-surface-50-950">
								{#if granularity !== 'weekly'}
									{@render taskHeader(1)}
								{/if}
								{#each buckets as bucket (bucket.key)}
									{@const isCurrent = bucket.key === currentBucketKey}
									<th
										data-current-period={isCurrent ? '' : undefined}
										aria-current={isCurrent ? 'date' : undefined}
										class="px-0 text-center text-[11px] font-semibold uppercase tracking-wider border-b border-surface-200-800
											{view.compact || granularity === 'weekly' ? 'py-1' : 'py-2.5'}
											{isCurrent ? 'bg-violet-600 text-white dark:bg-violet-700' : 'text-surface-500'}"
										title={isCurrent
											? `${m.controlPlanCurrentPeriod()} · ${bucket.start} — ${bucket.end}`
											: `${bucket.start} — ${bucket.end}`}
									>
										{getBucketLabel(bucket, granularity)}
										{#if showBucketYear}
											<div
												class="text-[10px] font-normal normal-case leading-tight {isCurrent
													? 'text-violet-100'
													: 'text-surface-400'}"
											>
												{bucket.key.split('-')[0]}
											</div>
										{/if}
									</th>
								{/each}
							</tr>
						</thead>
						{#each groups as group (group.key)}
							{@const groupId = `${view.grouping}:${group.key}`}
							{@const collapsed = collapsedGroups.has(groupId)}
							<tbody>
								{#if view.grouping !== 'none'}
									<tr data-group-row>
										<td
											class="sticky left-0 z-10 p-0 bg-surface-100-900 border-b border-r border-surface-200-800"
										>
											<button
												type="button"
												aria-expanded={!collapsed}
												class="flex w-full items-center gap-2 px-3 text-left font-semibold text-surface-800-200
													{view.compact ? 'h-6 text-[11px]' : 'h-8 text-xs'}"
												onclick={() => toggleGroup(groupId)}
											>
												<i
													class="fa-solid {collapsed
														? 'fa-chevron-right'
														: 'fa-chevron-down'} w-2.5 text-[9px] text-surface-500"
												></i>
												<span class="truncate">{group.label}</span>
												<span class="font-normal text-surface-500">{group.rows.length}</span>
											</button>
										</td>
										<td
											colspan={buckets.length}
											class="p-0 bg-surface-100-900 border-b border-surface-200-800"
										></td>
									</tr>
								{/if}
								{#if !collapsed}
									{#each group.rows as row (row.task.id)}
										{@const task = row.task}
										<tr class="group/row">
											<td
												class="sticky left-0 z-10 p-0 bg-surface-50-950 border-b border-r border-surface-200-800 group-hover/row:bg-surface-100-900"
											>
												<div
													class="grid items-center gap-x-2 px-3 {view.compact
														? 'h-7 text-xs'
														: 'h-10 text-[13px]'}"
													style:grid-template-columns={gridTemplate}
												>
													{#each visibleColumns as column (column.id)}
														{#if column.id === 'name'}
															<span class="flex min-w-0 items-center gap-1">
																<Anchor
																	href="/task-templates/{task.id}"
																	class="truncate font-medium text-surface-800-200 hover:text-violet-600 transition-colors"
																	title={task.name}
																>
																	{task.name}
																</Anchor>
																{#if task.link}
																	<a
																		href={task.link}
																		target="_blank"
																		rel="noopener noreferrer"
																		class="shrink-0 text-surface-500 hover:text-violet-600 transition-colors"
																		title={task.link}
																	>
																		<i class="fa-solid fa-arrow-up-right-from-square text-[9px]"
																		></i>
																	</a>
																{/if}
															</span>
														{:else}
															{@const value = cellValue(column.id, row)}
															<span
																class="truncate text-surface-600-400"
																class:font-mono={column.id === 'ref'}
																title={value}>{value}</span
															>
														{/if}
													{/each}
												</div>
											</td>
											{#each buckets as bucket (bucket.key)}
												{@const bucketData = task.bucket_status?.[bucket.key]}
												{@const state = cellState(bucketData)}
												{@const nodeIds = bucketData?.node_ids ?? []}
												<!-- A late cell leads to its late occurrence, not to an earlier
												     one of the same period that is already closed. -->
												{@const firstNodeId =
													(state === 'overdue' && bucketData?.overdue_node_id) ||
													nodeIds[0] ||
													null}
												{@const cellShape = view.compact ? 'mx-0.5 h-4' : 'mx-0.5 h-6'}
												<td
													class="p-0 border-b border-surface-100-900 group-hover/row:bg-surface-100-900
														{bucket.key === currentBucketKey ? 'bg-violet-100/60 dark:bg-violet-900/30' : ''}"
												>
													{#if firstNodeId}
														<Anchor
															href="/task-nodes/{firstNodeId}"
															label={task.name}
															class="flex items-center justify-center rounded-sm {OCCURRENCE_STYLES[
																state
															]} {cellShape} hover:opacity-80 transition-opacity"
															title={nodeIds.length > 1
																? `${CELL_LABELS[state]()} · ${nodeIds.length} ${m.taskNodes().toLowerCase()}`
																: CELL_LABELS[state]()}
															data-cell-state={state}
														>
															{#if nodeIds.length > 1 && !view.compact}
																<span class="text-[10px] font-semibold text-surface-900-100"
																	>×{nodeIds.length}</span
																>
															{/if}
														</Anchor>
													{:else}
														<div class="rounded-sm {OCCURRENCE_STYLES[state]} {cellShape}"></div>
													{/if}
												</td>
											{/each}
										</tr>
									{/each}
								{/if}
							</tbody>
						{/each}
					</table>
				</div>
			</div>
		{:else}
			<div
				class="text-center py-16 text-surface-500 border border-dashed border-surface-200-800 rounded-xl"
			>
				{#if outstandingOnly}
					<i class="fa-solid fa-circle-check text-3xl mb-3 text-green-500"></i>
					<p>{m.controlPlanNothingOutstanding()}</p>
				{:else}
					<i class="fa-solid fa-calendar-xmark text-3xl mb-3 text-surface-400"></i>
					<p>{m.noRecurrentTasksFound()}</p>
				{/if}
			</div>
		{/if}

		<!-- Legend -->
		<div
			class="flex flex-wrap items-center gap-x-5 gap-y-2 justify-center text-xs text-surface-600-400 bg-surface-50-950/80 backdrop-blur-sm border border-surface-200-800 rounded-xl px-5 py-2.5"
		>
			{#each ['completed', 'in_progress', 'planned', 'overdue', 'cancelled', 'none'] as const as state}
				<div class="flex items-center gap-1.5">
					<div class="w-3 h-3 rounded-sm {OCCURRENCE_STYLES[state]}"></div>
					<span>{CELL_LABELS[state]()}</span>
				</div>
			{/each}
			<div class="flex items-center gap-1.5">
				<div class="w-3 h-3 rounded-sm bg-violet-600 dark:bg-violet-700"></div>
				<span>{m.controlPlanCurrentPeriod()}</span>
			</div>
		</div>
	{/if}
</div>
