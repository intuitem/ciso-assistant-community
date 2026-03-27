<script lang="ts">
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import SoaTreeSection from './SoaTreeSection.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const tree = $derived(data.soaData.tree || {});
	const metadata = $derived(data.soaData.metadata || {});
	const treeEntries = $derived(Object.entries(tree));
	const riskScenarios = $derived(data.soaData.risk_scenarios || []);
	const returnUrl = $derived(page.url.pathname + page.url.search);

	function getStatusBadge(status: string): { label: string; classes: string } {
		switch (status) {
			case 'active':
				return { label: m.active(), classes: 'bg-green-100 text-green-700' };
			case 'in_progress':
				return { label: m.inProgress(), classes: 'bg-blue-100 text-blue-700' };
			case 'on_hold':
				return { label: m.onHold(), classes: 'bg-yellow-100 text-yellow-700' };
			case 'deprecated':
				return { label: m.deprecated(), classes: 'bg-red-100 text-red-700' };
			case 'to_do':
				return { label: m.toDo(), classes: 'bg-gray-100 text-gray-600' };
			default:
				return { label: status || '--', classes: 'bg-gray-100 text-gray-600' };
		}
	}

	function exportPDF() {
		window.print();
	}

	function getTreatmentBadge(treatment: string): { label: string; classes: string } {
		switch (treatment) {
			case 'mitigate':
				return { label: m.mitigate(), classes: 'bg-blue-50 text-blue-700' };
			case 'accept':
				return { label: m.accept(), classes: 'bg-green-50 text-green-700' };
			case 'avoid':
				return { label: m.avoid(), classes: 'bg-red-50 text-red-700' };
			case 'transfer':
				return { label: m.transfer(), classes: 'bg-purple-50 text-purple-700' };
			default:
				return { label: treatment || m.open(), classes: 'bg-gray-50 text-gray-600' };
		}
	}
</script>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex items-start justify-between print:mb-2">
		<div class="flex items-center gap-3">
			<a
				href="/reports/soa"
				class="text-gray-500 hover:text-gray-700 transition-colors no-print"
				title={m.backToSelection()}
			>
				<i class="fas fa-arrow-left text-lg"></i>
			</a>
			<div>
				<h1 class="text-2xl font-bold text-gray-900">{m.statementOfApplicability()}</h1>
				<div class="flex flex-wrap gap-2 mt-1.5">
					{#if metadata.compliance_assessment?.name}
						<span
							class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
						>
							<i class="fas fa-clipboard-check mr-1.5"></i>
							{metadata.compliance_assessment.name}
						</span>
					{/if}
					{#if metadata.framework?.name}
						<span
							class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200"
						>
							<i class="fas fa-book mr-1.5"></i>
							{metadata.framework.ref_id || metadata.framework.name}
						</span>
					{/if}
					{#if metadata.selected_implementation_groups?.length > 0}
						{#each metadata.selected_implementation_groups as group}
							<span
								class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200"
							>
								<i class="fas fa-layer-group mr-1.5"></i>
								{group}
							</span>
						{/each}
					{/if}
					{#if metadata.risk_assessments?.length > 0}
						{#each metadata.risk_assessments as raName}
							<span
								class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-red-50 text-red-700 border border-red-200"
							>
								<i class="fas fa-exclamation-triangle mr-1.5"></i>
								{raName}
							</span>
						{/each}
					{/if}
				</div>
			</div>
		</div>
		<button
			onclick={exportPDF}
			class="no-print flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors shadow-sm"
		>
			<i class="fas fa-file-pdf"></i>
			PDF
		</button>
	</div>

	<!-- SoA Table -->
	<div
		class="bg-white card border border-gray-200 overflow-hidden print:border-none print:shadow-none"
	>
		<div class="overflow-x-auto">
			<table class="w-full table-fixed border-collapse">
				<colgroup>
					<col class="w-[8%]" /><!-- Ref -->
					<col class="w-[22%]" /><!-- Requirement -->
					<col class="w-[7%]" /><!-- Applicable -->
					<col class="w-[11%]" /><!-- Result -->
					<col class="w-[22%]" /><!-- Observation -->
					<col class="w-[30%]" /><!-- Implementation -->
				</colgroup>
				<thead class="sticky top-0 z-10 print:static">
					<tr class="bg-gray-800 text-white border-b-2 border-gray-900">
						<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
							Ref
						</th>
						<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
							{m.requirement()}
						</th>
						<th class="px-3 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider">
							{m.applicable()}
						</th>
						<th class="px-3 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider">
							{m.result()}
						</th>
						<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
							{m.observation()}
						</th>
						<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
							{m.implementation()}
						</th>
					</tr>
				</thead>
				<tbody>
					{#each treeEntries as [nodeId, node], i}
						<SoaTreeSection {nodeId} {node} depth={0} index={i} />
					{/each}
				</tbody>
			</table>
		</div>
	</div>

	<!-- Risk Scenarios Section -->
	{#if riskScenarios.length > 0}
		<div
			class="bg-white card border border-gray-200 overflow-hidden print:break-before-page print:border-none print:shadow-none"
		>
			<div class="px-4 py-3 bg-red-50 border-b border-red-200">
				<div class="flex items-center gap-2">
					<i class="fas fa-shield-halved text-red-600"></i>
					<h2 class="text-lg font-semibold text-gray-900">{m.riskTreatmentControls()}</h2>
				</div>
				<p class="text-xs text-gray-600 mt-1 ml-7">{m.riskTreatmentControlsDescription()}</p>
			</div>
			<div class="overflow-x-auto">
				<table class="w-full table-fixed border-collapse">
					<colgroup>
						<col class="w-[8%]" /><!-- Ref -->
						<col class="w-[20%]" /><!-- Risk Scenario -->
						<col class="w-[10%]" /><!-- Treatment -->
						<col class="w-[10%]" /><!-- Current Level -->
						<col class="w-[36%]" /><!-- Implementation -->
						<col class="w-[10%]" /><!-- Residual Risk -->
					</colgroup>
					<thead class="sticky top-0 z-10 print:static">
						<tr class="bg-gray-800 text-white border-b-2 border-gray-900">
							<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
								Ref
							</th>
							<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
								{m.riskScenarios()}
							</th>
							<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
								{m.treatment()}
							</th>
							<th
								class="px-3 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider"
							>
								{m.currentLevel()}
							</th>
							<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
								{m.implementation()}
							</th>
							<th
								class="px-3 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider"
							>
								{m.residualLevel()}
							</th>
						</tr>
					</thead>
					<tbody>
						{#each riskScenarios as rs, i}
							{@const treatmentBadge = getTreatmentBadge(rs.treatment)}
							<tr
								class="border-b border-gray-200 transition-colors {i % 2 === 0
									? 'bg-white'
									: 'bg-slate-50'}"
							>
								<!-- Ref -->
								<td class="px-3 py-2.5 text-xs font-mono text-gray-600 align-top">
									{rs.ref_id || ''}
								</td>
								<!-- Risk Scenario -->
								<td class="px-3 py-2.5 align-top">
									<Anchor
										breadcrumbAction="push"
										href="/risk-scenarios/{rs.id}?next={encodeURIComponent(returnUrl)}"
										class="text-sm font-medium text-gray-900 break-words hover:underline"
									>
										{rs.name}
									</Anchor>
									{#if rs.threats?.length > 0}
										<div class="text-xs text-gray-500 mt-0.5">
											{rs.threats.map((t: Record<string, string>) => t.name).join(', ')}
										</div>
									{/if}
								</td>
								<!-- Treatment -->
								<td class="px-3 py-2.5 align-top">
									<span
										class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium {treatmentBadge.classes}"
									>
										{treatmentBadge.label}
									</span>
								</td>
								<!-- Current Level -->
								<td class="px-3 py-2.5 text-center align-top">
									{#if rs.current_risk?.name && rs.current_risk.name !== '--'}
										<span
											class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold text-white print:border print:border-gray-400"
											style="background-color: {rs.current_risk.hexcolor || '#6b7280'}"
										>
											{rs.current_risk.name}
										</span>
									{:else}
										<span class="text-xs text-gray-400">--</span>
									{/if}
								</td>
								<!-- Implementation -->
								<td class="px-3 py-2.5 align-top">
									{#if rs.applied_controls?.length > 0}
										<div class="flex flex-col gap-2.5">
											{#each rs.applied_controls as ac}
												{@const statusBadge = getStatusBadge(ac.status)}
												<Anchor
													breadcrumbAction="push"
													href="/applied-controls/{ac.id}?next={encodeURIComponent(returnUrl)}"
													class="flex items-start gap-1.5 hover:underline"
												>
													<span
														class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium whitespace-nowrap flex-shrink-0 {statusBadge.classes}"
													>
														{statusBadge.label}
													</span>
													<span class="text-xs text-gray-700 break-words">
														{ac.ref_id ? `${ac.ref_id} ` : ''}{ac.name}
													</span>
												</Anchor>
											{/each}
										</div>
									{:else}
										<span class="text-xs text-gray-400">--</span>
									{/if}
								</td>
								<!-- Residual Risk -->
								<td class="px-3 py-2.5 text-center align-top">
									{#if rs.residual_risk?.name && rs.residual_risk.name !== '--'}
										<span
											class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold text-white print:border print:border-gray-400"
											style="background-color: {rs.residual_risk.hexcolor || '#6b7280'}"
										>
											{rs.residual_risk.name}
										</span>
									{:else}
										<span class="text-xs text-gray-400">--</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>

<style>
	@media print {
		:global(.no-print),
		:global(nav),
		:global(aside),
		:global(header),
		:global(footer),
		:global(.sidebar),
		:global(#shell-header),
		:global(#page-header),
		:global(.app-bar),
		:global(.app-rail) {
			display: none !important;
		}

		:global(body) {
			print-color-adjust: exact;
			-webkit-print-color-adjust: exact;
		}

		@page {
			size: A3 landscape;
			margin: 1.5cm 1cm;
		}

		:global(main) {
			padding: 0 !important;
			margin: 0 !important;
			max-width: none !important;
		}

		table {
			font-size: 9pt;
		}

		th {
			font-size: 8pt;
		}
	}
</style>
