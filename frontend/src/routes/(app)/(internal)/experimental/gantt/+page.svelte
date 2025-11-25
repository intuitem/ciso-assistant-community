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

	// Transform applied controls to Gantt entries
	function transformAppliedControlsToGanttEntries(appliedControls: any[]): GanttEntry[] {
		return appliedControls
			.filter((control) => control.eta || control.due_date)
			.map((control) => {
				// Determine type based on dates
				let type: 'milestone' | 'task' | 'activity' = 'task';
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

	// State for dummy data toggle
	let useDummyData = $state(true);

	// Compute entries based on data source
	let ganttEntries = $derived(
		useDummyData
			? getDummyGanttEntries()
			: transformAppliedControlsToGanttEntries(data.appliedControls)
	);

	// Transform folders to match component interface
	let folders: Folder[] = $derived(
		data.folders.map((f: any) => ({
			id: f.id,
			name: f.name,
			str: f.str
		}))
	);

	// URL builder for real applied controls
	function itemUrlBuilder(entry: GanttEntry): string {
		if (useDummyData) {
			return '#';
		}
		return `/applied-controls/${entry.id}`;
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
