<script lang="ts">
	import { onMount } from 'svelte';
	import Gantt from 'frappe-gantt';

	export let tasks;
	export let lang = 'en';
	let mounted = false;

	let gantt;

	onMount(() => {
		gantt = new Gantt('#gantt', tasks, {
			view_mode: 'Month',
			date_format: 'YYYY-MM-DD',
			language: lang,
			infinite_padding: false,
			readonly_dates: true,
			readonly_progress: true,
			view_mode_select: true,
			popup_on: 'click',
			holidays: [], //this is to remove the grayed weekends
			popup: ({ task, set_details, add_action }) => {
				set_details(`
          <p class="text-black text-sm">${task.name}</p>
          <p>${task.description}</p>
					<p><span class="text-black">Start:</span> ${task.start}</p>
					<p><span class="text-black">End:</span> ${task.end}</p>
					<p>Progress: ${task.progress || 0}%</p>
				`);

				add_action(
					`<a href="/applied-controls/${task.id}" target="_blank" style="color:blue;">🔗 View Details</a>`
				);
			}
		});

		mounted = true;
		// this is a compensation for the issue with Today in Weekly view
		setTimeout(() => {
			gantt.change_view_mode('Week', true);
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
