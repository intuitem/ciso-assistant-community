<script lang="ts">
	export interface GanttEntry {
		id: string;
		name: string;
		type: 'milestone' | 'task' | 'activity';
		start_date: string | null;
		end_date: string | null;
		progress: number;
		description: string;
		ref_id: string;
		folder_uuid: string;
		group_id: string | null;
	}

	export interface Folder {
		id: string;
		name: string;
		str?: string;
	}

	interface Props {
		entries: GanttEntry[];
		folders?: Folder[];
		onItemSelect?: (itemId: string | null) => void;
		itemUrlBuilder?: (entry: GanttEntry) => string;
	}

	let { entries, folders = [], onItemSelect, itemUrlBuilder }: Props = $props();

	type ZoomLevel = 'day' | 'week' | 'month' | 'year';

	// State
	let zoomLevel = $state<ZoomLevel>('month');
	let viewStartDate = $state<Date>(new Date());
	let selectedItemId = $state<string | null>(null);
	let selectedFolder = $state<string>('');

	// Calculate visible date range based on zoom level and current view position
	function getVisibleDateRange(
		startDate: Date,
		zoom: ZoomLevel,
		latestEventDate?: Date
	): { min: Date; max: Date } {
		const min = new Date(startDate);
		const max = new Date(startDate);

		switch (zoom) {
			case 'day':
				max.setDate(max.getDate() + 7);
				break;
			case 'week':
				max.setDate(max.getDate() + 56);
				break;
			case 'month':
				max.setMonth(max.getMonth() + 6);
				break;
			case 'year':
				max.setFullYear(max.getFullYear() + 2);
				break;
		}

		// If we have latest event date, extend the range to include it with margin
		if (latestEventDate) {
			const latestWithMargin = new Date(latestEventDate);
			switch (zoom) {
				case 'day':
					latestWithMargin.setDate(latestWithMargin.getDate() + 2);
					break;
				case 'week':
					latestWithMargin.setDate(latestWithMargin.getDate() + 14);
					break;
				case 'month':
					latestWithMargin.setMonth(latestWithMargin.getMonth() + 2);
					break;
				case 'year':
					latestWithMargin.setMonth(latestWithMargin.getMonth() + 6);
					break;
			}

			if (latestWithMargin > max) {
				max.setTime(latestWithMargin.getTime());
			}
		}

		return { min, max };
	}

	// Get earliest and latest dates from all entries
	function getDataDateRange(entries: GanttEntry[]): { earliest: Date; latest: Date } | null {
		if (entries.length === 0) return null;

		const dates: Date[] = [];
		entries.forEach((entry) => {
			if (entry.start_date) dates.push(new Date(entry.start_date));
			if (entry.end_date) dates.push(new Date(entry.end_date));
		});

		if (dates.length === 0) return null;

		return {
			earliest: new Date(Math.min(...dates.map((d) => d.getTime()))),
			latest: new Date(Math.max(...dates.map((d) => d.getTime())))
		};
	}

	let dataDateRange = $derived(getDataDateRange(entries));

	// Calculate minimum allowed start date
	function getMinStartDate(earliest: Date | null, zoom: ZoomLevel): Date {
		if (!earliest) return new Date(new Date().getFullYear() - 1, 0, 1);

		const minDate = new Date(earliest);
		switch (zoom) {
			case 'day':
				minDate.setDate(minDate.getDate() - 14);
				break;
			case 'week':
				minDate.setDate(minDate.getDate() - 112);
				break;
			case 'month':
				minDate.setMonth(minDate.getMonth() - 12);
				break;
			case 'year':
				minDate.setMonth(minDate.getMonth() - 3);
				break;
		}
		return minDate;
	}

	// Calculate maximum allowed start date
	function getMaxStartDate(latest: Date | null, zoom: ZoomLevel): Date {
		if (!latest) return new Date(new Date().getFullYear() + 1, 11, 31);

		const maxDate = new Date(latest);
		switch (zoom) {
			case 'day':
				maxDate.setDate(maxDate.getDate() + 14);
				maxDate.setDate(maxDate.getDate() - 7);
				break;
			case 'week':
				maxDate.setDate(maxDate.getDate() + 112);
				maxDate.setDate(maxDate.getDate() - 56);
				break;
			case 'month':
				maxDate.setMonth(maxDate.getMonth() + 12);
				maxDate.setMonth(maxDate.getMonth() - 6);
				break;
			case 'year':
				maxDate.setMonth(maxDate.getMonth() + 6);
				maxDate.setFullYear(maxDate.getFullYear() - 2);
				break;
		}
		return maxDate;
	}

	let minStartDate = $derived(getMinStartDate(dataDateRange?.earliest || null, zoomLevel));
	let maxStartDate = $derived(getMaxStartDate(dataDateRange?.latest || null, zoomLevel));
	let dateRange = $derived(getVisibleDateRange(viewStartDate, zoomLevel, dataDateRange?.latest));

	// Calculate timeline width dynamically based on actual date range
	function getActualTimelineWidth(range: { min: Date; max: Date }, zoom: ZoomLevel): number {
		const days = Math.ceil((range.max.getTime() - range.min.getTime()) / (1000 * 60 * 60 * 24));

		switch (zoom) {
			case 'day':
				return Math.max(840, (days / 7) * 840);
			case 'week':
				const weeks = Math.ceil(days / 7);
				return Math.max(1200, (weeks / 8) * 1200);
			case 'month':
				const months = Math.ceil(days / 30);
				return Math.max(1080, (months / 6) * 1080);
			case 'year':
				const quarters = Math.ceil(days / 91);
				return Math.max(1440, (quarters / 8) * 1440);
		}
	}

	let timelineWidth = $derived(getActualTimelineWidth(dateRange, zoomLevel));

	// Filtered entries
	let filteredEntries = $derived(
		entries.filter((entry) => {
			if (selectedFolder && entry.folder_uuid !== selectedFolder) return false;

			const entryStart = entry.start_date ? new Date(entry.start_date) : null;
			const entryEnd = entry.end_date ? new Date(entry.end_date) : null;

			if (entryEnd && entryEnd < dateRange.min) return false;
			if (entryStart && entryStart > dateRange.max) return false;

			return true;
		})
	);

	// Navigation functions
	function slideLeft() {
		const newDate = new Date(viewStartDate);
		switch (zoomLevel) {
			case 'day':
				newDate.setDate(newDate.getDate() - 7);
				break;
			case 'week':
				newDate.setDate(newDate.getDate() - 28);
				break;
			case 'month':
				newDate.setMonth(newDate.getMonth() - 3);
				break;
			case 'year':
				newDate.setFullYear(newDate.getFullYear() - 1);
				break;
		}
		if (newDate < minStartDate) {
			viewStartDate = new Date(minStartDate);
		} else {
			viewStartDate = newDate;
		}
	}

	function slideRight() {
		const newDate = new Date(viewStartDate);
		switch (zoomLevel) {
			case 'day':
				newDate.setDate(newDate.getDate() + 7);
				break;
			case 'week':
				newDate.setDate(newDate.getDate() + 28);
				break;
			case 'month':
				newDate.setMonth(newDate.getMonth() + 3);
				break;
			case 'year':
				newDate.setFullYear(newDate.getFullYear() + 1);
				break;
		}
		if (newDate > maxStartDate) {
			viewStartDate = new Date(maxStartDate);
		} else {
			viewStartDate = newDate;
		}
	}

	function resetToToday() {
		const today = new Date();

		if (!dataDateRange) {
			const newDate = new Date(today);
			switch (zoomLevel) {
				case 'day':
					newDate.setDate(today.getDate() - 3);
					break;
				case 'week':
					newDate.setDate(today.getDate() - 28);
					break;
				case 'month':
					newDate.setMonth(today.getMonth() - 3);
					break;
				case 'year':
					newDate.setFullYear(today.getFullYear() - 1);
					break;
			}
			viewStartDate = newDate;
			return;
		}

		const earliestWithMargin = new Date(dataDateRange.earliest);
		const latestWithMargin = new Date(dataDateRange.latest);

		switch (zoomLevel) {
			case 'day':
				earliestWithMargin.setDate(earliestWithMargin.getDate() - 2);
				latestWithMargin.setDate(latestWithMargin.getDate() + 2);
				break;
			case 'week':
				earliestWithMargin.setDate(earliestWithMargin.getDate() - 14);
				latestWithMargin.setDate(latestWithMargin.getDate() + 14);
				break;
			case 'month':
				earliestWithMargin.setMonth(earliestWithMargin.getMonth() - 2);
				latestWithMargin.setMonth(latestWithMargin.getMonth() + 2);
				break;
			case 'year':
				earliestWithMargin.setMonth(earliestWithMargin.getMonth() - 3);
				latestWithMargin.setMonth(latestWithMargin.getMonth() + 6);
				break;
		}

		const dataRangeMidpoint = new Date(
			(earliestWithMargin.getTime() + latestWithMargin.getTime()) / 2
		);

		const centerPoint =
			today >= earliestWithMargin && today <= latestWithMargin ? today : dataRangeMidpoint;

		const newDate = new Date(centerPoint);
		switch (zoomLevel) {
			case 'day':
				newDate.setDate(centerPoint.getDate() - 3);
				break;
			case 'week':
				newDate.setDate(centerPoint.getDate() - 28);
				break;
			case 'month':
				newDate.setMonth(centerPoint.getMonth() - 3);
				break;
			case 'year':
				newDate.setFullYear(centerPoint.getFullYear() - 1);
				break;
		}

		if (newDate < minStartDate) {
			viewStartDate = new Date(minStartDate);
		} else if (newDate > maxStartDate) {
			viewStartDate = new Date(maxStartDate);
		} else {
			viewStartDate = newDate;
		}
	}

	// Initialize view
	function initializeView() {
		if (!dataDateRange) {
			resetToToday();
			return;
		}

		const today = new Date();
		const earliest = dataDateRange.earliest;
		const latest = dataDateRange.latest;

		const startFromEarliest = new Date(earliest);

		switch (zoomLevel) {
			case 'day':
				startFromEarliest.setDate(startFromEarliest.getDate() - 2);
				break;
			case 'week':
				startFromEarliest.setDate(startFromEarliest.getDate() - 14);
				break;
			case 'month':
				startFromEarliest.setMonth(startFromEarliest.getMonth() - 2);
				break;
			case 'year':
				startFromEarliest.setMonth(startFromEarliest.getMonth() - 6);
				break;
		}

		if (earliest > today) {
			viewStartDate = startFromEarliest;
		} else if (latest < today) {
			const startDate = new Date(latest);
			switch (zoomLevel) {
				case 'day':
					startDate.setDate(startDate.getDate() - 7);
					break;
				case 'week':
					startDate.setDate(startDate.getDate() - 56);
					break;
				case 'month':
					startDate.setMonth(startDate.getMonth() - 6);
					break;
				case 'year':
					startDate.setFullYear(startDate.getFullYear() - 2);
					break;
			}
			viewStartDate = startDate;
		} else {
			if (startFromEarliest < today) {
				viewStartDate = startFromEarliest;
			} else {
				resetToToday();
			}
		}
	}

	$effect(() => {
		initializeView();
	});

	// Format date for display based on zoom level
	function formatDate(date: Date): string {
		switch (zoomLevel) {
			case 'day':
				return date.toLocaleDateString('en-US', {
					month: 'short',
					day: 'numeric',
					year: 'numeric'
				});
			case 'week':
				return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
			case 'month':
				return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
			case 'year':
				const quarter = Math.floor(date.getMonth() / 3) + 1;
				return `Q${quarter} ${date.getFullYear()}`;
		}
	}

	// Generate time scale markers
	function getTimeScaleMarkers(): { label: string; position: number }[] {
		const markers: { label: string; position: number }[] = [];
		const { min, max } = dateRange;
		const current = new Date(min);

		while (current <= max) {
			const position = getDatePosition(current.toISOString().split('T')[0], min, max);
			markers.push({
				label: formatDate(current),
				position
			});

			switch (zoomLevel) {
				case 'day':
					current.setDate(current.getDate() + 1);
					break;
				case 'week':
					current.setDate(current.getDate() + 7);
					break;
				case 'month':
					current.setMonth(current.getMonth() + 1);
					break;
				case 'year':
					current.setMonth(current.getMonth() + 3);
					break;
			}
		}

		return markers;
	}

	let timeScaleMarkers = $derived(getTimeScaleMarkers());

	// Calculate position on timeline
	function getDatePosition(date: string | null, minDate: Date, maxDate: Date): number {
		if (!date) return 0;
		const d = new Date(date).getTime();
		const min = minDate.getTime();
		const max = maxDate.getTime();
		return ((d - min) / (max - min)) * 100;
	}

	// Get today's position
	function getTodayPosition(): number | null {
		const today = new Date();
		if (today < dateRange.min || today > dateRange.max) return null;
		return getDatePosition(today.toISOString().split('T')[0], dateRange.min, dateRange.max);
	}

	let todayPosition = $derived(getTodayPosition());

	// Handle item click
	function handleItemClick(itemId: string) {
		if (selectedItemId === itemId) {
			selectedItemId = null;
			onItemSelect?.(null);
		} else {
			selectedItemId = itemId;
			onItemSelect?.(itemId);
		}
	}
</script>

<div class="space-y-4">
	<!-- Controls -->
	<div class="flex items-center justify-between gap-4">
		<!-- Zoom level -->
		<div>
			<label class="block text-sm font-medium text-gray-900 mb-1">Zoom</label>
			<div class="flex gap-1">
				<button
					type="button"
					class="btn btn-sm {zoomLevel === 'day' ? 'preset-filled' : 'preset-outlined'}"
					onclick={() => {
						zoomLevel = 'day';
						resetToToday();
					}}
				>
					Day
				</button>
				<button
					type="button"
					class="btn btn-sm {zoomLevel === 'week' ? 'preset-filled' : 'preset-outlined'}"
					onclick={() => {
						zoomLevel = 'week';
						resetToToday();
					}}
				>
					Week
				</button>
				<button
					type="button"
					class="btn btn-sm {zoomLevel === 'month' ? 'preset-filled' : 'preset-outlined'}"
					onclick={() => {
						zoomLevel = 'month';
						resetToToday();
					}}
				>
					Month
				</button>
				<button
					type="button"
					class="btn btn-sm {zoomLevel === 'year' ? 'preset-filled' : 'preset-outlined'}"
					onclick={() => {
						zoomLevel = 'year';
						resetToToday();
					}}
				>
					Year
				</button>
			</div>
		</div>

		<!-- Navigation -->
		<div>
			<label class="block text-sm font-medium text-gray-900 mb-1">Navigate</label>
			<div class="flex gap-1">
				<button type="button" class="btn btn-sm preset-outlined" onclick={slideLeft}>
					<i class="fas fa-chevron-left"></i>
				</button>
				<button type="button" class="btn btn-sm preset-outlined" onclick={resetToToday}>
					<i class="fas fa-calendar-day mr-1"></i>
					Today
				</button>
				<button type="button" class="btn btn-sm preset-outlined" onclick={slideRight}>
					<i class="fas fa-chevron-right"></i>
				</button>
			</div>
		</div>

		<!-- Folder filter -->
		{#if folders.length > 0}
			<div class="w-64">
				<label for="folder" class="block text-sm font-medium text-gray-900 mb-1">
					Filter by Folder
				</label>
				<select
					id="folder"
					bind:value={selectedFolder}
					class="w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
				>
					<option value="">All Folders</option>
					{#each folders as folder}
						<option value={folder.id}>{folder.str || folder.name}</option>
					{/each}
				</select>
			</div>
		{/if}
	</div>

	<!-- Stats and Details Section -->
	<div class="grid grid-cols-2 gap-4">
		<!-- Stats counters -->
		<div class="grid grid-cols-2 gap-4">
			<div class="bg-blue-50 p-4 rounded-lg">
				<div class="text-2xl font-bold text-blue-600">{filteredEntries.length}</div>
				<div class="text-sm text-gray-600">Total Items</div>
			</div>
			<div class="bg-green-50 p-4 rounded-lg">
				<div class="text-2xl font-bold text-green-600">
					{filteredEntries.filter((e) => e.type === 'milestone').length}
				</div>
				<div class="text-sm text-gray-600">Milestones</div>
			</div>
			<div class="bg-yellow-50 p-4 rounded-lg">
				<div class="text-2xl font-bold text-yellow-600">
					{filteredEntries.filter((e) => e.type === 'task').length}
				</div>
				<div class="text-sm text-gray-600">Tasks</div>
			</div>
			<div class="bg-purple-50 p-4 rounded-lg">
				<div class="text-2xl font-bold text-purple-600">
					{filteredEntries.filter((e) => e.type === 'activity').length}
				</div>
				<div class="text-sm text-gray-600">Control Implementations</div>
			</div>
		</div>

		<!-- Details panel -->
		<div class="bg-gray-50 p-4 rounded-lg border border-gray-200">
			{#if selectedItemId}
				{@const selectedEntry = filteredEntries.find((e) => e.id === selectedItemId)}
				{#if selectedEntry}
					<div class="space-y-3">
						<div class="flex items-start justify-between gap-2">
							<h3 class="font-semibold text-base">{selectedEntry.name}</h3>
							<button
								type="button"
								onclick={() => handleItemClick(selectedItemId)}
								class="text-gray-400 hover:text-gray-600"
								title="Clear selection"
							>
								<i class="fas fa-times"></i>
							</button>
						</div>

						{#if selectedEntry.ref_id}
							<div class="text-sm text-gray-600">
								<span class="font-medium">Reference:</span>
								{selectedEntry.ref_id}
							</div>
						{/if}

						{#if selectedEntry.description}
							<div class="text-sm text-gray-700">
								{selectedEntry.description}
							</div>
						{/if}

						<div class="text-sm text-gray-600 space-y-1 pt-2 border-t border-gray-300">
							<div>
								<span class="font-medium">Type:</span>
								<span
									class="ml-2 px-2 py-0.5 rounded text-xs {selectedEntry.type === 'milestone'
										? 'bg-green-100 text-green-700'
										: selectedEntry.type === 'task'
											? 'bg-yellow-100 text-yellow-700'
											: 'bg-purple-100 text-purple-700'}"
								>
									{selectedEntry.type === 'milestone'
										? 'Milestone'
										: selectedEntry.type === 'task'
											? 'Task'
											: 'Control Implementation'}
								</span>
							</div>
							{#if selectedEntry.start_date}
								<div>
									<span class="font-medium">Start:</span>
									{new Date(selectedEntry.start_date).toLocaleDateString('en-US', {
										year: 'numeric',
										month: 'short',
										day: 'numeric'
									})}
								</div>
							{/if}
							{#if selectedEntry.end_date}
								<div>
									<span class="font-medium">{selectedEntry.type === 'milestone' ? 'Date' : 'End'}:</span>
									{new Date(selectedEntry.end_date).toLocaleDateString('en-US', {
										year: 'numeric',
										month: 'short',
										day: 'numeric'
									})}
								</div>
							{/if}
							{#if selectedEntry.type === 'activity'}
								<div>
									<span class="font-medium">Progress:</span>
									<span class="ml-2">{selectedEntry.progress}%</span>
									<div class="mt-1 w-full bg-gray-200 rounded-full h-2">
										<div
											class="bg-purple-500 h-2 rounded-full transition-all"
											style="width: {selectedEntry.progress}%"
										></div>
									</div>
								</div>
							{/if}
						</div>

						{#if itemUrlBuilder}
							<div class="pt-2">
								<a href={itemUrlBuilder(selectedEntry)} class="btn btn-sm preset-filled w-full">
									<i class="fas fa-external-link-alt mr-2"></i>
									View Full Details
								</a>
							</div>
						{/if}
					</div>
				{/if}
			{:else}
				<div class="flex items-center justify-center h-full text-gray-400 text-sm">
					<div class="text-center">
						<i class="fas fa-mouse-pointer text-2xl mb-2"></i>
						<p>Click on any item to view details</p>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<!-- Timeline -->
	{#if filteredEntries.length === 0}
		<div class="text-center py-12 text-gray-500">
			<i class="fas fa-calendar-alt text-4xl mb-4"></i>
			<p>No items with dates found.</p>
		</div>
	{:else}
		<div class="border-t pt-4">
			<div class="flex items-start">
				<!-- Fixed column for names -->
				<div class="w-64 flex-shrink-0 pr-4">
					<div class="font-semibold text-sm text-gray-600 mb-4 h-10 flex items-end pb-1">
						Name
					</div>
					<div class="space-y-2">
						{#each filteredEntries as entry (entry.id)}
							<div class="h-10 flex items-center border-b pb-2">
								<div class="w-full">
									<div class="font-medium text-sm truncate" title={entry.name}>
										{#if entry.type === 'milestone'}
											<i class="fas fa-flag text-green-500 mr-1"></i>
										{:else if entry.type === 'task'}
											<i class="fas fa-square text-yellow-500 mr-1"></i>
										{:else}
											<i class="fas fa-bars text-purple-500 mr-1"></i>
										{/if}
										{entry.name}
									</div>
									{#if entry.ref_id}
										<div class="text-xs text-gray-500">{entry.ref_id}</div>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</div>

				<!-- Scrollable timeline area -->
				<div class="flex-1 overflow-x-auto">
					<div style="width: {timelineWidth}px;">
						<!-- Time scale markers -->
						<div class="relative h-10 border-b border-gray-300 mb-4">
							{#each timeScaleMarkers as marker}
								<div
									class="absolute top-0 h-10 flex flex-col items-start justify-end pb-1"
									style="left: {marker.position}%;"
								>
									<div class="h-2 w-px bg-gray-300 mb-1"></div>
									<span class="text-xs text-gray-600 transform -translate-x-1/2 whitespace-nowrap">
										{marker.label}
									</span>
								</div>
							{/each}

							<!-- Today marker -->
							{#if todayPosition !== null}
								<div class="absolute top-0 h-full w-0.5 bg-red-500 z-10" style="left: {todayPosition}%;">
									<div
										class="absolute -top-1 left-1/2 transform -translate-x-1/2 text-xs font-semibold text-red-500 whitespace-nowrap"
									>
										Today
									</div>
								</div>
							{/if}
						</div>

						<!-- Gantt chart bars -->
						<div class="space-y-2">
							{#each filteredEntries as entry (entry.id)}
								<div class="h-10 flex items-center border-b pb-2 relative">
									<div class="w-full relative h-8 bg-gray-50 rounded overflow-visible">
										<!-- Background grid lines -->
										{#each timeScaleMarkers as marker}
											<div
												class="absolute top-0 h-8 w-px bg-gray-200"
												style="left: {marker.position}%;"
											></div>
										{/each}

										<!-- Today marker line -->
										{#if todayPosition !== null}
											<div
												class="absolute top-0 h-8 w-0.5 bg-red-300 z-0"
												style="left: {todayPosition}%;"
											></div>
										{/if}

										{#if entry.type === 'milestone'}
											<!-- Milestone -->
											<button
												type="button"
												class="absolute top-0 h-8 flex items-center justify-center z-10 cursor-pointer hover:scale-110 transition-transform"
												style="left: {getDatePosition(
													entry.end_date,
													dateRange.min,
													dateRange.max
												)}%; transform: translateX(-50%);"
												onclick={() => handleItemClick(entry.id)}
											>
												<div class="w-4 h-4 bg-green-500 rotate-45 border-2 border-white shadow"></div>
											</button>
										{:else if entry.type === 'task'}
											<!-- Task -->
											<button
												type="button"
												class="absolute top-1 h-6 bg-yellow-500 rounded shadow z-10 cursor-pointer hover:bg-yellow-600 transition-colors"
												style="left: {getDatePosition(
													entry.end_date,
													dateRange.min,
													dateRange.max
												)}%; width: 3px;"
												onclick={() => handleItemClick(entry.id)}
											></button>
										{:else if entry.type === 'activity'}
											<!-- Control Implementation -->
											{@const leftPos = getDatePosition(entry.start_date, dateRange.min, dateRange.max)}
											{@const rightPos = getDatePosition(entry.end_date, dateRange.min, dateRange.max)}
											{@const width = rightPos - leftPos}
											<button
												type="button"
												class="absolute top-1 h-6 bg-purple-200 rounded shadow z-10 cursor-pointer hover:bg-purple-300 transition-colors"
												style="left: {leftPos}%; width: {width}%;"
												onclick={() => handleItemClick(entry.id)}
											>
												<div
													class="h-full bg-purple-500 rounded transition-all pointer-events-none"
													style="width: {entry.progress}%;"
												></div>
											</button>
											<div
												class="absolute top-1 h-6 flex items-center justify-center text-xs font-semibold text-white z-20 pointer-events-none"
												style="left: {leftPos}%; width: {width}%;"
											>
												{#if entry.progress > 0}
													{entry.progress}%
												{/if}
											</div>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Legend -->
		<div class="flex gap-6 text-sm pt-4 border-t">
			<div class="flex items-center gap-2">
				<div class="w-4 h-4 bg-green-500 rotate-45"></div>
				<span>Milestone</span>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-1 h-4 bg-yellow-500"></div>
				<span>Task (1 day)</span>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-8 h-4 bg-purple-500 rounded"></div>
				<span>Control Implementation (range)</span>
			</div>
		</div>
	{/if}
</div>
