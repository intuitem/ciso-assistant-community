<script lang="ts">
	import CalendarHeatmap from '$lib/components/Chart/CalendarHeatmap.svelte';

	const currentYear = new Date().getFullYear();
</script>

<main class="p-8 space-y-8">
	<div>
		<h1 class="text-3xl font-bold mb-2">Calendar Activity Heatmap</h1>
		<p class="text-gray-600 mb-8">
			Experimental calendar heatmap using ECharts 6 - GitHub-style activity visualization
		</p>
	</div>

	<div class="bg-white rounded-lg shadow p-6">
		<CalendarHeatmap
			name="current_year"
			year={currentYear}
			title="Current Year Activity ({currentYear})"
			height="h-80"
		/>
	</div>
</main>
