<script>
	import GanttChart from '$lib/components/GanttChart.svelte';

	// Sample timeline data spanning two years
	const items = [
		{ id: 1, content: 'Project A', start: '2025-01-01', end: '2025-03-15', group: 1 },
		{ id: 2, content: 'Project B', start: '2025-02-15', end: '2025-06-30', group: 2 },
		{ id: 3, content: 'Milestone 1', start: '2025-04-01', type: 'point', group: 1 },
		{ id: 4, content: 'Project C', start: '2025-05-10', end: '2025-08-22', group: 3 },
		{ id: 5, content: 'Project D', start: '2025-07-01', end: '2025-12-31', group: 2 },
		{ id: 6, content: 'Milestone 2', start: '2025-09-15', type: 'point', group: 3 },
		{ id: 7, content: 'Project E', start: '2025-10-01', end: '2026-02-28', group: 1 },
		{ id: 8, content: 'Project F', start: '2026-01-15', end: '2026-07-31', group: 2 },
		{ id: 9, content: 'Milestone 3', start: '2026-03-01', type: 'point', group: 1 },
		{ id: 10, content: 'Project G', start: '2026-04-01', end: '2026-11-30', group: 3 }
	];

	// Groups for categorizing items
	const groups = [
		{ id: 1, content: 'Team Alpha' },
		{ id: 2, content: 'Team Beta' },
		{ id: 3, content: 'Team Gamma' }
	];

	// Timeline options with enhanced zoom capabilities
	const options = {
		editable: false,
		zoomable: true,
		zoomMin: 1000 * 60 * 60 * 24, // One day
		zoomMax: 1000 * 60 * 60 * 24 * 365 * 2, // Two years
		stack: true,
		selectable: true,
		// Adaptive time axis configuration
		timeAxis: { scale: 'day', step: 1 },
		// Configure the format of the time axis based on zoom level
		format: {
			minorLabels: {
				millisecond: 'SSS',
				second: 's',
				minute: 'HH:mm',
				hour: 'HH:mm',
				weekday: 'ddd D',
				day: 'D',
				month: 'MMM',
				year: 'YYYY'
			},
			majorLabels: {
				millisecond: 'HH:mm:ss',
				second: 'D MMMM HH:mm',
				minute: 'ddd D MMMM',
				hour: 'ddd D MMMM',
				weekday: 'MMMM YYYY',
				day: 'MMMM YYYY',
				month: 'YYYY',
				year: ''
			}
		}
	};
</script>

<svelte:head>
	<title>Timeline Example</title>
</svelte:head>

<div class="h-screen p-4">
	<h1 class="text-2xl mb-4">Vis.js Timeline in SvelteKit</h1>
	<div class="h-96">
		<GanttChart {items} {groups} {options} height="100%" width="100%" />
	</div>

	<div class="mt-4">
		<p>Zoom instructions:</p>
		<ul class="list-disc pl-6">
			<li>Mouse wheel to zoom in/out</li>
			<li>Ctrl + drag to move the timeline</li>
			<li>Click and drag to select a time range for zooming</li>
		</ul>
	</div>
</div>
