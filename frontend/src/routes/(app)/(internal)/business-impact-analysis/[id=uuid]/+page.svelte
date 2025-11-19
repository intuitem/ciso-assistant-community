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
				formAction: '/validation-flows?/create',
				additionalInitialData: {
					folder: business_impact_analysis.folder.id,
					business_impact_analysis: [business_impact_analysis.id]
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
			{#if !business_impact_analysis?.is_locked}
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
		</div>
	{/snippet}
</DetailView>
