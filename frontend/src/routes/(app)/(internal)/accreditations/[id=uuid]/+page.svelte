<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const accreditation = data.data;
	const collection = accreditation.collection_data;

	// Collection sections with their labels and URL patterns
	const collectionSections = [
		{
			key: 'compliance_assessments',
			label: m.complianceAssessments(),
			urlPattern: '/compliance-assessments/'
		},
		{ key: 'risk_assessments', label: m.riskAssessments(), urlPattern: '/risk-assessments/' },
		{
			key: 'crq_studies',
			label: m.quantitativeRiskStudies(),
			urlPattern: '/quantitative-risk-studies/'
		},
		{ key: 'ebios_studies', label: m.ebiosRmStudies(), urlPattern: '/ebios-rm/' },
		{ key: 'entity_assessments', label: m.entityAssessments(), urlPattern: '/entity-assessments/' },
		{
			key: 'findings_assessments',
			label: m.findingsAssessments(),
			urlPattern: '/findings-assessments/'
		},
		{ key: 'documents', label: m.evidences(), urlPattern: '/evidences/' },
		{
			key: 'security_exceptions',
			label: m.securityExceptions(),
			urlPattern: '/security-exceptions/'
		},
		{ key: 'policies', label: m.policies(), urlPattern: '/policies/' }
	];

	// Status color mapping
	const statusColorMap = {
		draft: 'bg-gray-300 text-gray-800',
		accredited: 'bg-green-300 text-green-800',
		not_accredited: 'bg-red-300 text-red-800',
		obsolete: 'bg-orange-300 text-orange-800'
	};

	// Category color mapping
	const categoryColorMap = {
		acc_simplified: 'bg-blue-300 text-blue-800',
		acc_elaborated: 'bg-indigo-300 text-indigo-800',
		acc_advanced: 'bg-purple-300 text-purple-800',
		acc_sensitive: 'bg-pink-300 text-pink-800',
		acc_restricted: 'bg-red-300 text-red-800',
		other: 'bg-gray-300 text-gray-800'
	};

	// Get checklist progress from backend
	let checklistProgress = $derived(accreditation.checklist_progress ?? 0);
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<!-- Export action button -->
			<!-- <button class="btn preset-filled-primary-500"> -->
			<!-- 	<i class="fa-solid hidden fa-download mr-2"></i>{m.exportButton()} -->
			<!-- </button> -->
		</div>
	{/snippet}
</DetailView>

<!-- Accreditation details section -->
<div class="card bg-white p-6 m-4 shadow-sm relative">
	<!-- Status and Category badges in top right corner with progress bar below -->
	<div class="absolute top-6 right-6 flex flex-col items-end gap-2">
		<div class="flex gap-2">
			<span
				class="badge text-xs {categoryColorMap[accreditation.category] || categoryColorMap.other}"
			>
				{safeTranslate(accreditation.category)}
			</span>
			<span class="badge text-xs {statusColorMap[accreditation.status] || statusColorMap.draft}">
				{safeTranslate(accreditation.status)}
			</span>
		</div>

		<!-- Checklist Progress Bar -->
		{#if accreditation.checklist}
			<a
				href="/compliance-assessments/{accreditation.checklist.id}"
				class="w-48 block hover:opacity-80 transition-opacity cursor-pointer"
				title="View compliance assessment"
			>
				<div class="flex items-center justify-between mb-1">
					<span class="text-xs font-semibold text-gray-700">{m.checklistProgress()}</span>
					<span class="text-xs text-gray-600">{checklistProgress}%</span>
				</div>
				<Progress value={checklistProgress} max={100} height="h-1.5" meter="bg-primary-500" />
			</a>
		{/if}
	</div>

	<!-- Name and Ref ID as subtitle -->
	<div class="mb-6 pr-48">
		<h2 class="text-2xl font-semibold">{accreditation.name}</h2>
		{#if accreditation.ref_id}
			<p class="text-sm text-gray-600 mt-1">{accreditation.ref_id}</p>
		{/if}
	</div>

	<!-- Description and Observation split horizontally -->
	<div class="grid grid-cols-2 gap-6">
		<!-- Description -->
		<div>
			<h3 class="text-sm font-semibold text-gray-700 mb-2">{m.description()}</h3>
			<div class="prose prose-sm max-w-none text-gray-900">
				{#if accreditation.description}
					<MarkdownRenderer content={accreditation.description} />
				{:else}
					<p class="text-gray-400 italic">No description provided</p>
				{/if}
			</div>
		</div>

		<!-- Observation -->
		<div>
			<h3 class="text-sm font-semibold text-gray-700 mb-2">Observation</h3>
			<div class="prose prose-sm max-w-none text-gray-900">
				{#if accreditation.observation}
					<MarkdownRenderer content={accreditation.observation} />
				{:else}
					<p class="text-gray-400 italic">No observation provided</p>
				{/if}
			</div>
		</div>
	</div>

	<!-- Associated Collection Objects -->
	{#if collection}
		<div class="mt-8 pt-6 border-t border-gray-200">
			<h3 class="text-lg font-semibold text-gray-800 mb-4">{m.associatedObjects()}</h3>

			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each collectionSections as section}
					{@const items = collection[section.key]}
					{#if items && items.length > 0}
						<div class="bg-gray-50 rounded-lg p-4">
							<h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
								{section.label}
								<span class="badge preset-tonal-secondary text-xs">{items.length}</span>
							</h4>
							<ul class="space-y-2">
								{#each items as item}
									<li class="text-sm">
										<Anchor
											href="{section.urlPattern}{item.id}"
											class="text-primary-600 hover:text-primary-800 hover:underline"
										>
											{item.str || item.name || item.id}
										</Anchor>
									</li>
								{/each}
							</ul>
						</div>
					{/if}
				{/each}
			</div>

			{#if !collectionSections.some((s) => collection[s.key]?.length > 0)}
				<p class="text-gray-400 italic text-sm">No associated objects in this collection</p>
			{/if}
		</div>
	{/if}
</div>
