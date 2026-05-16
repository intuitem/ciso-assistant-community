<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	$pageTitle = 'Analytics Export';
</script>

<div class="p-4 space-y-4">
	<div>
		<h2 class="text-lg font-semibold text-gray-900">Analytics Export</h2>
		<p class="text-sm text-gray-600">
			Export all analytics dashboard data as a multi-sheet Excel file (Summary, Risk Levels,
			Compliance, Controls, Incidents) — ready to use in Power BI or any reporting tool.
		</p>
	</div>

	<a
		href="/analytics/export/xlsx"
		class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 hover:text-gray-900 transition-colors shadow-sm"
		download
	>
		<i class="fa-solid fa-file-excel text-green-600"></i>
		{m.exportButton() + ' ' + m.asXLSX()}
	</a>
</div>
