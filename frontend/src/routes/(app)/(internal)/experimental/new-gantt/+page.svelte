<script>
	import { onMount } from 'svelte';
	import moment from 'moment';
	import { SvelteGantt, SvelteGanttTable, MomentSvelteGanttDateAdapter } from 'svelte-gantt/svelte';

	let currentStart;
	let currentEnd;
	let options;
	let mounted = false;

	function time(input) {
		return moment(input, 'HH:mm');
	}

	onMount(() => {
		currentStart = time('06:00');
		currentEnd = time('18:00');

		const data = {
			rows: [
				{
					id: 1,
					label: 'Room 1',
					draggable: false
				},
				{
					id: 2,
					label: 'Room 2',
					draggable: false
				},
				{
					id: 3,
					label: 'Room 3',
					draggable: false
				},
				{
					id: 4,
					label: 'Room 4',
					draggable: false
				},
				{
					id: 5,
					label: 'Room 5',
					draggable: false
				}
			],
			tasks: [
				{
					id: 3,
					resourceId: 1,
					label: 'simple',
					from: time('09:30'),
					to: time('12:00'),
					resizable: false
				},
				{
					id: 4,
					resourceId: 2,
					label: 'simple',
					from: time('08:00'),
					to: time('10:00'),
					resizable: false
				},
				{
					id: 5,
					resourceId: 1,
					label: 'simple',
					from: time('13:00'),
					to: time('14:00'),
					resizable: false
				},
				{
					id: 6,
					resourceId: 3,
					label: 'simple',
					from: time('09:00'),
					to: time('11:00'),
					resizable: false
				}
			],
			dependencies: []
		};

		options = {
			dateAdapter: new MomentSvelteGanttDateAdapter(moment),
			rows: data.rows,
			tasks: data.tasks,
			dependencies: data.dependencies,
			timeRanges: [],
			columnUnit: 'minute',
			columnOffset: 30,
			magnetOffset: 15,
			rowHeight: 75,
			rowPadding: 5,
			layout: 'expand',
			headers: [
				{ unit: 'day', format: 'MMMM Do', sticky: true },
				{ unit: 'hour', format: 'H:mm', sticky: true }
			],
			fitWidth: true,
			minWidth: 800,
			from: currentStart,
			to: currentEnd,
			tableHeaders: [{ title: 'All Rooms', property: 'label', width: 140, type: 'tree' }],
			tableWidth: 100,
			ganttTableModules: [SvelteGanttTable]
		};

		mounted = true;
	});
</script>

<main class="w-full">
	{#if mounted}
		<div>
			<SvelteGantt {...options}></SvelteGantt>
		</div>
	{/if}
</main>

<style scoped>
	:global(.header-container) {
		pointer-events: none;
	}

	:global(.sg-task-content) {
		width: 100%;
		padding-right: 14px;
	}
</style>
