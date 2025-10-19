<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import TimelineTable from '$lib/components/BIA/TimelineTable.svelte';
	import ActivityTracker from '$lib/components/DataViz/ActivityTracker.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	$effect(() => {
		const handlePrint = () => {
			document.documentElement.classList.add('is-printing');
		};
		const handleAfterPrint = () => {
			document.documentElement.classList.remove('is-printing');
		};
		window.addEventListener('beforeprint', handlePrint);
		window.addEventListener('afterprint', handleAfterPrint);

		return () => {
			window.removeEventListener('beforeprint', handlePrint);
			window.removeEventListener('afterprint', handleAfterPrint);
		};
	});

	let { data }: Props = $props();
	pageTitle.set('Business Impact Analysis Report');

	const { bia, timelineData, metrics, assets, appliedControls } = data;

	function exportPDF() {
		window.print();
	}

	// Helper functions for objectives vs capabilities table
	function formatComparison(comparison: any[], field: 'expectation' | 'reality'): string {
		const items = comparison
			.map((c: any) => {
				const value = c[field];
				if (value === null || value === undefined) return null;
				return `${safeTranslate(c.objective)}: ${value}`;
			})
			.filter((item: any) => item !== null);
		return items.length > 0 ? items.join('\n') : '';
	}

	function getSecurityObjectives(asset: any): string {
		return formatComparison(asset.security_objectives_comparison || [], 'expectation');
	}

	function getSecurityCapabilities(asset: any): string {
		return formatComparison(asset.security_objectives_comparison || [], 'reality');
	}

	function getRecoveryObjectives(asset: any): string {
		return formatComparison(asset.recovery_objectives_comparison || [], 'expectation');
	}

	function getRecoveryCapabilities(asset: any): string {
		return formatComparison(asset.recovery_objectives_comparison || [], 'reality');
	}

	function getOverallVerdict(asset: any): boolean | null {
		const securityComparison = asset.security_objectives_comparison || [];
		const recoveryComparison = asset.recovery_objectives_comparison || [];
		const allComparisons = [...securityComparison, ...recoveryComparison];

		if (allComparisons.length === 0) return null;

		const hasFailed = allComparisons.some((c: any) => c.verdict === false);
		if (hasFailed) return false;

		const hasPassed = allComparisons.some((c: any) => c.verdict === true);
		if (hasPassed) return true;

		return null;
	}
</script>

<div class="bg-white shadow-sm p-4 px-8 mx-auto relative">
	<!-- Back to BIA Link and Export Button -->
	<div class="mb-4 flex justify-between items-center no-print">
		<Anchor
			breadcrumbAction="push"
			href={`/business-impact-analysis/${bia.id}`}
			class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
		>
			<i class="fa-solid fa-arrow-left"></i>
			<p>{m.back()}</p>
		</Anchor>
		<button
			onclick={exportPDF}
			class="btn preset-filled-primary-500 flex items-center gap-2 no-print"
		>
			<i class="fa-solid fa-file-pdf"></i>
			<span>{m.exportPdf()}</span>
		</button>
	</div>

	<!-- Section 1: BIA Header -->
	<section class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 mb-2">{bia.name}</h1>
		{#if bia.description}
			<div class="text-gray-600 mb-4">
				<MarkdownRenderer content={bia.description} />
			</div>
		{/if}
		<div class="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm mb-6">
			<div>
				<span class="font-semibold text-gray-700">{m.version()}:</span>
				<span class="ml-2">{bia.version || 'N/A'}</span>
			</div>
			<div>
				<span class="font-semibold text-gray-700">{m.status()}:</span>
				<span class="ml-2">{bia.status ? safeTranslate(bia.status) : 'N/A'}</span>
			</div>
			<div>
				<span class="font-semibold text-gray-700">{m.referenceScale()}:</span>
				<span class="ml-2">{bia.risk_matrix?.str || 'N/A'}</span>
			</div>
		</div>

		<!-- Assets Included -->
		{#if assets && assets.length > 0}
			<div class="mb-4">
				<h3 class="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
					<i class="fa-solid fa-server"></i>
					{m.assets()}
					<span class="badge preset-tonal-secondary text-xs">{assets.length}</span>
				</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
					{#each assets as assetAssessment}
						<div
							class="border border-gray-200 rounded-lg p-3 bg-gray-50 hover:shadow-md transition-shadow"
						>
							<div class="flex items-start gap-2">
								{#if assetAssessment.asset.type === 'PR'}
									<i class="fa-solid fa-briefcase text-blue-500 mt-1"></i>
								{:else}
									<i class="fa-solid fa-cube text-blue-500 mt-1"></i>
								{/if}
								<div class="flex-1">
									<div class="font-semibold text-gray-900">{assetAssessment.asset.name}</div>
									{#if assetAssessment.asset.folder}
										<div class="text-xs text-gray-600">
											<span class="font-medium">{m.domain()}:</span>
											<span class="ml-1">{assetAssessment.asset.folder.str}</span>
										</div>
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</section>

	<!-- Section 2: Timeline Table -->
	<section class="mb-8 page-break-section">
		<h2 class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2">
			{m.impactOverTime()}
		</h2>
		<TimelineTable data={timelineData} />
	</section>

	<!-- Section 3: Recovery Insights -->
	<section class="mb-8 page-break-section">
		<h2 class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2">
			{m.recoveryInsights()}
		</h2>
		<div class="flex items-center justify-center bg-gray-50 rounded-lg p-6 mb-6">
			<ActivityTracker {metrics} />
		</div>

		<!-- Asset Assessment Status Table -->
		{#if assets && assets.length > 0}
			<div class="overflow-x-auto">
				<table class="min-w-full bg-white border border-gray-200 rounded-lg">
					<thead class="bg-gray-100">
						<tr>
							<th class="px-4 py-3 text-left text-sm font-semibold text-gray-700 border-b"
								>{m.asset()}</th
							>
							<th class="px-4 py-3 text-center text-sm font-semibold text-gray-700 border-b"
								>{m.documented()}</th
							>
							<th class="px-4 py-3 text-center text-sm font-semibold text-gray-700 border-b"
								>{m.tested()}</th
							>
							<th class="px-4 py-3 text-center text-sm font-semibold text-gray-700 border-b"
								>{m.objectivesMet()}</th
							>
						</tr>
					</thead>
					<tbody>
						{#each assets as assetAssessment}
							<tr class="border-b hover:bg-gray-50">
								<td class="px-4 py-3 text-sm font-medium text-gray-900">
									{assetAssessment.asset.name}
								</td>
								<td class="px-4 py-3 text-center">
									<span
										class="inline-flex items-center justify-center w-6 h-6 rounded-full"
										class:bg-green-500={assetAssessment.recovery_documented}
										class:bg-gray-400={!assetAssessment.recovery_documented}
									>
										{#if assetAssessment.recovery_documented}
											<i class="fa-solid fa-check text-white text-xs"></i>
										{:else}
											<i class="fa-solid fa-xmark text-white text-xs"></i>
										{/if}
									</span>
								</td>
								<td class="px-4 py-3 text-center">
									<span
										class="inline-flex items-center justify-center w-6 h-6 rounded-full"
										class:bg-green-500={assetAssessment.recovery_tested}
										class:bg-gray-400={!assetAssessment.recovery_tested}
									>
										{#if assetAssessment.recovery_tested}
											<i class="fa-solid fa-check text-white text-xs"></i>
										{:else}
											<i class="fa-solid fa-xmark text-white text-xs"></i>
										{/if}
									</span>
								</td>
								<td class="px-4 py-3 text-center">
									<span
										class="inline-flex items-center justify-center w-6 h-6 rounded-full"
										class:bg-green-500={assetAssessment.recovery_targets_met}
										class:bg-gray-400={!assetAssessment.recovery_targets_met}
									>
										{#if assetAssessment.recovery_targets_met}
											<i class="fa-solid fa-check text-white text-xs"></i>
										{:else}
											<i class="fa-solid fa-xmark text-white text-xs"></i>
										{/if}
									</span>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>

	<!-- Section 4: Objectives vs Capabilities Comparison -->
	<section class="mb-8 page-break-section">
		<h2 class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2">
			{m.objectivesVsCapabilities()}
		</h2>
		{#if assets && assets.length > 0}
			<div class="overflow-x-auto">
				<table class="min-w-full bg-white border border-gray-200 rounded-lg">
					<thead class="bg-gray-100">
						<tr>
							<th
								rowspan="2"
								class="px-4 py-3 text-left text-sm font-semibold text-gray-700 border-b align-middle"
								>{m.asset()}</th
							>
							<th
								colspan="2"
								class="px-4 py-3 text-center text-sm font-semibold text-gray-700 border-b border-l"
								>{m.security()}</th
							>
							<th
								colspan="2"
								class="px-4 py-3 text-center text-sm font-semibold text-gray-700 border-b border-l"
								>{m.recovery()}</th
							>
							<th
								rowspan="2"
								class="px-4 py-3 text-center text-sm font-semibold text-gray-700 border-b border-l align-middle"
								>{m.alignment()}</th
							>
						</tr>
						<tr>
							<th class="px-4 py-2 text-center text-xs font-medium text-gray-600 border-b border-l"
								>{m.objective()}</th
							>
							<th class="px-4 py-2 text-center text-xs font-medium text-gray-600 border-b"
								>{m.capability()}</th
							>
							<th class="px-4 py-2 text-center text-xs font-medium text-gray-600 border-b border-l"
								>{m.objective()}</th
							>
							<th class="px-4 py-2 text-center text-xs font-medium text-gray-600 border-b"
								>{m.capability()}</th
							>
						</tr>
					</thead>
					<tbody>
						{#each assets as assetAssessment}
							{@const verdict = getOverallVerdict(assetAssessment.asset)}
							{@const securityObjectives = getSecurityObjectives(assetAssessment.asset)}
							{@const securityCapabilities = getSecurityCapabilities(assetAssessment.asset)}
							{@const recoveryObjectives = getRecoveryObjectives(assetAssessment.asset)}
							{@const recoveryCapabilities = getRecoveryCapabilities(assetAssessment.asset)}
							<tr class="border-b hover:bg-gray-50">
								<td class="px-4 py-3 text-sm font-medium text-gray-900">
									{assetAssessment.asset.name}
								</td>
								<td class="px-4 py-3 text-xs text-gray-700 border-l whitespace-pre-line align-top">
									{securityObjectives || '--'}
								</td>
								<td class="px-4 py-3 text-xs text-gray-700 whitespace-pre-line align-top">
									{securityCapabilities || '--'}
								</td>
								<td class="px-4 py-3 text-xs text-gray-700 border-l whitespace-pre-line align-top">
									{recoveryObjectives || '--'}
								</td>
								<td class="px-4 py-3 text-xs text-gray-700 whitespace-pre-line align-top">
									{recoveryCapabilities || '--'}
								</td>
								<td class="px-4 py-3 text-center border-l align-middle">
									{#if verdict !== null}
										<span
											class="inline-flex items-center justify-center w-6 h-6 rounded-full"
											class:bg-green-500={verdict === true}
											class:bg-red-500={verdict === false}
										>
											{#if verdict === true}
												<i class="fa-solid fa-check text-white text-xs"></i>
											{:else}
												<i class="fa-solid fa-xmark text-white text-xs"></i>
											{/if}
										</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>

	<!-- Section 5: Applied Controls -->
	{#if appliedControls && appliedControls.length > 0}
		<section class="mb-8 page-break-section">
			<h2 class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2">
				{m.appliedControls()}
			</h2>
			<div class="overflow-x-auto">
				<table class="min-w-full bg-white border border-gray-200 rounded-lg">
					<thead class="bg-gray-100">
						<tr>
							<th class="px-4 py-3 text-left text-sm font-semibold text-gray-700 border-b"
								>{m.name()}</th
							>
							<th class="px-4 py-3 text-left text-sm font-semibold text-gray-700 border-b"
								>{m.folder()}</th
							>
							<th class="px-4 py-3 text-left text-sm font-semibold text-gray-700 border-b"
								>{m.status()}</th
							>
							<th class="px-4 py-3 text-left text-sm font-semibold text-gray-700 border-b"
								>{m.eta()}</th
							>
						</tr>
					</thead>
					<tbody>
						{#each appliedControls as control}
							<tr class="border-b hover:bg-gray-50">
								<td class="px-4 py-3 text-sm text-gray-900">{control.str || control.name}</td>
								<td class="px-4 py-3 text-sm text-gray-900">{control.folder.str}</td>
								<td class="px-4 py-3 text-sm text-gray-700">
									{control.status ? safeTranslate(control.status) : '--'}
								</td>
								<td class="px-4 py-3 text-sm text-gray-700">
									{control.eta ? formatDateOrDateTime(control.eta) : '--'}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}
</div>

<style>
	:global(html) {
		scroll-behavior: smooth;
	}

	/* Print styles for PDF export */
	@media print {
		/* Hide elements that shouldn't be printed */
		:global(.no-print),
		:global(.app-shell > .sidebar),
		:global(.app-bar),
		:global(nav),
		:global(header),
		:global(.breadcrumbs),
		:global([class*='AppBar']),
		:global(.drawer),
		:global([class*='drawer']),
		:global(.sidebar),
		:global([class*='sidebar']),
		:global(aside),
		:global([role='complementary']) {
			display: none !important;
			visibility: hidden !important;
		}

		/* Default page setup - portrait */
		@page {
			size: A3 landscape;
			margin: 1cm 1cm;
		}

		/* Reset all layout constraints */
		:global(html),
		:global(body) {
			margin: 0 !important;
			padding: 0 !important;
			width: 100% !important;
			height: auto !important;
			overflow: visible !important;
			background: white !important;
		}

		/* Reset main content area */
		:global(main) {
			margin: 0 !important;
			padding: 0 !important;
			background: white !important;
			min-height: auto !important;
			width: 100% !important;
			max-width: 100% !important;
		}

		/* Remove shadows for cleaner print */
		:global(.shadow-sm),
		:global(.shadow-md),
		:global(.shadow-lg) {
			box-shadow: none !important;
		}

		/* Page breaks before major sections */
		.page-break-section {
			page-break-before: always !important;
			break-before: page !important;
		}

		/* Prevent page breaks inside important elements */
		.card,
		.border {
			page-break-inside: avoid !important;
			break-inside: avoid !important;
		}

		/* Ensure badges and colored elements print well */
		.badge,
		[class*='bg-'],
		[style*='background-color'] {
			-webkit-print-color-adjust: exact !important;
			print-color-adjust: exact !important;
			color-adjust: exact !important;
		}

		/* Better spacing for sections */
		section {
			margin-bottom: 1rem !important;
		}

		/* Ensure proper link rendering */
		a {
			color: inherit !important;
			text-decoration: none !important;
		}

		/* Make sure icons print */
		:global(.fa-solid),
		:global(.fa-regular) {
			-webkit-print-color-adjust: exact !important;
			print-color-adjust: exact !important;
		}

		/* Optimize font sizes */
		body {
			font-size: 10pt !important;
		}

		h1 {
			font-size: 18pt !important;
		}

		h2 {
			font-size: 14pt !important;
		}

		h3 {
			font-size: 12pt !important;
		}

		/* Make tables print nicely */
		table {
			border-collapse: collapse !important;
			width: 100% !important;
			font-size: 8pt !important;
		}

		table,
		th,
		td {
			border: 1px solid #999 !important;
		}

		th {
			background-color: #f3f4f6 !important;
			font-weight: bold !important;
			padding: 4px 6px !important;
		}

		td {
			padding: 3px 6px !important;
		}
	}
</style>
