<script lang="ts">
	import TreemapChart from '$lib/components/Chart/TreemapChart.svelte';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	$pageTitle = m.vulnerabilityTreemap();

	// Define available severities and statuses based on actual Vulnerability model (lowercase keys from backend)
	const severityOptions = ['critical', 'high', 'medium', 'low', 'info', 'undefined'];
	const statusOptions = [
		'potential',
		'exploitable',
		'mitigated',
		'fixed',
		'not_exploitable',
		'unaffected',
		'--'
	];

	// State for filters - exclude Undefined by default
	let selectedSeverities = $state<string[]>(['critical', 'high', 'medium', 'low', 'info']);
	let selectedStatuses = $state<string[]>([
		'potential',
		'exploitable',
		'mitigated',
		'fixed',
		'not_exploitable',
		'unaffected'
	]);

	// Function to filter and translate data for display
	function filterTreemapData(rawData: any[]) {
		if (!Array.isArray(rawData)) {
			return [];
		}

		return rawData
			.map((domain) => {
				const filteredChildren = domain.children
					.filter((severity: any) => selectedSeverities.includes(severity.name))
					.map((severity: any) => ({
						...severity,
						name: safeTranslate(severity.name), // Translate severity for display
						children: severity.children
							.filter((status: any) => selectedStatuses.includes(status.name))
							.map((status: any) => ({
								...status,
								name: safeTranslate(status.name) // Translate status for display
							}))
					}))
					.filter((severity: any) => severity.children.length > 0);

				return {
					...domain,
					children: filteredChildren
				};
			})
			.filter((domain) => domain.children.length > 0);
	}

	function toggleSeverity(severity: string) {
		if (selectedSeverities.includes(severity)) {
			selectedSeverities = selectedSeverities.filter((s) => s !== severity);
		} else {
			selectedSeverities = [...selectedSeverities, severity];
		}
	}

	function toggleStatus(status: string) {
		if (selectedStatuses.includes(status)) {
			selectedStatuses = selectedStatuses.filter((s) => s !== status);
		} else {
			selectedStatuses = [...selectedStatuses, status];
		}
	}

	function selectAllSeverities() {
		selectedSeverities = [...severityOptions];
	}

	function clearAllSeverities() {
		selectedSeverities = [];
	}

	function selectAllStatuses() {
		selectedStatuses = [...statusOptions];
	}

	function clearAllStatuses() {
		selectedStatuses = [];
	}

	// Severity colors for visual consistency (using lowercase keys)
	const severityColors: Record<string, string> = {
		critical: 'bg-red-500 text-white border-red-600 hover:bg-red-600',
		high: 'bg-orange-500 text-white border-orange-600 hover:bg-orange-600',
		medium: 'bg-yellow-500 text-white border-yellow-600 hover:bg-yellow-600',
		low: 'bg-blue-500 text-white border-blue-600 hover:bg-blue-600',
		info: 'bg-gray-500 text-white border-gray-600 hover:bg-gray-600',
		undefined: 'bg-slate-500 text-white border-slate-600 hover:bg-slate-600'
	};

	// Inactive severity colors
	const severityColorsInactive: Record<string, string> = {
		critical: 'bg-red-50 text-red-400 border-red-200 hover:bg-red-100',
		high: 'bg-orange-50 text-orange-400 border-orange-200 hover:bg-orange-100',
		medium: 'bg-yellow-50 text-yellow-400 border-yellow-200 hover:bg-yellow-100',
		low: 'bg-blue-50 text-blue-400 border-blue-200 hover:bg-blue-100',
		info: 'bg-gray-50 text-gray-400 border-gray-200 hover:bg-gray-100',
		undefined: 'bg-slate-50 text-slate-400 border-slate-200 hover:bg-slate-100'
	};

	// Status colors based on vulnerability lifecycle (using raw status values)
	const statusColors: Record<string, string> = {
		potential: 'bg-yellow-500 text-white border-yellow-600 hover:bg-yellow-600',
		exploitable: 'bg-red-500 text-white border-red-600 hover:bg-red-600',
		mitigated: 'bg-blue-500 text-white border-blue-600 hover:bg-blue-600',
		fixed: 'bg-green-500 text-white border-green-600 hover:bg-green-600',
		not_exploitable: 'bg-teal-500 text-white border-teal-600 hover:bg-teal-600',
		unaffected: 'bg-emerald-500 text-white border-emerald-600 hover:bg-emerald-600',
		'--': 'bg-slate-500 text-white border-slate-600 hover:bg-slate-600'
	};

	// Inactive status colors
	const statusColorsInactive: Record<string, string> = {
		potential: 'bg-yellow-50 text-yellow-400 border-yellow-200 hover:bg-yellow-100',
		exploitable: 'bg-red-50 text-red-400 border-red-200 hover:bg-red-100',
		mitigated: 'bg-blue-50 text-blue-400 border-blue-200 hover:bg-blue-100',
		fixed: 'bg-green-50 text-green-400 border-green-200 hover:bg-green-100',
		not_exploitable: 'bg-teal-50 text-teal-400 border-teal-200 hover:bg-teal-100',
		unaffected: 'bg-emerald-50 text-emerald-400 border-emerald-200 hover:bg-emerald-100',
		'--': 'bg-slate-50 text-slate-400 border-slate-200 hover:bg-slate-100'
	};
</script>

<div class="bg-white p-6 h-screen overflow-auto">
	<!-- Filters Section -->
	<div class="mb-6 space-y-6 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
		<!-- Severity Filters -->
		<div>
			<div class="flex items-center justify-between mb-3">
				<div>
					<label class="text-base font-semibold text-gray-900">{m.severity()}</label>
					<p class="text-xs text-gray-500 mt-0.5">{m.filterVulnerabilitiesBySeverity()}</p>
				</div>
				<div class="flex gap-2">
					<button
						onclick={selectAllSeverities}
						class="text-xs px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium shadow-sm"
					>
						{m.selectAll()}
					</button>
					<button
						onclick={clearAllSeverities}
						class="text-xs px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
					>
						{m.clear()}
					</button>
				</div>
			</div>
			<div class="flex flex-wrap gap-2">
				{#each severityOptions as severity}
					<button
						onclick={() => toggleSeverity(severity)}
						class="px-4 py-2 rounded-lg border-2 transition-all duration-200 font-medium text-sm shadow-sm {selectedSeverities.includes(
							severity
						)
							? severityColors[severity] + ' ring-2 ring-offset-1 ring-current'
							: severityColorsInactive[severity]}"
					>
						{safeTranslate(severity)}
						{#if selectedSeverities.includes(severity)}
							<i class="fas fa-check ml-1.5 text-xs"></i>
						{/if}
					</button>
				{/each}
			</div>
		</div>

		<!-- Divider -->
		<div class="border-t border-gray-200"></div>

		<!-- Status Filters -->
		<div>
			<div class="flex items-center justify-between mb-3">
				<div>
					<label class="text-base font-semibold text-gray-900">{m.status()}</label>
					<p class="text-xs text-gray-500 mt-0.5">{m.filterVulnerabilitiesByStatus()}</p>
				</div>
				<div class="flex gap-2">
					<button
						onclick={selectAllStatuses}
						class="text-xs px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium shadow-sm"
					>
						{m.selectAll()}
					</button>
					<button
						onclick={clearAllStatuses}
						class="text-xs px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
					>
						{m.clear()}
					</button>
				</div>
			</div>
			<div class="flex flex-wrap gap-2">
				{#each statusOptions as status}
					<button
						onclick={() => toggleStatus(status)}
						class="px-4 py-2 rounded-lg border-2 transition-all duration-200 font-medium text-sm shadow-sm {selectedStatuses.includes(
							status
						)
							? statusColors[status] + ' ring-2 ring-offset-1 ring-current'
							: statusColorsInactive[status]}"
					>
						{safeTranslate(status)}
						{#if selectedStatuses.includes(status)}
							<i class="fas fa-check ml-1.5 text-xs"></i>
						{/if}
					</button>
				{/each}
			</div>
		</div>
	</div>

	<!-- Treemap -->
	<div class="h-[calc(100vh-400px)]">
		{#await data.stream.treemapData}
			<div class="flex items-center justify-center h-full">
				<LoadingSpinner />
			</div>
		{:then loadedData}
			{#key `${selectedSeverities.join(',')}-${selectedStatuses.join(',')}`}
				{@const filteredData = filterTreemapData(loadedData)}
				{#if filteredData.length === 0}
					<div class="flex items-center justify-center h-full text-gray-500">
						{m.noDataMatchesFilters()}
					</div>
				{:else}
					<TreemapChart
						tree={filteredData}
						name="vulnerability_treemap"
						title={m.clickToDrillDown()}
					/>
				{/if}
			{/key}
		{:catch error}
			<div class="flex items-center justify-center h-full text-red-500">
				{m.failedToLoadVulnerabilityData()}: {error.message}
			</div>
		{/await}
	</div>
</div>
