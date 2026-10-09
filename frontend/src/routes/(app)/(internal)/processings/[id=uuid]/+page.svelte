<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import ValidationFlowsSection from '$lib/components/ValidationFlows/ValidationFlowsSection.svelte';
	import { invalidateAll } from '$app/navigation';
	import { enhance } from '$app/forms';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const processing = $derived(data.data);
	const screening = $derived(processing.dpia_screening);
	const screeningOutcomes = $derived(
		Object.entries(screening?.computed_outcome ?? {}) as [
			string,
			{ label?: string; color?: string }
		][]
	);
	const outcomeClass: Record<string, string> = {
		red: 'preset-tonal-error',
		orange: 'preset-tonal-warning',
		green: 'preset-tonal-success',
		purple: 'preset-tonal-secondary'
	};

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
			<a
				href="/processings/{processing.id}/export/xlsx"
				class="btn preset-filled-primary-500 h-fit"
				data-testid="export-processing-button"
			>
				<i class="fa-solid fa-download mr-2"></i>
				{m.exportButton()} XLSX
			</a>
			{#if page.data?.featureflags?.dpias !== false}
				<form method="POST" action="?/startScreening" use:enhance>
					<button
						type="submit"
						class="btn preset-filled-secondary-500 h-fit w-full"
						data-testid="dpia-screening-button"
					>
						<i class="fa-solid fa-clipboard-question mr-2"></i>
						{screening?.status === 'draft' ? m.dpiaScreeningResume() : m.dpiaScreeningStart()}
					</button>
				</form>
			{/if}
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
		{#if screening}
			<div class="card p-4 bg-surface-50-950 shadow-sm flex flex-col gap-2 mb-4">
				<div class="flex items-baseline justify-between gap-2">
					<h3 class="font-semibold">{m.dpiaScreening()}</h3>
					<a class="anchor text-sm" href="/quick-form-responses/{screening.id}"
						>{screening.ref_id}</a
					>
				</div>
				<p class="text-sm text-surface-600-400">
					{safeTranslate(screening.status)}
					{#if screening.submitted_at}
						· {new Date(screening.submitted_at).toLocaleDateString()}
					{/if}
				</p>
				{#if screeningOutcomes.length}
					<div class="flex flex-wrap gap-2">
						{#each screeningOutcomes as [ref, outcome]}
							<span class="badge {outcomeClass[outcome.color ?? ''] ?? 'preset-tonal'}"
								>{outcome.label ?? ref}</span
							>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
		{#if page.data?.featureflags?.validation_flows && processing.validation_flows}
			{#key processing.validation_flows}
				<ValidationFlowsSection validationFlows={processing.validation_flows} />
			{/key}
		{/if}
	{/snippet}
</DetailView>
