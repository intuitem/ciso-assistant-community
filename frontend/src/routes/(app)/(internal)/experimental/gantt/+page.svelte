<script lang="ts">
	import type { PageData } from './$types';
	import GanttChart from '$lib/components/Gantt/GanttChart.svelte';
	import type { GanttEntry, Folder } from '$lib/components/Gantt/GanttChart.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

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

	// Transform applied controls to Gantt entries (Control Implementation)
	function transformAppliedControlsToGanttEntries(appliedControls: any[]): GanttEntry[] {
		return appliedControls
			.filter((control) => control.start_date || control.eta)
			.map((control) => {
				// Determine type based on dates
				let type: 'milestone' | 'task' | 'activity' = 'milestone';
				let start_date = null;
				let end_date = null;

				if (control.start_date && control.eta) {
					// Both dates -> activity (Control Implementation)
					type = 'activity';
					start_date = control.start_date;
					end_date = control.eta;
				} else if (control.start_date || control.eta) {
					// Single date -> milestone
					type = 'milestone';
					end_date = control.eta || control.start_date;
				}

				// Calculate progress based on status
				let progress = 0;
				if (control.status === 'active') progress = 100;
				else if (control.status === 'in_progress') progress = 50;

				return {
					id: `control-${control.id}`,
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

	// Transform task nodes to Gantt entries (Tasks)
	function transformTaskNodesToGanttEntries(taskNodes: any[]): GanttEntry[] {
		return taskNodes
			.filter((task) => task.due_date)
			.map((task) => {
				// Tasks are single-day items with only due_date
				return {
					id: `task-${task.id}`,
					name: task.name || 'Unnamed Task',
					type: 'task' as const,
					start_date: null,
					end_date: task.due_date,
					progress: 0,
					description: task.description || '',
					ref_id: '',
					folder_uuid: task.folder?.id || '',
					group_id: null
				};
			});
	}

	// State for dummy data toggle (default to real data)
	let useDummyData = $state(false);

	// Compute entries based on data source
	let ganttEntries = $derived(
		useDummyData
			? getDummyGanttEntries()
			: [
					...transformAppliedControlsToGanttEntries(data.appliedControls),
					...transformTaskNodesToGanttEntries(data.taskNodes)
				]
	);

	// Transform folders to match component interface
	let folders: Folder[] = $derived(
		data.folders.map((f: any) => ({
			id: f.id,
			name: f.name,
			str: f.str
		}))
	);

	// URL builder for real data (applied controls and tasks)
	function itemUrlBuilder(entry: GanttEntry): string {
		if (useDummyData) {
			return '#';
		}

		// Extract the actual ID (remove prefix)
		if (entry.id.startsWith('control-')) {
			const controlId = entry.id.replace('control-', '');
			return `/applied-controls/${controlId}`;
		} else if (entry.id.startsWith('task-')) {
			const taskId = entry.id.replace('task-', '');
			return `/task-nodes/${taskId}`;
		}

		return '#';
	}
</script>

<div class="bg-white p-6 shadow-sm space-y-4">
	<div class="flex items-center justify-between">
		<div>
			<h2 class="h2 font-bold">Gantt Diagram</h2>
			<p class="text-sm text-gray-600">Visualize applied controls timeline</p>
		</div>

		<!-- Data source toggle -->
		<div>
			<label class="block text-sm font-medium text-gray-900 mb-1">Data Source</label>
			<button
				type="button"
				class="btn btn-sm {useDummyData ? 'preset-filled' : 'preset-outlined'}"
				onclick={() => (useDummyData = !useDummyData)}
			>
				<i class="fas {useDummyData ? 'fa-flask' : 'fa-database'} mr-2"></i>
				{useDummyData ? 'Demo' : 'Real'}
			</button>
		</div>
	</div>

	<!-- Gantt Chart Component -->
	<GanttChart entries={ganttEntries} {folders} {itemUrlBuilder} />
</div>
