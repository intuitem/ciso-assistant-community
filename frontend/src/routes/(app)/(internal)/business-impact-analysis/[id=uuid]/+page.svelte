<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { page } from '$app/state';
	import ActivityTracker from '$lib/components/DataViz/ActivityTracker.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import ValidationFlowsSection from '$lib/components/ValidationFlows/ValidationFlowsSection.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const business_impact_analysis = data.data;

	function modalRequestValidation(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.validationFlowForm,
				model: data.validationFlowModel,
				debug: false,
				invalidateAll: false,
				formAction: '/validation-flows?/create'
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

{#if business_impact_analysis.is_locked}
	<div
		class="alert bg-yellow-100 border border-yellow-300 text-yellow-800 px-4 py-3 rounded-lg shadow-sm mx-4 mt-4"
	>
		<div class="flex items-center">
			<i class="fa-solid fa-lock text-yellow-600 mr-2"></i>
			<span class="font-medium">{m.lockedAssessment()}</span>
			<span class="ml-2 text-sm">{m.lockedAssessmentMessage()}</span>
		</div>
	</div>
{/if}

<DetailView
	{data}
	disableCreate={business_impact_analysis.is_locked}
	disableEdit={business_impact_analysis.is_locked}
	disableDelete={business_impact_analysis.is_locked}
>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<Anchor
				href={`${page.url.pathname}/visual`}
				class="btn preset-filled-primary-500 h-fit"
				breadcrumbAction="push"
				><i class="fa-solid fa-stopwatch mr-2"></i>{m.impactOverTime()}</Anchor
			>
			<Anchor
				href={`${page.url.pathname}/report`}
				class="btn preset-filled-primary-500 h-fit"
				breadcrumbAction="push"><i class="fa-solid fa-file-lines mr-2"></i>{m.report()}</Anchor
			>
			{#if !business_impact_analysis?.is_locked && page.data?.featureflags?.validation_flows}
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
		<div class="h-full flex flex-col space-y-4">
			<div class="card p-4 bg-gray-50 shadow-xs grow">
				<div class="font-bold text-xl mb-4">{m.recoveryInsights()}</div>
				<div class="flex items-center justify-center">
					<ActivityTracker metrics={data.metrics} />
				</div>
			</div>
			{#if page.data?.featureflags?.validation_flows}
				<ValidationFlowsSection validationFlows={business_impact_analysis.validation_flows} />
			{/if}
		</div>
	{/snippet}
</DetailView>
