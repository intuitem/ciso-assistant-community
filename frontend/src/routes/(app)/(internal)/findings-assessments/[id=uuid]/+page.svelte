<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { Popover } from '@skeletonlabs/skeleton-svelte';
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
	let exportPopupOpen = $state(false);
	let chartKey = $state(0);

	const modalStore: ModalStore = getModalStore();
	const findings_assessment = $derived(data.data);

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

	function resizeObserver(node: HTMLElement) {
		const observer = new ResizeObserver(() => {
			chartKey = chartKey + 1;
		});
		observer.observe(node);
		return {
			destroy() {
				observer.disconnect();
			}
		};
	}
</script>

{#if data.data?.is_locked}
	<div
		class="alert bg-yellow-100 border border-yellow-300 text-yellow-800 px-4 py-3 rounded-lg shadow-sm mx-4 mt-4 mb-4"
	>
		<div class="flex items-center">
			<i class="fa-solid fa-lock text-yellow-600 mr-2"></i>
			<span class="font-medium">{m.lockedAssessment()}</span>
			<span class="ml-2 text-sm">{m.lockedAssessmentMessage()}</span>
		</div>
	</div>
{/if}
<DetailView {data} disableCreate={data.data?.is_locked} disableDelete={data.data?.is_locked}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<Popover
				open={exportPopupOpen}
				onOpenChange={(e) => (exportPopupOpen = e.open)}
				positioning={{ placement: 'bottom' }}
				triggerBase="btn preset-filled-primary-500 w-full"
				contentBase="card whitespace-nowrap bg-surface-50-950 py-2 w-fit shadow-lg space-y-1"
				zIndex="1000"
			>
				{#snippet trigger()}
					<span data-testid="export-button">
						<i class="fa-solid fa-download mr-2"></i>{m.exportButton()}
					</span>
				{/snippet}
				{#snippet content()}
					<div>
						<p class="block px-4 py-2 text-sm text-surface-950-50">{m.findingsAssessment()}</p>
						<a
							href="/findings-assessments/{data.data.id}/export/xlsx"
							class="block px-4 py-2 text-sm text-surface-950-50 hover:bg-surface-200-800">... {m.asXLSX()}</a
						>
						<a
							href="/findings-assessments/{data.data.id}/export/md"
							class="block px-4 py-2 text-sm text-surface-950-50 hover:bg-surface-200-800"
							>... {m.asMarkdown()}</a
						>
						<a
							href="/findings-assessments/{data.data.id}/export/pdf"
							class="block px-4 py-2 text-sm text-surface-950-50 hover:bg-surface-200-800">... {m.asPDF()}</a
						>
					</div>
				{/snippet}
			</Popover>
			<Anchor
				href={`${page.url.pathname}/action-plan`}
				class="btn preset-filled-primary-500 h-fit"
				breadcrumbAction="push"><i class="fa-solid fa-heart-pulse mr-2"></i>{m.actionPlan()}</Anchor
			>
			{#if !findings_assessment?.is_locked && page.data?.featureflags?.validation_flows}
				<button
					class="btn text-surface-100-900 bg-linear-to-r from-orange-500 to-amber-500 h-fit"
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
		{#key form}
			<div class="h-full flex flex-col space-y-4">
				<div class="card p-4 bg-surface-50-950 shadow-xs">
					<h3 class="text-lg font-semibold mb-2">{m.summary()}</h3>
					<div class="grid grid-cols-2 gap-2">
						<div class="rounded-lg bg-primary-100 p-3 text-center">
							<p class="text-xs font-medium text-primary-800">Total</p>
							<p class="text-xl font-bold text-primary-900" data-testid="summary-total">
								{data.findings_metrics.raw_metrics.total_count || 'N/A'}
							</p>
						</div>
						<div class="rounded-lg bg-primary-100 p-3 text-center">
							<p class="text-xs font-medium text-primary-800">{m.followUpUnresolvedHigh()}</p>
							<!--                                                                          hoc = high or critical -->
							<p class="text-xl font-bold text-primary-900" data-testid="summary-unresolved-hoc">
								{data.findings_metrics.raw_metrics.unresolved_important_count || 'N/A'}
							</p>
						</div>
					</div>
				</div>

				<div class="card p-2 bg-surface-50-950 shadow-xs flex-1 flex flex-row gap-2" use:resizeObserver>
					{#key chartKey}
						<div class="flex-1 min-h-0 min-w-0">
							<HalfDonutChart
								name="current_h"
								title={m.severity()}
								classesContainer="card p-2 bg-surface-50-950 h-full"
								values={data.findings_metrics.severity_chart_data}
								colors={data.findings_metrics.severity_chart_data.map((object) => object.color)}
							/>
						</div>
						<div class="flex-1 min-h-0 min-w-0">
							<DonutChart
								classesContainer="card p-2 bg-surface-50-950 h-full"
								name="f_treatment_progress"
								title={m.progress()}
								values={data.findings_metrics.status_chart_data.values}
							/>
						</div>
					{/key}
				</div>
				{#if page.data?.featureflags?.validation_flows}
					{#key findings_assessment.validation_flows}
						<ValidationFlowsSection validationFlows={findings_assessment.validation_flows} />
					{/key}
				{/if}
			</div>
		{/key}
	{/snippet}
</DetailView>
