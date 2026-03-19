<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import type { PageData, ActionData } from './$types';
	import { page } from '$app/state';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import ValidationFlowsSection from '$lib/components/ValidationFlows/ValidationFlowsSection.svelte';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const accreditation = $derived(data.data);
	const collection = accreditation.collection_data;

	// Collection sections with their labels, URL patterns, and icons
	const collectionSections = [
		{
			key: 'compliance_assessments',
			label: m.complianceAssessments(),
			urlPattern: '/compliance-assessments/',
			icon: 'fa-solid fa-list-check'
		},
		{
			key: 'risk_assessments',
			label: m.riskAssessments(),
			urlPattern: '/risk-assessments/',
			icon: 'fa-solid fa-biohazard'
		},
		{
			key: 'crq_studies',
			label: m.quantitativeRiskStudies(),
			urlPattern: '/quantitative-risk-studies/',
			icon: 'fa-solid fa-chart-line'
		},
		{
			key: 'ebios_studies',
			label: m.ebiosRmStudies(),
			urlPattern: '/ebios-rm/',
			icon: 'fa-solid fa-chart-diagram'
		},
		{
			key: 'entity_assessments',
			label: m.entityAssessments(),
			urlPattern: '/entity-assessments/',
			icon: 'fa-solid fa-building'
		},
		{
			key: 'findings_assessments',
			label: m.findingsAssessments(),
			urlPattern: '/findings-assessments/',
			icon: 'fa-solid fa-magnifying-glass'
		},
		{
			key: 'documents',
			label: m.evidences(),
			urlPattern: '/evidences/',
			icon: 'fa-solid fa-file-lines'
		},
		{
			key: 'security_exceptions',
			label: m.securityExceptions(),
			urlPattern: '/security-exceptions/',
			icon: 'fa-solid fa-shield-halved'
		},
		{
			key: 'policies',
			label: m.policies(),
			urlPattern: '/policies/',
			icon: 'fa-solid fa-book'
		}
	];

	// Status color mapping for associated objects (these use raw CharField values, not Terminology)
	const objectStatusColorMap: Record<string, string> = {
		planned: 'bg-gray-100 text-gray-600',
		in_progress: 'bg-blue-100 text-blue-700',
		in_review: 'bg-amber-100 text-amber-700',
		done: 'bg-green-100 text-green-700',
		deprecated: 'bg-red-100 text-red-600',
		draft: 'bg-gray-100 text-gray-600',
		missing: 'bg-red-100 text-red-600',
		approved: 'bg-green-100 text-green-700',
		rejected: 'bg-red-100 text-red-600',
		expired: 'bg-orange-100 text-orange-600',
		active: 'bg-green-100 text-green-700'
	};

	function getObjectStatusColor(status: string | Record<string, string>): string {
		const key = typeof status === 'string' ? status : status?.str || '';
		return objectStatusColorMap[key] || 'bg-gray-100 text-gray-600';
	}

	// Get checklist progress from backend
	let checklistProgress = $derived(accreditation.checklist_progress ?? 0);

	function modalRequestValidation(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.validationFlowForm,
				model: data.validationFlowModel,
				debug: false,
				invalidateAll: true,
				formAction: '/validation-flows?/create',
				onConfirm: async () => {
					await invalidateAll();
				}
			}
		};

		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.requestValidation()
		};
		modalStore.trigger(modal);
	}
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			{#if page.data?.featureflags?.validation_flows}
				<button
					class="btn text-gray-100 bg-linear-to-r from-orange-500 to-amber-500 h-fit"
					onclick={() => modalRequestValidation()}
					data-testid="request-validation-button"
				>
					<i class="fa-solid fa-check-circle mr-2"></i>
					{m.requestValidation()}
				</button>
			{/if}
		</div>
	{/snippet}

	{#snippet widgets()}
		<!-- Authority -->
		{#if accreditation.authority || accreditation.authority_name}
			<div class="rounded-lg bg-gray-50 p-4 mb-3">
				<h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
					<i class="fa-solid fa-building-columns mr-1"></i>
					{m.authority()}
				</h4>
				{#if accreditation.authority}
					<Anchor
						href="/entities/{accreditation.authority.id}"
						class="text-primary-600 hover:text-primary-800 hover:underline font-medium"
					>
						{accreditation.authority.str || accreditation.authority.name}
					</Anchor>
					{#if accreditation.authority_name}
						<p class="text-xs text-gray-500 mt-1">{accreditation.authority_name}</p>
					{/if}
				{:else}
					<p class="text-gray-900 font-medium">{accreditation.authority_name}</p>
				{/if}
			</div>
		{/if}

		<!-- Status & Category -->
		<div class="rounded-lg bg-gray-50 p-4 mb-3 space-y-3">
			<div class="flex items-center justify-between">
				<span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">{m.status()}</span
				>
				<span class="badge text-xs font-medium px-2.5 py-0.5 rounded-full preset-tonal-primary">
					{safeTranslate(accreditation.status)}
				</span>
			</div>
			<div class="flex items-center justify-between">
				<span class="text-xs font-semibold text-gray-500 uppercase tracking-wide"
					>{m.category()}</span
				>
				<span class="badge text-xs font-medium px-2.5 py-0.5 rounded-full preset-tonal-secondary">
					{safeTranslate(accreditation.category)}
				</span>
			</div>
		</div>

		<!-- Checklist Progress -->
		{#if accreditation.checklist}
			<a
				href="/compliance-assessments/{accreditation.checklist.id}"
				class="block rounded-lg bg-gray-50 p-4 mb-3 hover:bg-gray-100 transition-colors duration-200"
			>
				<div class="flex items-center justify-between mb-2">
					<span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">
						<i class="fa-solid fa-list-check mr-1"></i>
						{m.checklistProgress()}
					</span>
					<span class="text-sm font-bold text-gray-800">{checklistProgress}%</span>
				</div>
				<Progress value={checklistProgress} max={100}>
					<Progress.Track class="h-2 rounded-full">
						<Progress.Range class="bg-primary-500 rounded-full" />
					</Progress.Track>
				</Progress>
			</a>
		{/if}

		<!-- Decision Evidence -->
		{#if accreditation.decision_evidence && accreditation.decision_evidence.length > 0}
			<div class="rounded-lg bg-gray-50 p-4 mb-3">
				<h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
					<i class="fa-solid fa-file-circle-check mr-1"></i>
					{m.decisionEvidence()}
				</h4>
				<ul class="space-y-1.5">
					{#each accreditation.decision_evidence as evidence}
						<li class="text-sm">
							<Anchor
								href="/evidences/{evidence.id}"
								class="text-primary-600 hover:text-primary-800 hover:underline"
							>
								{evidence.str || evidence.name || evidence.id}
							</Anchor>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Validation Flows -->
		{#if page.data?.featureflags?.validation_flows && accreditation.validation_flows}
			{#key accreditation.validation_flows}
				<ValidationFlowsSection validationFlows={accreditation.validation_flows} />
			{/key}
		{/if}
	{/snippet}
</DetailView>

<!-- Accreditation details section -->
<div class="card bg-white p-6 m-4 shadow-sm">
	<!-- Name and Ref ID -->
	<div class="mb-6">
		<h2 class="text-2xl font-semibold">{accreditation.name}</h2>
		{#if accreditation.ref_id}
			<p class="text-sm text-gray-500 mt-1">{accreditation.ref_id}</p>
		{/if}
	</div>

	<!-- Description and Observation -->
	<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
		<div class="border-l-2 border-gray-200 pl-4">
			<h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
				{m.description()}
			</h3>
			<div class="prose prose-sm max-w-none text-gray-900">
				{#if accreditation.description}
					<MarkdownRenderer content={accreditation.description} />
				{:else}
					<p class="text-gray-400 italic">{m.noDescription()}</p>
				{/if}
			</div>
		</div>

		<div class="border-l-2 border-gray-200 pl-4">
			<h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
				{m.observation()}
			</h3>
			<div class="prose prose-sm max-w-none text-gray-900">
				{#if accreditation.observation}
					<MarkdownRenderer content={accreditation.observation} />
				{:else}
					<p class="text-gray-400 italic">{m.noObservation()}</p>
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
								<i class="{section.icon} text-gray-400 text-xs"></i>
								{section.label}
								<span class="badge preset-tonal-secondary text-xs ml-auto">{items.length}</span>
							</h4>
							<ul class="space-y-2">
								{#each items as item}
									<li class="text-sm flex items-center justify-between gap-2">
										<Anchor
											href="{section.urlPattern}{item.id}"
											class="text-primary-600 hover:text-primary-800 hover:underline truncate"
										>
											{item.str || item.name || item.id}
										</Anchor>
										{#if item.status}
											<span
												class="badge text-xs px-2 py-0.5 rounded-full shrink-0 {getObjectStatusColor(
													item.status
												)}"
											>
												{safeTranslate(item.status)}
											</span>
										{/if}
									</li>
								{/each}
							</ul>
						</div>
					{/if}
				{/each}
			</div>

			{#if !collectionSections.some((s) => collection[s.key]?.length > 0)}
				<p class="text-gray-400 italic text-sm">{m.noAssociatedObjects()}</p>
			{/if}
		</div>
	{/if}
</div>
