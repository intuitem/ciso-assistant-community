<script lang="ts">
	import { m } from '$paraglide/messages';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/state';
	import type { PageData } from './$types';

	const STORAGE_KEY = 'soa_selection';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// URL param takes priority over saved state
	const caFromUrl = browser ? page.url.searchParams.get('ca') : null;

	function loadSaved(): { compliance: string; risk: string[]; groups: string[] } {
		if (!browser) return { compliance: '', risk: [], groups: [] };
		try {
			const saved = localStorage.getItem(STORAGE_KEY);
			if (saved) return JSON.parse(saved);
		} catch {}
		return { compliance: '', risk: [], groups: [] };
	}

	const saved = loadSaved();
	let selectedComplianceAssessment: string = $state(caFromUrl || saved.compliance);
	let selectedRiskAssessments: string[] = $state(saved.risk);
	let selectedImplementationGroups: string[] = $state(saved.groups ?? []);

	const statusLabels: Record<string, () => string> = {
		planned: m.planned,
		in_progress: m.inProgress,
		in_review: m.inReview,
		done: m.done,
		deprecated: m.deprecated
	};

	function translateStatus(status: string): string {
		return statusLabels[status]?.() ?? status;
	}

	function toggleImplementationGroup(refId: string) {
		if (selectedImplementationGroups.includes(refId)) {
			selectedImplementationGroups = selectedImplementationGroups.filter((g) => g !== refId);
		} else {
			selectedImplementationGroups = [...selectedImplementationGroups, refId];
		}
	}

	function toggleRiskAssessment(id: string) {
		if (selectedRiskAssessments.includes(id)) {
			selectedRiskAssessments = selectedRiskAssessments.filter((r) => r !== id);
		} else {
			selectedRiskAssessments = [...selectedRiskAssessments, id];
		}
	}

	// Derive implementation groups from the selected CA's framework
	const implementationGroups = $derived.by(() => {
		const ca = data.complianceAssessments.find(
			(c: Record<string, any>) => c.id === selectedComplianceAssessment
		);
		if (!ca?.framework?.id) return [];
		return data.frameworkGroupsMap?.[ca.framework.id] || [];
	});

	// Select all groups by default when CA changes (skip on initial load if restoring saved state without URL override)
	let lastAutoSelectedCA: string = $state(caFromUrl ? '' : saved.compliance);

	$effect(() => {
		if (selectedComplianceAssessment !== lastAutoSelectedCA) {
			lastAutoSelectedCA = selectedComplianceAssessment;
			const soaGroup = implementationGroups.find(
				(g: { ref_id: string }) => g.ref_id.toLowerCase() === 'soa'
			);
			if (soaGroup) {
				selectedImplementationGroups = [soaGroup.ref_id];
			} else {
				selectedImplementationGroups = implementationGroups.map(
					(g: { ref_id: string }) => g.ref_id
				);
			}
		}
	});

	function handleGenerate() {
		if (!selectedComplianceAssessment) return;
		if (browser) {
			localStorage.setItem(
				STORAGE_KEY,
				JSON.stringify({
					compliance: selectedComplianceAssessment,
					risk: selectedRiskAssessments,
					groups: selectedImplementationGroups
				})
			);
		}
		const params = new URLSearchParams();
		params.set('compliance_assessment', selectedComplianceAssessment);
		if (selectedRiskAssessments.length > 0) {
			params.set('risk_assessments', selectedRiskAssessments.join(','));
		}
		if (
			selectedImplementationGroups.length > 0 &&
			selectedImplementationGroups.length < implementationGroups.length
		) {
			params.set('implementation_groups', selectedImplementationGroups.join(','));
		}
		goto(`/reports/soa/results?${params.toString()}`);
	}

	const selectedComplianceData = $derived(
		data.complianceAssessments.find(
			(ca: Record<string, any>) => ca.id === selectedComplianceAssessment
		)
	);
</script>

<div class="space-y-6 max-w-4xl mx-auto">
	<!-- Header -->
	<div class="flex items-center gap-3">
		<a href="/reports" class="text-surface-600-400 hover:text-surface-700-300 transition-colors">
			<i class="fas fa-arrow-left text-lg"></i>
		</a>
		<div>
			<h1 class="text-2xl font-bold text-surface-900-100">{m.statementOfApplicability()}</h1>
			<p class="text-sm text-surface-600-400 mt-1">{m.soaDescription()}</p>
		</div>
	</div>

	<!-- Step 1: Select Compliance Assessment -->
	<div class="bg-surface-50-950 card border border-surface-200-800 p-6">
		<div class="flex items-center gap-3 mb-4">
			<div
				class="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-semibold text-sm"
			>
				1
			</div>
			<h2 class="text-lg font-semibold text-surface-900-100">{m.soaSelectCompliance()}</h2>
		</div>

		{#if data.complianceAssessments.length === 0}
			<p class="text-surface-600-400 italic">{m.soaNoComplianceAssessments()}</p>
		{:else}
			<select
				bind:value={selectedComplianceAssessment}
				class="w-full px-3 py-2 border border-surface-300-700 rounded-lg bg-surface-50-950 text-surface-900-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
			>
				<option value="" disabled>{m.soaSelectCompliance()}</option>
				{#each data.complianceAssessments as ca}
					<option value={ca.id}>
						{ca.name}
						{ca.framework?.str ? `(${ca.framework.str})` : ''}
						{ca.perimeter?.str
							? `— ${ca.perimeter.str}`
							: ca.folder?.str
								? `— ${ca.folder.str}`
								: ''}
					</option>
				{/each}
			</select>

			{#if selectedComplianceData}
				<div class="mt-3 flex flex-wrap gap-2">
					{#if selectedComplianceData.framework?.str}
						<span
							class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
						>
							<i class="fas fa-book mr-1.5"></i>
							{selectedComplianceData.framework.str}
						</span>
					{/if}
					{#if selectedComplianceData.perimeter?.str}
						<span
							class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-green-50 text-green-700 border border-green-200"
						>
							<i class="fas fa-crosshairs mr-1.5"></i>
							{selectedComplianceData.perimeter.str}
						</span>
					{:else if selectedComplianceData.folder?.str}
						<span
							class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-green-50 text-green-700 border border-green-200"
						>
							<i class="fas fa-folder mr-1.5"></i>
							{selectedComplianceData.folder.str}
						</span>
					{/if}
					{#if selectedComplianceData.status}
						<span
							class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-surface-50-950 text-surface-700-300 border border-surface-200-800"
						>
							<i class="fas fa-info-circle mr-1.5"></i>
							{translateStatus(selectedComplianceData.status)}
						</span>
					{/if}
				</div>
			{/if}

			<!-- Implementation Group Toggles -->
			{#if implementationGroups.length > 1}
				<div class="mt-4 pt-4 border-t border-surface-100-900">
					<label class="block text-sm font-medium text-surface-700-300 mb-2">
						{m.implementationGroups()}
					</label>
					<div class="flex flex-wrap gap-2">
						{#each implementationGroups as group}
							{@const isSelected = selectedImplementationGroups.includes(group.ref_id)}
							<button
								type="button"
								onclick={() => toggleImplementationGroup(group.ref_id)}
								class="px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors
									{isSelected
									? 'bg-blue-600 text-white border-blue-600'
									: 'bg-surface-50-950 text-surface-500 border-surface-300-700 hover:border-gray-400 line-through'}"
							>
								{group.name}
							</button>
						{/each}
					</div>
				</div>
			{/if}
		{/if}
	</div>

	<!-- Step 2: Select Risk Assessment(s) -->
	<div class="bg-surface-50-950 card border border-surface-200-800 p-6">
		<div class="flex items-center gap-3 mb-4">
			<div
				class="w-8 h-8 rounded-full bg-surface-100-900 text-surface-600-400 flex items-center justify-center font-semibold text-sm"
			>
				2
			</div>
			<div>
				<h2 class="text-lg font-semibold text-surface-900-100">{m.soaSelectRisk()}</h2>
				<p class="text-xs text-surface-600-400 mt-0.5">
					{m.soaSelectRiskDescription()}
				</p>
			</div>
		</div>

		{#if data.riskAssessments.length === 0}
			<p class="text-surface-600-400 italic">{m.soaNoRiskAssessments()}</p>
		{:else}
			<div class="space-y-2 max-h-64 overflow-y-auto">
				{#each data.riskAssessments as ra}
					<label
						class="flex items-center gap-3 p-3 rounded-lg border transition-colors cursor-pointer
							{selectedRiskAssessments.includes(ra.id)
							? 'border-red-300 bg-red-50'
							: 'border-surface-200-800 hover:border-surface-300-700 bg-surface-50-950'}"
					>
						<input
							type="checkbox"
							checked={selectedRiskAssessments.includes(ra.id)}
							onchange={() => toggleRiskAssessment(ra.id)}
							class="rounded border-surface-300-700 text-red-600 focus:ring-red-500"
						/>
						<div class="flex-1 min-w-0">
							<span class="text-sm font-medium text-surface-900-100">{ra.name}</span>
							{#if ra.risk_matrix?.str}
								<span class="text-xs text-surface-600-400 ml-2">({ra.risk_matrix.str})</span>
							{/if}
						</div>
						{#if ra.perimeter?.str}
							<span class="text-xs text-surface-600-400 bg-surface-100-900 px-2 py-0.5 rounded flex-shrink-0">
								{ra.perimeter.str}
							</span>
						{/if}
					</label>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Generate Button -->
	<div class="flex justify-end">
		<button
			onclick={handleGenerate}
			disabled={!selectedComplianceAssessment}
			class="px-6 py-2.5 rounded-lg font-medium text-white transition-all
				{selectedComplianceAssessment
				? 'bg-blue-600 hover:bg-blue-700 shadow-sm hover:shadow'
				: 'bg-surface-300-700 cursor-not-allowed'}"
		>
			<i class="fas fa-table mr-2"></i>
			{m.generate()}
		</button>
	</div>
</div>
