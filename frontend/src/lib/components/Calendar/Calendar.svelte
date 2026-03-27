<script lang="ts">
	import { fly } from 'svelte/transition';
	import Day from './Day.svelte';
	import { Switch, Accordion } from '@skeletonlabs/skeleton-svelte';
	import { showAllEvents } from '$lib/utils/stores';
	import { writable } from 'svelte/store';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { CALENDAR_CATEGORIES, type CalendarEvent, type CalendarCategory } from './types';

	const today = new Date();

	interface Props {
		info: CalendarEvent[];
		month?: number;
		year?: number;
		categories: typeof CALENDAR_CATEGORIES;
		actorIds?: string[];
	}

	let {
		info,
		month = today.getMonth() + 1,
		year = today.getFullYear(),
		categories,
		actorIds = []
	}: Props = $props();

	export const selectedDay = writable<{ day: number; month: number; year: number } | null>(null);
	export const showSidePanel = writable(false);

	// Reset side panel when navigating to a different month
	$effect(() => {
		// Track month and year to trigger on navigation
		void month;
		void year;
		$selectedDay = null;
		$showSidePanel = false;
	});

	function closePanel() {
		$showSidePanel = false;
	}

	const daysOfWeek = [
		m.monday(),
		m.tuesday(),
		m.wednesday(),
		m.thursday(),
		m.friday(),
		m.saturday(),
		m.sunday()
	];
	const monthNames = [
		m.january(),
		m.february(),
		m.march(),
		m.april(),
		m.may(),
		m.june(),
		m.july(),
		m.august(),
		m.september(),
		m.october(),
		m.november(),
		m.december()
	];

	function currentMonth() {
		return `/calendar/${today.getFullYear()}/${today.getMonth() + 1}`;
	}

	function nextMonth(year: number, month: number) {
		if (month == 12) {
			return `/calendar/${year + 1}/1`;
		}
		return `/calendar/${year}/${month + 1}`;
	}

	function prevMonth(year: number, month: number) {
		if (month == 1) {
			return `/calendar/${year - 1}/12`;
		}
		return `/calendar/${year}/${month - 1}`;
	}

	// Build a Set of actor IDs for efficient lookup (includes user + team actors)
	let actorIdSet = $derived(new Set(actorIds));

	// Per-category visibility filter
	let visibleCategories = $state<Record<string, boolean>>(
		Object.fromEntries(Object.keys(categories).map((k) => [k, true]))
	);

	function toggleCategory(key: string) {
		visibleCategories[key] = !visibleCategories[key];
	}

	let filteredInfo = $state(info);

	$effect(() => {
		const showAll = $showAllEvents;
		const cats = visibleCategories;
		const myActors = actorIdSet;
		filteredInfo = info
			.filter((event) => cats[event.category])
			.filter((event) => showAll || event.users?.some((actor: any) => myActors.has(actor.id)));
	});

	let daysInMonth = $derived(new Date(year, month, 0).getDate());
	let firstDay = $derived(new Date(year, month - 1, 1).getDay());

	// Side panel: events for selected day, grouped by category
	let selectedDayItems = $derived(
		$selectedDay
			? filteredInfo.filter(
					(item) =>
						item.date.getDate() === $selectedDay!.day &&
						item.date.getMonth() + 1 === $selectedDay!.month &&
						item.date.getFullYear() === $selectedDay!.year
				)
			: []
	);

	let groupedItems = $derived.by(() => {
		const groups: Record<string, CalendarEvent[]> = {};
		for (const item of selectedDayItems) {
			if (!groups[item.category]) groups[item.category] = [];
			groups[item.category].push(item);
		}
		return groups;
	});

	const categoryLabelMap: Record<string, () => string> = {
		appliedControl: m.appliedControls,
		riskAcceptance: m.riskAcceptances,
		audit: m.complianceAssessments,
		task: m.tasks,
		contract: m.contracts,
		securityException: m.securityExceptions,
		finding: m.findings,
		riskAssessment: m.riskAssessments
	};
</script>

<div class="flex flex-row h-full gap-3">
	<!-- Main Calendar -->
	<div
		class="flex flex-col rounded-xl bg-white h-full {$showSidePanel
			? 'w-2/3'
			: 'w-full'} p-3 space-y-2 shadow-lg border border-surface-200"
	>
		<!-- Header -->
		<div class="flex items-center justify-between bg-surface-50 rounded-lg px-6 py-3">
			<a
				href={prevMonth(year, month)}
				aria-label={m.previous()}
				class="text-surface-500 hover:text-primary-600 transition-colors p-2 rounded-lg hover:bg-surface-100"
			>
				<i class="fas fa-chevron-left"></i>
			</a>
			{#key month}
				<h2
					class="text-2xl font-semibold text-surface-800 tracking-wide"
					in:fly={{ delay: 100, duration: 300 }}
				>
					{monthNames[month - 1]}, {year}
				</h2>
			{/key}
			<a
				href={nextMonth(year, month)}
				aria-label={m.next()}
				class="text-surface-500 hover:text-primary-600 transition-colors p-2 rounded-lg hover:bg-surface-100"
			>
				<i class="fas fa-chevron-right"></i>
			</a>
		</div>

		<!-- Filter Chips (Legend + Filter) -->
		<div class="flex flex-wrap gap-1.5 px-1">
			{#each Object.entries(categories) as [key, cat]}
				<button
					class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all cursor-pointer
					{visibleCategories[key]
						? 'border-surface-200 bg-surface-100 text-surface-700'
						: 'border-surface-200 bg-transparent text-surface-400 line-through opacity-50'}"
					aria-pressed={visibleCategories[key]}
					onclick={() => toggleCategory(key)}
				>
					<span class="inline-block w-2.5 h-2.5 rounded-full {cat.dotClass}"></span>
					{categoryLabelMap[key]?.() ?? key}
				</button>
			{/each}
		</div>

		<!-- Day of week headers -->
		<div class="grid grid-cols-7 gap-1 text-xs font-semibold text-surface-500 px-1">
			{#each daysOfWeek as dayName}
				<div class="flex justify-center py-1">
					{dayName}
				</div>
			{/each}
		</div>

		<!-- Day grid -->
		<div class="grid grid-cols-7 gap-1 h-full">
			{#if firstDay > 0}
				{#each Array.from({ length: firstDay - 1 }, (_, i) => i + 1) as _}
					<div></div>
				{/each}
			{:else}
				{#each Array.from({ length: 6 }, (_, i) => i + 1) as _}
					<div></div>
				{/each}
			{/if}
			{#each Array.from({ length: daysInMonth }, (_, i) => i + 1) as day}
				<Day {day} {month} {year} info={filteredInfo} {selectedDay} {showSidePanel} {categories} />
			{/each}
		</div>

		<!-- Footer -->
		<div class="flex items-center justify-between bg-surface-50 rounded-lg px-4 py-2">
			<a
				href={currentMonth()}
				class="flex items-center gap-1.5 text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors px-3 py-1.5 rounded-lg hover:bg-primary-50"
			>
				<i class="fas fa-calendar-day"></i>
				{m.today()}
			</a>
			<Switch
				name="tasks-toggle"
				checked={$showAllEvents}
				onCheckedChange={(e) => ($showAllEvents = e.checked)}
			>
				<Switch.Control>
					<Switch.Thumb />
				</Switch.Control>
				<Switch.HiddenInput />
				<span class="text-sm text-surface-600">{m.showAllEvents()}</span>
			</Switch>
		</div>
	</div>

	<!-- Side Panel -->
	{#if $showSidePanel && $selectedDay}
		<div
			class="flex flex-col rounded-xl bg-white h-full w-1/3 p-4 space-y-3 shadow-lg border border-surface-200"
			in:fly={{ x: 300, duration: 300 }}
			out:fly={{ x: 300, duration: 300 }}
		>
			<!-- Panel Header -->
			<div class="flex justify-between items-center pb-2 border-b border-surface-100">
				<h2 class="text-lg font-semibold text-surface-800">
					{$selectedDay.day}
					{monthNames[$selectedDay.month - 1]}, {$selectedDay.year}
				</h2>
				<button
					onclick={closePanel}
					aria-label={m.close()}
					class="text-surface-400 hover:text-surface-600 transition-colors p-1 rounded-lg hover:bg-surface-100"
				>
					<i class="fas fa-times"></i>
				</button>
			</div>

			<!-- Grouped Events -->
			<div class="overflow-y-auto grow">
				{#if selectedDayItems.length > 0}
					{@const groups = groupedItems}
					<Accordion value={Object.keys(groups)} multiple>
						{#each Object.entries(groups) as [catKey, items]}
							{@const cat = categories[catKey as CalendarCategory]}
							<Accordion.Item value={catKey}>
								<Accordion.ItemTrigger class="flex items-center gap-2 py-2 cursor-pointer">
									<span class="inline-block w-3 h-3 rounded-full {cat.dotClass}"></span>
									<span class="font-medium text-sm text-surface-700">
										{categoryLabelMap[catKey]?.() ?? catKey}
									</span>
									<span
										class="text-xs font-semibold bg-surface-100 text-surface-600 px-1.5 py-0.5 rounded-full"
									>
										{items.length}
									</span>
									<Accordion.ItemIndicator
										class="ml-auto transition-transform duration-200 data-[state=open]:rotate-180"
									>
										<i class="fas fa-chevron-down text-xs text-surface-400"></i>
									</Accordion.ItemIndicator>
								</Accordion.ItemTrigger>
								<Accordion.ItemContent>
									<ul class="space-y-1 pl-5 pb-2">
										{#each items as item}
											<li
												class="p-2 rounded-md border-l-2 transition-colors {cat.borderClass} {cat.bgClass} {cat.hoverClass}"
											>
												<Anchor href={item.link} class="block">
													<div class="flex items-center justify-between gap-2">
														<span class="font-medium text-sm {cat.textClass} truncate">
															{item.label}
														</span>
														{#if item.status}
															<span
																class="shrink-0 text-[10px] font-medium bg-surface-100 text-surface-500 px-1.5 py-0.5 rounded"
															>
																{safeTranslate(item.status)}
															</span>
														{/if}
													</div>
												</Anchor>
											</li>
										{/each}
									</ul>
								</Accordion.ItemContent>
							</Accordion.Item>
						{/each}
					</Accordion>
				{:else}
					<div class="text-center text-surface-400 py-8">
						<i class="fas fa-calendar-xmark text-2xl mb-2"></i>
						<p>{m.noEvents()}</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
