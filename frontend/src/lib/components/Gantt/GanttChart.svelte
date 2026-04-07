<script lang="ts">
	import { tick } from 'svelte';

	export interface GanttItem {
		id: string;
		name: string;
		startDate: Date | null;
		endDate: Date | null;
		progress: number; // 0-100
		type: 'bar' | 'milestone';
		category: string; // e.g. 'appliedControls', 'complianceAssessments'
		categoryLabel: string;
		folder: string; // folder name (domain)
		folderId: string;
		href: string;
		color: string;
	}

	type ZoomLevel = 'weekly' | 'monthly' | 'yearly';

	interface Props {
		items: GanttItem[];
		zoom?: ZoomLevel;
	}

	let { items, zoom = 'monthly' }: Props = $props();

	// --- Layout constants ---
	const ROW_HEIGHT = 32;
	const ROW_GAP = 4;
	const HEADER_HEIGHT = 50;
	const LABEL_WIDTH = 280;
	const MILESTONE_RADIUS = 7;
	const BAR_HEIGHT = 20;
	const MIN_BAR_WIDTH = 6;

	// --- Computed timeline bounds ---
	let timelineStart = $derived.by(() => {
		const dates = items
			.flatMap((i) => [i.startDate, i.endDate])
			.filter((d): d is Date => d !== null);
		if (dates.length === 0) return new Date();
		const min = new Date(Math.min(...dates.map((d) => d.getTime())));
		// week buffer before
		min.setDate(min.getDate() - 7);
		return startOfDay(min);
	});

	let timelineEnd = $derived.by(() => {
		const dates = items
			.flatMap((i) => [i.startDate, i.endDate])
			.filter((d): d is Date => d !== null);
		if (dates.length === 0) {
			const d = new Date();
			d.setMonth(d.getMonth() + 3);
			return d;
		}
		const max = new Date(Math.max(...dates.map((d) => d.getTime())));
		// week buffer after
		max.setDate(max.getDate() + 7);
		return startOfDay(max);
	});

	// --- Swimlane grouping: folder -> category -> items ---
	interface Swimlane {
		folderId: string;
		folderName: string;
		categories: {
			category: string;
			categoryLabel: string;
			items: GanttItem[];
		}[];
	}

	let swimlanes: Swimlane[] = $derived.by(() => {
		const folderMap = new Map<
			string,
			{ folderName: string; catMap: Map<string, { label: string; items: GanttItem[] }> }
		>();

		for (const item of items) {
			if (!folderMap.has(item.folderId)) {
				folderMap.set(item.folderId, { folderName: item.folder, catMap: new Map() });
			}
			const entry = folderMap.get(item.folderId)!;
			if (!entry.catMap.has(item.category)) {
				entry.catMap.set(item.category, { label: item.categoryLabel, items: [] });
			}
			entry.catMap.get(item.category)!.items.push(item);
		}

		const result: Swimlane[] = [];
		for (const [folderId, { folderName, catMap }] of folderMap) {
			const categories = Array.from(catMap.entries()).map(([category, { label, items }]) => ({
				category,
				categoryLabel: label,
				items: items.sort((a, b) => {
					const aDate = a.startDate ?? a.endDate ?? new Date(0);
					const bDate = b.startDate ?? b.endDate ?? new Date(0);
					return aDate.getTime() - bDate.getTime();
				})
			}));
			result.push({ folderId, folderName, categories });
		}
		return result.sort((a, b) => a.folderName.localeCompare(b.folderName));
	});

	// --- Flat row list for positioning ---
	interface Row {
		kind: 'folder-header' | 'category-header' | 'item';
		label: string;
		item?: GanttItem;
		depth: number;
	}

	let rows: Row[] = $derived.by(() => {
		const r: Row[] = [];
		for (const sl of swimlanes) {
			r.push({ kind: 'folder-header', label: sl.folderName, depth: 0 });
			for (const cat of sl.categories) {
				r.push({ kind: 'category-header', label: cat.categoryLabel, depth: 1 });
				for (const item of cat.items) {
					r.push({ kind: 'item', label: item.name, item, depth: 2 });
				}
			}
		}
		return r;
	});

	let totalHeight = $derived(HEADER_HEIGHT + rows.length * (ROW_HEIGHT + ROW_GAP) + 20);

	// --- Time scale helpers ---
	function startOfDay(d: Date): Date {
		const r = new Date(d);
		r.setHours(0, 0, 0, 0);
		return r;
	}

	function daysBetween(a: Date, b: Date): number {
		return (b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24);
	}

	let totalDays = $derived(Math.max(1, daysBetween(timelineStart, timelineEnd)));

	// Pixel width per day depends on zoom
	let dayWidth = $derived.by(() => {
		switch (zoom) {
			case 'weekly':
				return 18;
			case 'monthly':
				return 4;
			case 'yearly':
				return 1;
		}
	});

	let chartWidth = $derived(totalDays * dayWidth);

	function dateToX(d: Date): number {
		return daysBetween(timelineStart, d) * dayWidth;
	}

	// --- Grid lines and labels ---
	interface GridMark {
		x: number;
		label: string;
		isMajor: boolean;
	}

	let gridMarks: GridMark[] = $derived.by(() => {
		const marks: GridMark[] = [];
		const d = new Date(timelineStart);

		if (zoom === 'weekly') {
			// Show each Monday, major = 1st of month
			// Move to next Monday
			const day = d.getDay();
			const daysToMonday = day === 0 ? 1 : day === 1 ? 0 : 8 - day;
			d.setDate(d.getDate() + daysToMonday);

			while (d <= timelineEnd) {
				const x = dateToX(d);
				const isMajor = d.getDate() <= 7;
				const label = isMajor
					? d.toLocaleDateString('en', { month: 'short', year: 'numeric' })
					: d.toLocaleDateString('en', { day: 'numeric', month: 'short' });
				marks.push({ x, label, isMajor });
				d.setDate(d.getDate() + 7);
			}
		} else if (zoom === 'monthly') {
			// Show 1st of each month
			d.setDate(1);
			if (d < timelineStart) d.setMonth(d.getMonth() + 1);
			while (d <= timelineEnd) {
				const x = dateToX(d);
				const isMajor = d.getMonth() === 0;
				const label = isMajor
					? d.toLocaleDateString('en', { month: 'short', year: 'numeric' })
					: d.toLocaleDateString('en', { month: 'short' });
				marks.push({ x, label, isMajor });
				d.setMonth(d.getMonth() + 1);
			}
		} else {
			// yearly: show Jan of each year
			d.setMonth(0, 1);
			if (d < timelineStart) d.setFullYear(d.getFullYear() + 1);
			while (d <= timelineEnd) {
				const x = dateToX(d);
				marks.push({ x, label: d.getFullYear().toString(), isMajor: true });
				d.setFullYear(d.getFullYear() + 1);
			}
		}
		return marks;
	});

	// --- Today line ---
	let todayX = $derived(dateToX(startOfDay(new Date())));
	let todayVisible = $derived(todayX >= 0 && todayX <= chartWidth);

	// --- Tooltip ---
	let tooltip = $state<{ x: number; y: number; item: GanttItem } | null>(null);

	function showTooltip(e: MouseEvent, item: GanttItem) {
		tooltip = { x: e.clientX, y: e.clientY, item };
	}

	function hideTooltip() {
		tooltip = null;
	}

	function formatDate(d: Date | null): string {
		if (!d) return '—';
		return d.toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' });
	}

	// --- Scroll container ref for auto-scroll to today ---
	let scrollContainer: HTMLDivElement | undefined = $state();

	$effect(() => {
		if (scrollContainer && todayVisible) {
			tick().then(() => {
				const scrollTo = Math.max(0, todayX - scrollContainer!.clientWidth / 3);
				scrollContainer!.scrollLeft = scrollTo;
			});
		}
	});
</script>

<div class="gantt-wrapper relative">
	<!-- Label column + scrollable chart area -->
	<div class="flex overflow-hidden border border-surface-300 rounded-lg">
		<!-- Fixed label column -->
		<div
			class="shrink-0 bg-surface-50 border-r border-surface-300 overflow-hidden"
			style="width: {LABEL_WIDTH}px"
		>
			<!-- Header spacer -->
			<div
				class="border-b border-surface-300 bg-surface-100 flex items-end px-2 text-xs font-semibold text-surface-500"
				style="height: {HEADER_HEIGHT}px"
			>
				Items
			</div>
			<!-- Row labels -->
			{#each rows as row, i}
				{@const y = i * (ROW_HEIGHT + ROW_GAP)}
				<div
					class="flex items-center overflow-hidden text-ellipsis whitespace-nowrap"
					style="height: {ROW_HEIGHT}px; margin-top: {ROW_GAP}px; padding-left: {8 +
						row.depth * 16}px"
					title={row.label}
				>
					{#if row.kind === 'folder-header'}
						<span class="text-xs font-bold text-surface-700 uppercase tracking-wide">
							<i class="fa-solid fa-folder text-primary-500 mr-1"></i>
							{row.label}
						</span>
					{:else if row.kind === 'category-header'}
						<span class="text-xs font-semibold text-surface-500">
							{row.label}
						</span>
					{:else if row.item}
						<a
							href={row.item.href}
							class="text-xs text-surface-700 hover:text-primary-600 hover:underline truncate"
							title={row.label}
						>
							{row.label}
						</a>
					{/if}
				</div>
			{/each}
		</div>

		<!-- Scrollable chart area -->
		<div class="flex-1 overflow-x-auto overflow-y-hidden" bind:this={scrollContainer}>
			<svg
				width={chartWidth}
				height={totalHeight}
				class="block"
				role="img"
				aria-label="Gantt chart"
			>
				<!-- Header background -->
				<rect x="0" y="0" width={chartWidth} height={HEADER_HEIGHT} class="fill-surface-100" />
				<line
					x1="0"
					y1={HEADER_HEIGHT}
					x2={chartWidth}
					y2={HEADER_HEIGHT}
					stroke="var(--color-surface-300)"
					stroke-width="1"
				/>

				<!-- Grid lines and labels -->
				{#each gridMarks as mark}
					<line
						x1={mark.x}
						y1={0}
						x2={mark.x}
						y2={totalHeight}
						stroke={mark.isMajor ? 'var(--color-surface-300)' : 'var(--color-surface-200)'}
						stroke-width={mark.isMajor ? 1 : 0.5}
					/>
					<text
						x={mark.x + 4}
						y={HEADER_HEIGHT - 8}
						class="fill-surface-500"
						font-size="11"
						font-family="system-ui, sans-serif"
					>
						{mark.label}
					</text>
				{/each}

				<!-- Today line -->
				{#if todayVisible}
					<line
						x1={todayX}
						y1={0}
						x2={todayX}
						y2={totalHeight}
						stroke="var(--color-error-500)"
						stroke-width="1.5"
						stroke-dasharray="4 2"
					/>
					<text
						x={todayX + 4}
						y={14}
						fill="var(--color-error-500)"
						font-size="10"
						font-weight="bold"
						font-family="system-ui, sans-serif">Today</text
					>
				{/if}

				<!-- Row backgrounds -->
				{#each rows as row, i}
					{@const y = HEADER_HEIGHT + i * (ROW_HEIGHT + ROW_GAP)}
					{#if row.kind === 'folder-header'}
						<rect
							x="0"
							{y}
							width={chartWidth}
							height={ROW_HEIGHT}
							fill="var(--color-surface-100)"
							opacity="0.7"
						/>
					{:else if row.kind === 'item' && i % 2 === 0}
						<rect
							x="0"
							{y}
							width={chartWidth}
							height={ROW_HEIGHT}
							fill="var(--color-surface-50)"
							opacity="0.5"
						/>
					{/if}
				{/each}

				<!-- Bars and milestones -->
				{#each rows as row, i}
					{#if row.kind === 'item' && row.item}
						{@const item = row.item}
						{@const cy = HEADER_HEIGHT + i * (ROW_HEIGHT + ROW_GAP) + ROW_HEIGHT / 2}

						{#if item.type === 'milestone'}
							<!-- Diamond milestone -->
							{@const mx = dateToX(item.endDate ?? item.startDate ?? new Date())}
							<g
								class="cursor-pointer"
								onmouseenter={(e) => showTooltip(e, item)}
								onmouseleave={hideTooltip}
							>
								<polygon
									points="{mx},{cy - MILESTONE_RADIUS} {mx + MILESTONE_RADIUS},{cy} {mx},{cy +
										MILESTONE_RADIUS} {mx - MILESTONE_RADIUS},{cy}"
									fill={item.color}
									stroke="white"
									stroke-width="1"
								/>
							</g>
						{:else}
							<!-- Bar -->
							{@const x1 = dateToX(item.startDate!)}
							{@const x2 = dateToX(item.endDate!)}
							{@const barWidth = Math.max(MIN_BAR_WIDTH, x2 - x1)}
							{@const barY = cy - BAR_HEIGHT / 2}
							<g
								class="cursor-pointer"
								onmouseenter={(e) => showTooltip(e, item)}
								onmouseleave={hideTooltip}
							>
								<!-- Background (unfilled) -->
								<rect
									x={x1}
									y={barY}
									width={barWidth}
									height={BAR_HEIGHT}
									rx="4"
									ry="4"
									fill={item.color}
									opacity="0.25"
									stroke={item.color}
									stroke-width="1"
								/>
								<!-- Progress fill -->
								{#if item.progress > 0}
									{@const fillWidth = Math.max(2, (barWidth * item.progress) / 100)}
									<rect
										x={x1}
										y={barY}
										width={fillWidth}
										height={BAR_HEIGHT}
										rx="4"
										ry="4"
										fill={item.color}
										opacity="0.7"
									/>
								{/if}
								<!-- Progress text inside bar if wide enough -->
								{#if barWidth > 40}
									<text
										x={x1 + barWidth / 2}
										y={cy + 4}
										text-anchor="middle"
										font-size="10"
										font-weight="600"
										font-family="system-ui, sans-serif"
										fill="var(--color-surface-700)"
									>
										{item.progress}%
									</text>
								{/if}
							</g>
						{/if}
					{/if}
				{/each}
			</svg>
		</div>
	</div>

	<!-- Tooltip -->
	{#if tooltip}
		<div
			class="fixed z-50 bg-white shadow-xl border border-surface-200 rounded-lg px-3 py-2 text-xs pointer-events-none max-w-xs"
			style="left: {tooltip.x + 12}px; top: {tooltip.y - 10}px"
		>
			<div class="font-bold text-surface-800 mb-1">{tooltip.item.name}</div>
			<div class="text-surface-500">
				<span
					class="inline-block w-2 h-2 rounded-full mr-1"
					style="background: {tooltip.item.color}"
				></span>
				{tooltip.item.categoryLabel} &middot; {tooltip.item.folder}
			</div>
			{#if tooltip.item.type === 'milestone'}
				<div class="mt-1">
					<i class="fa-solid fa-diamond text-[8px] mr-1"></i>
					{formatDate(tooltip.item.endDate ?? tooltip.item.startDate)}
				</div>
			{:else}
				<div class="mt-1">
					{formatDate(tooltip.item.startDate)} &rarr; {formatDate(tooltip.item.endDate)}
				</div>
				<div class="mt-0.5">Progress: {tooltip.item.progress}%</div>
			{/if}
		</div>
	{/if}
</div>
