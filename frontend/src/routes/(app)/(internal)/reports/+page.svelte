<script lang="ts">
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';
	import ReportTile from './ReportTile.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	interface ReportTileData {
		id: string;
		title: string;
		description: string;
		icon: string;
		category: string;
		onClick?: () => void;
		href?: string;
		tags?: string[];
	}

	// Available report tiles
	const reportTiles: ReportTileData[] = [
		{
			id: 'dora-roi',
			title: 'DORA Register of Information',
			description:
				'Generate DORA-compliant Register of Information (ROI) containing entity data required by the Digital Operational Resilience Act',
			icon: 'fa-solid fa-building-shield',
			category: 'compliance',
			href: '/reports/dora-roi',
			tags: ['DORA', 'Regulation', 'Entities']
		},
		{
			id: 'compliance-summary',
			title: m.complianceSummaryReport ? m.complianceSummaryReport() : 'Compliance Summary Report',
			description: m.complianceSummaryReportDesc
				? m.complianceSummaryReportDesc()
				: 'Generate comprehensive compliance status across all frameworks',
			icon: 'fa-solid fa-clipboard-check',
			category: 'compliance',
			tags: ['Compliance', 'Frameworks', 'Audits']
		},
		{
			id: 'incident-analysis',
			title: m.incidentAnalysisReport ? m.incidentAnalysisReport() : 'Incident Analysis Report',
			description: m.incidentAnalysisReportDesc
				? m.incidentAnalysisReportDesc()
				: 'Comprehensive analysis of security incidents and trends',
			icon: 'fa-solid fa-bug',
			category: 'operations',
			tags: ['Incidents', 'Operations', 'Security']
		},
		{
			id: 'asset-inventory',
			title: m.assetInventoryReport ? m.assetInventoryReport() : 'Asset Inventory Report',
			description: m.assetInventoryReportDesc
				? m.assetInventoryReportDesc()
				: 'Complete inventory of assets and their risk profiles',
			icon: 'fa-solid fa-gem',
			category: 'assets',
			tags: ['Assets', 'Inventory', 'Risk']
		}
	];

	function handleTileClick(tile: ReportTileData): void {
		if (tile.onClick) {
			tile.onClick();
		} else {
			// Default action - will be implemented with backend
			console.log(`Report tile clicked: ${tile.id}`);
			// TODO: Navigate to report generation page or trigger report generation
		}
	}
</script>

<div class="px-4 py-6 space-y-6">
	<!-- Header -->

	<!-- Reports Grid with White Background -->
	<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			{#each reportTiles as tile}
				<ReportTile
					title={tile.title}
					description={tile.description}
					icon={tile.icon}
					category={tile.category}
					href={tile.href}
					tags={tile.tags}
					onclick={tile.href ? undefined : () => handleTileClick(tile)}
				/>
			{/each}
		</div>
	</div>

	<!-- Info Section -->
	<div class="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border border-gray-200 p-6">
		<div class="flex items-start gap-4">
			<div class="flex-shrink-0">
				<i class="fas fa-info-circle text-2xl text-blue-600"></i>
			</div>
			<div>
				<h3 class="text-lg font-semibold text-gray-900 mb-2">
					{m.aboutReports ? m.aboutReports() : 'About Reports'}
				</h3>
				<p class="text-gray-700">
					{m.aboutReportsDescription
						? m.aboutReportsDescription()
						: 'Reports provide a simple tools to generate specialized reports useful for key insights or required by authorities for specific standards.\nMore specialized capabilities will be added as we identify specific cases.'}
				</p>
			</div>
		</div>
	</div>
</div>
