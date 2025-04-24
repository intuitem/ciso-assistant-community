<script>
	import { onMount } from 'svelte';
	import Gantt from 'frappe-gantt';
	let mounted = false;
	let gantt;

	let groups = [{ id: 'website', name: 'website', bar_class: 'bar-website' }];
	let tasks = [
		{
			id: '1',
			name: 'Redesign website',
			start: '2025-01-01',
			end: '2025-10-31',
			progress: 80,
			group_id: 'website'
		},
		{
			id: '2',
			name: 'Other stuff on the website',
			start: '2025-12-01',
			end: '2025-12-31',
			progress: 20,
			group_id: 'website'
		},
		{
			id: '3',
			name: 'Clean up the warehouse',
			start: '2025-10-01',
			end: '2025-12-31',
			progress: 50,
			group_id: 'warehouse'
		}
	];

	onMount(async () => {
		gantt = new Gantt('#gantt', tasks, {
			groups: groups,
			view_mode: 'Month',
			date_format: 'YYYY-MM-DD',
			infinite_padding: false,
			readonly_dates: true,
			readonly_progress: true,
			view_mode_select: true,
			holidays: [] //this is for disabling the grayed weekend
		});

		mounted = true;
	});
</script>

<main class="w-full">
	<!-- Render container always; render content via JS only after mount -->
	<div id="gantt"></div>
</main>

<style>
	#gantt {
		width: 100%;
		height: 800px;
		margin-bottom: 20px;
	}
	.bar-website {
		border: 4pt;
	}
</style>
