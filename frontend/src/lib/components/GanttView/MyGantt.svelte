<script lang="ts">
	import { onMount } from 'svelte';
	import Gantt from 'frappe-gantt';

	export let tasks;
	export let lang = 'en';
	let mounted = false;

	let gantt;

	onMount(async () => {
		// Set viewMode to 'Week' before rendering
		gantt = new Gantt('#gantt', tasks, {
			view_mode: 'Month',
			date_format: 'YYYY-MM-DD',
			language: lang,
			infinite_padding: false,
			readonly_dates: true,
			readonly_progress: true,
			view_mode_select: true,
			popup_on: 'hover',
			holidays: [] //this is for disabling the grayed weekend
		});

		mounted = true;

		// this is a compensation for the Today button issue in weekly view
		setTimeout(() => {
			gantt.change_view_mode('Week', true); // Change the view in the Gantt object
			gantt.scroll_current();
		}, 300);
	});
</script>

<svelte:head>
	<link rel="stylesheet" href="/vendor/frappe-gantt.css" />
</svelte:head>

<main class="w-full h-dvh p-2">
	<!-- Render container always; render content via JS only after mount -->
	<div id="gantt" class="mb-10"></div>
</main>
