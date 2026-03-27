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
	const additionalControls = $derived(data.soaData.additional_controls || []);
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
					<col class="w-[25%]" /><!-- Observation -->
					<col class="w-[38%]" /><!-- Implementation -->
				</colgroup>
				<thead class="sticky top-0 z-10 print:static">
					<tr class="bg-gray-800 text-white border-b-2 border-gray-900">
						<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
							Ref
						</th>
						<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
							{m.referenceControl()}
						</th>
						<th class="px-3 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider">
							{m.applicable()}
						</th>
						<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
							{m.justification()}
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

	<!-- Additional Controls from Risk Treatment -->
	{#if additionalControls.length > 0}
		<div
			class="bg-white card border border-gray-200 overflow-hidden print:break-before-page print:border-none print:shadow-none"
		>
			<div class="px-4 py-3 bg-red-50 border-b border-red-200">
				<div class="flex items-center gap-2">
					<i class="fas fa-shield-halved text-red-600"></i>
					<h2 class="text-lg font-semibold text-gray-900">{m.additionalControls()}</h2>
				</div>
				<p class="text-xs text-gray-600 mt-1 ml-7">{m.riskTreatmentControlsDescription()}</p>
			</div>
			<div class="overflow-x-auto">
				<table class="w-full table-fixed border-collapse">
					<colgroup>
						<col class="w-[8%]" /><!-- Ref -->
						<col class="w-[22%]" /><!-- Reference Control -->
						<col class="w-[25%]" /><!-- Justification -->
						<col class="w-[10%]" /><!-- Risk Coverage -->
						<col class="w-[35%]" /><!-- Implementation -->
					</colgroup>
					<thead class="sticky top-0 z-10 print:static">
						<tr class="bg-gray-800 text-white border-b-2 border-gray-900">
							<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
								Ref
							</th>
							<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
								{m.referenceControl()}
							</th>
							<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
								{m.justification()}
							</th>
							<th
								class="px-3 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider"
							>
								{m.riskCoverage()}
							</th>
							<th class="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider">
								{m.implementation()}
							</th>
						</tr>
					</thead>
					<tbody>
						{#each additionalControls as ac, i}
							{@const statusBadge = getStatusBadge(ac.status)}
							<tr
								class="border-b border-gray-200 transition-colors {i % 2 === 0
									? 'bg-white'
									: 'bg-slate-50'}"
							>
								<!-- Ref -->
								<td class="px-3 py-2 text-xs font-mono text-gray-600 align-top">
									{ac.reference_control?.ref_id || ''}
								</td>
								<!-- Reference Control -->
								<td class="px-3 py-2 text-sm text-gray-900 align-top overflow-hidden">
									{#if ac.reference_control}
										<div class="font-medium">{ac.reference_control.name}</div>
										{#if ac.reference_control.description}
											<div class="text-xs text-gray-500 mt-0.5">
												{ac.reference_control.description}
											</div>
										{/if}
									{/if}
								</td>
								<!-- Justification -->
								<td class="px-3 py-2 text-sm text-gray-600 align-top overflow-hidden">
									<span class="break-words">{ac.observation || ''}</span>
								</td>
								<!-- Risk Coverage -->
								<td class="px-3 py-2 text-center align-top">
									{#if ac.risk_scenarios?.length > 0}
										<span class="text-sm font-semibold text-gray-700">
											{ac.risk_scenarios.length}
										</span>
									{:else}
										<span class="text-xs text-gray-400">--</span>
									{/if}
								</td>
								<!-- Implementation -->
								<td class="px-3 py-2 align-top">
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
