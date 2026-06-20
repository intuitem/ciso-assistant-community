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
			title: m.doraRegisterOfInformation(),
			description: m.doraRoiDescription(),
			icon: 'fa-solid fa-building-shield',
			category: 'compliance',
			href: '/reports/dora-roi',
			tags: ['DORA', 'Regulation', 'Entities']
		},
		{
			id: 'soa',
			title: m.statementOfApplicability(),
			description: m.soaDescription(),
			icon: 'fa-solid fa-clipboard-check',
			category: 'compliance',
			href: '/reports/soa',
			tags: ['ISO 27001', 'Compliance', 'Controls']
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

<div class="space-y-6">
	<!-- Header -->

	<!-- Reports Grid with White Background -->
	<div class="bg-surface-50-950 card border border-surface-200-800 p-6">
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
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
	<div
		class="bg-gradient-to-br from-surface-50-950 to-surface-100-900 card border border-surface-200-800 p-6"
	>
		<div class="flex items-start gap-4">
			<div class="flex-shrink-0">
				<i class="fas fa-info-circle text-2xl text-blue-600"></i>
			</div>
			<div>
				<h3 class="text-lg font-semibold text-surface-950-50 mb-2">
					{m.aboutReports()}
				</h3>
				<p class="text-surface-700-300 whitespace-pre-line">
					{m.aboutReportsDescription()}
				</p>
			</div>
		</div>
	</div>
</div>
