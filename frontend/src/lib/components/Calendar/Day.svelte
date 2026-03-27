<script lang="ts">
	import { Tooltip } from '@skeletonlabs/skeleton-svelte';
	import { m } from '$paraglide/messages';
	import { CALENDAR_CATEGORIES, type CalendarEvent, type CalendarCategory } from './types';

	interface Props {
		day: number;
		month: number;
		year: number;
		info: CalendarEvent[];
		selectedDay: any;
		showSidePanel: any;
		categories: typeof CALENDAR_CATEGORIES;
	}

	let { day, month, year, info, selectedDay, showSidePanel, categories }: Props = $props();

	const today = new Date();
	const MAX_DOTS_PER_CATEGORY = 5;

	let isToday = $derived(
		day === today.getDate() && month === today.getMonth() + 1 && year === today.getFullYear()
	);

	let isPast = $derived(
		year < today.getFullYear() ||
			(year === today.getFullYear() && month < today.getMonth() + 1) ||
			(year === today.getFullYear() && month === today.getMonth() + 1 && day < today.getDate())
	);

	let dayInfo = $derived(
		info.filter(
			(item) =>
				item.date.getDate() === day &&
				item.date.getMonth() + 1 === month &&
				item.date.getFullYear() === year
		)
	);

	let totalCount = $derived(dayInfo.length);

	let dotsByCategory = $derived.by(() => {
		const counts: Record<string, number> = {};
		for (const item of dayInfo) {
			counts[item.category] = (counts[item.category] || 0) + 1;
		}
		return counts;
	});

	let heatBg = $derived.by(() => {
		if (totalCount === 0 || isPast) return '';
		if (totalCount <= 2) return 'bg-primary-50/50';
		if (totalCount <= 5) return 'bg-primary-50';
		return 'bg-primary-100/70';
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

	function openSidePanel() {
		selectedDay.set({ day, month, year });
		showSidePanel.set(true);
	}

	let isSelected = $derived(
		$selectedDay?.day === day && $selectedDay?.month === month && $selectedDay?.year === year
	);

	let cellClass = $derived(
		`flex flex-col items-start p-1.5 rounded-lg text-sm min-h-20 w-full h-full border transition-all cursor-pointer hover:bg-surface-100 ${
			isPast
				? totalCount > 0
					? 'bg-surface-100 text-surface-400 border-surface-200'
					: 'bg-surface-50 text-surface-400 border-surface-100'
				: totalCount > 0
					? `border-surface-200 ${heatBg}`
					: 'border-surface-200 bg-white'
		} ${isSelected ? 'ring-2 ring-primary-400' : ''}`
	);
</script>

{#snippet dayContent()}
	<!-- Day number + count -->
	<div class="flex items-center justify-between w-full mb-1">
		<span
			class={isToday
				? 'font-bold bg-primary-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs'
				: 'text-xs text-surface-600'}
		>
			{day}
		</span>
		{#if totalCount > 0}
			<span class="text-[10px] font-semibold text-surface-400">
				{totalCount}
			</span>
		{/if}
	</div>

	<!-- Colored dots -->
	{#if totalCount > 0}
		<div class="flex flex-wrap gap-[3px] mt-auto">
			{#each Object.entries(dotsByCategory) as [catKey, count]}
				{@const cat = categories[catKey as CalendarCategory]}
				{#each Array(Math.min(count, MAX_DOTS_PER_CATEGORY)) as _}
					<span class="w-2 h-2 rounded-full {cat.dotClass}"></span>
				{/each}
				{#if count > MAX_DOTS_PER_CATEGORY}
					<span class="text-[8px] leading-none text-surface-400 self-center">
						+{count - MAX_DOTS_PER_CATEGORY}
					</span>
				{/if}
			{/each}
		</div>
	{/if}
{/snippet}

<div class="min-h-20">
	{#if totalCount > 0}
		<Tooltip openDelay={300} closeDelay={100} positioning={{ placement: 'top' }}>
			<Tooltip.Trigger class={cellClass} onclick={openSidePanel}>
				{@render dayContent()}
			</Tooltip.Trigger>
			<Tooltip.Positioner class="!z-50">
				<Tooltip.Content>
					<div class="bg-surface-900 text-white p-2.5 rounded-lg shadow-xl text-xs space-y-1">
						{#each Object.entries(dotsByCategory) as [catKey, count]}
							{@const cat = categories[catKey as CalendarCategory]}
							<div class="flex items-center gap-2">
								<span class="w-2 h-2 rounded-full {cat.dotClass}"></span>
								<span>{categoryLabelMap[catKey]?.() ?? catKey}:</span>
								<span class="font-semibold">{count}</span>
							</div>
						{/each}
					</div>
				</Tooltip.Content>
			</Tooltip.Positioner>
		</Tooltip>
	{:else}
		<button class={cellClass} onclick={openSidePanel}>
			{@render dayContent()}
		</button>
	{/if}
</div>
