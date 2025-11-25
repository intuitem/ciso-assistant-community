<script lang="ts">
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	type GanttEntryType = 'milestone' | 'task' | 'activity';

	interface GanttEntry {
		id: string;
		name: string;
		type: GanttEntryType;
		start_date: string | null;
		end_date: string | null;
		progress: number;
		description: string;
		ref_id: string;
		folder_uuid: string;
		group_id: string | null;
	}

	// Display names for entry types
	const entryTypeLabels = {
		milestone: 'Milestone',
		task: 'Task',
		activity: 'Control Implementation'
	};

	interface GanttGroup {
		id: string;
		name: string;
	}

	// Hardcoded dummy data for demonstration
	function getDummyGanttEntries(): GanttEntry[] {
		const today = new Date();
		const oneWeekAgo = new Date(today);
		oneWeekAgo.setDate(today.getDate() - 7);
		const twoWeeksFromNow = new Date(today);
		twoWeeksFromNow.setDate(today.getDate() + 14);
		const oneMonthFromNow = new Date(today);
		oneMonthFromNow.setDate(today.getDate() + 30);
		const twoMonthsFromNow = new Date(today);
		twoMonthsFromNow.setDate(today.getDate() + 60);

		return [
			{
				id: 'dummy-1',
				name: 'Security Awareness Training',
				type: 'activity',
				start_date: oneWeekAgo.toISOString().split('T')[0],
				end_date: twoWeeksFromNow.toISOString().split('T')[0],
				progress: 65,
				description: 'Organization-wide security awareness program',
				ref_id: 'CTL-001',
				folder_uuid: '',
				group_id: 'Security'
			},
			{
				id: 'dummy-2',
				name: 'ISO 27001 Certification Audit',
				type: 'milestone',
				start_date: null,
				end_date: oneMonthFromNow.toISOString().split('T')[0],
				progress: 0,
				description: 'Final audit for ISO 27001 certification',
				ref_id: 'MILE-001',
				folder_uuid: '',
				group_id: 'Compliance'
			},
			{
				id: 'dummy-3',
				name: 'Firewall Configuration Review',
				type: 'task',
				start_date: null,
				end_date: today.toISOString().split('T')[0],
				progress: 0,
				description: 'Review and update firewall rules',
				ref_id: 'TSK-001',
				folder_uuid: '',
				group_id: 'Infrastructure'
			},
			{
				id: 'dummy-4',
				name: 'Data Encryption Implementation',
				type: 'activity',
				start_date: today.toISOString().split('T')[0],
				end_date: oneMonthFromNow.toISOString().split('T')[0],
				progress: 30,
				description: 'Deploy encryption for data at rest',
				ref_id: 'CTL-002',
				folder_uuid: '',
				group_id: 'Security'
			},
			{
				id: 'dummy-5',
				name: 'Incident Response Plan Update',
				type: 'activity',
				start_date: oneWeekAgo.toISOString().split('T')[0],
				end_date: twoMonthsFromNow.toISOString().split('T')[0],
				progress: 45,
				description: 'Update and test incident response procedures',
				ref_id: 'CTL-003',
				folder_uuid: '',
				group_id: 'Operations'
			}
		];
	}

	// Transform applied controls to Gantt entries
	function transformAppliedControlsToGanttEntries(appliedControls: any[]): GanttEntry[] {
		return appliedControls
			.filter((control) => control.eta || control.due_date)
			.map((control) => {
				// Determine type based on dates
				let type: GanttEntryType = 'task';
				let start_date = null;
				let end_date = null;

				if (control.eta && control.due_date) {
					type = 'activity';
					start_date = control.eta;
					end_date = control.due_date;
				} else if (control.eta || control.due_date) {
					type = 'milestone';
					end_date = control.eta || control.due_date;
				}

				// Calculate progress based on status
				let progress = 0;
				if (control.status === 'active') progress = 100;
				else if (control.status === 'in_progress') progress = 50;

				return {
					id: control.id,
					name: control.name || 'Unnamed Control',
					type,
					start_date,
					end_date,
					progress,
					description: control.description || '',
					ref_id: control.ref_id || '',
					folder_uuid: control.folder?.id || '',
					group_id: control.category || null
				};
			});
	}

	// Get unique groups from entries
	function getGroupsFromEntries(entries: GanttEntry[]): GanttGroup[] {
		const groupMap = new Map<string, string>();
		entries.forEach((entry) => {
			if (entry.group_id) {
				groupMap.set(entry.group_id, entry.group_id);
			}
		});
		return Array.from(groupMap.entries()).map(([id, name]) => ({ id, name }));
	}

	// Calculate date range for visualization
	function getDateRange(entries: GanttEntry[]): { min: Date; max: Date } {
		const dates: Date[] = [];
		entries.forEach((entry) => {
			if (entry.start_date) dates.push(new Date(entry.start_date));
			if (entry.end_date) dates.push(new Date(entry.end_date));
		});

		if (dates.length === 0) {
			const now = new Date();
			return {
				min: new Date(now.getFullYear(), now.getMonth() - 1, 1),
				max: new Date(now.getFullYear(), now.getMonth() + 2, 0)
			};
		}

		return {
			min: new Date(Math.min(...dates.map((d) => d.getTime()))),
			max: new Date(Math.max(...dates.map((d) => d.getTime())))
		};
	}

	// Calculate position on timeline (percentage)
	function getDatePosition(date: string | null, minDate: Date, maxDate: Date): number {
		if (!date) return 0;
		const d = new Date(date).getTime();
		const min = minDate.getTime();
		const max = maxDate.getTime();
		return ((d - min) / (max - min)) * 100;
	}

	// State
	let useDummyData = $state(true);
	let ganttEntries = $derived(
		useDummyData
			? getDummyGanttEntries()
			: transformAppliedControlsToGanttEntries(data.appliedControls)
	);
	let ganttGroups = $derived(getGroupsFromEntries(ganttEntries));
	let dateRange = $derived(getDateRange(ganttEntries));
	let selectedFolder = $state<string>('');

	// Filtered entries
	let filteredEntries = $derived(
		selectedFolder
			? ganttEntries.filter((entry) => entry.folder_uuid === selectedFolder)
			: ganttEntries
	);

	// Format date for display
	function formatDate(date: Date): string {
		return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
	}
</script>

<div class="bg-white p-6 shadow-sm space-y-4">
	<div class="flex items-center justify-between">
		<div>
			<h2 class="h2 font-bold">Gantt Diagram</h2>
			<p class="text-sm text-gray-600">Visualize applied controls timeline</p>
		</div>

		<div class="flex gap-4 items-end">
			<!-- Data source toggle -->
			<div>
				<label class="block text-sm font-medium text-gray-900 mb-1">Data Source</label>
				<button
					type="button"
					class="btn {useDummyData ? 'preset-filled' : 'preset-outlined'}"
					onclick={() => (useDummyData = !useDummyData)}
				>
					<i class="fas {useDummyData ? 'fa-flask' : 'fa-database'} mr-2"></i>
					{useDummyData ? 'Demo Data' : 'Real Data'}
				</button>
			</div>

			<!-- Folder filter (only for real data) -->
			{#if !useDummyData}
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
						{#each data.folders as folder}
							<option value={folder.id}>{folder.str || folder.name}</option>
						{/each}
					</select>
				</div>
			{/if}
		</div>
	</div>

	<!-- Stats -->
	<div class="grid grid-cols-4 gap-4">
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

	{#if filteredEntries.length === 0}
		<div class="text-center py-12 text-gray-500">
			<i class="fas fa-calendar-alt text-4xl mb-4"></i>
			<p>No items with dates found. Applied controls need ETA or due dates to appear here.</p>
		</div>
	{:else}
		<!-- Timeline header -->
		<div class="border-t pt-4">
			<div class="flex items-center text-sm text-gray-600 mb-2">
				<div class="w-64 font-semibold">Name</div>
				<div class="flex-1 flex justify-between px-4">
					<span>{formatDate(dateRange.min)}</span>
					<span>{formatDate(dateRange.max)}</span>
				</div>
			</div>

			<!-- Gantt chart -->
			<div class="space-y-2">
				{#each filteredEntries as entry (entry.id)}
					<div class="flex items-center border-b pb-2">
						<!-- Entry name -->
						<div class="w-64 pr-4">
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

						<!-- Timeline visualization -->
						<div class="flex-1 relative h-8 bg-gray-50 rounded">
							{#if entry.type === 'milestone'}
								<!-- Milestone: single point -->
								<div
									class="absolute top-0 h-8 flex items-center justify-center"
									style="left: {getDatePosition(
										entry.end_date,
										dateRange.min,
										dateRange.max
									)}%; transform: translateX(-50%);"
								>
									<div class="w-4 h-4 bg-green-500 rotate-45 border-2 border-white shadow"></div>
								</div>
							{:else if entry.type === 'task'}
								<!-- Task: single day bar -->
								<div
									class="absolute top-1 h-6 bg-yellow-500 rounded shadow"
									style="left: {getDatePosition(
										entry.end_date,
										dateRange.min,
										dateRange.max
									)}%; width: 2px;"
								></div>
							{:else if entry.type === 'activity'}
								<!-- Control Implementation: range bar with progress -->
								{@const leftPos = getDatePosition(entry.start_date, dateRange.min, dateRange.max)}
								{@const rightPos = getDatePosition(entry.end_date, dateRange.min, dateRange.max)}
								{@const width = rightPos - leftPos}
								<div
									class="absolute top-1 h-6 bg-purple-200 rounded shadow"
									style="left: {leftPos}%; width: {width}%;"
								>
									<!-- Progress bar -->
									<div
										class="h-full bg-purple-500 rounded transition-all"
										style="width: {entry.progress}%;"
									></div>
								</div>
								<!-- Progress label -->
								<div
									class="absolute top-1 h-6 flex items-center justify-center text-xs font-semibold text-white"
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
