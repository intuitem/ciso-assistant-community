<script lang="ts">
	import type { PageData } from './$types';
	import GanttChart from '$lib/components/Gantt/GanttChart.svelte';
	import type { GanttEntry, Folder } from '$lib/components/Gantt/GanttChart.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

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

	// Compute entries from real data
	let ganttEntries = $derived([
		...transformAppliedControlsToGanttEntries(data.appliedControls),
		...transformTaskNodesToGanttEntries(data.taskNodes)
	]);

	// Transform folders to match component interface
	let folders: Folder[] = $derived(
		data.folders.map((f: any) => ({
			id: f.id,
			name: f.name,
			str: f.str
		}))
	);

	// URL builder for applied controls and tasks
	function itemUrlBuilder(entry: GanttEntry): string {
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
	<div>
		<h2 class="h2 font-bold">Gantt Diagram</h2>
		<p class="text-sm text-gray-600">Visualize applied controls timeline</p>
	</div>

	<!-- Gantt Chart Component -->
	<GanttChart entries={ganttEntries} {folders} {itemUrlBuilder} />
</div>
