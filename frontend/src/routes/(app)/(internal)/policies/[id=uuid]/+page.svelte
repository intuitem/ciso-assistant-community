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
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const policy = $derived(data.data);
	const policyDocument = $derived(data.policyDocument);
	const currentRevisionContent = $derived(data.currentRevisionContent);

	const statusColors: Record<string, string> = {
		draft: 'bg-yellow-100 text-yellow-800',
		in_review: 'bg-blue-100 text-blue-800',
		change_requested: 'bg-red-100 text-red-800',
		published: 'bg-green-100 text-green-800',
		deprecated: 'bg-gray-100 text-gray-500'
	};

	const statusLabels: Record<string, string> = {
		draft: 'Draft',
		in_review: 'In review',
		change_requested: 'Change requested',
		published: 'Published',
		deprecated: 'Deprecated'
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
				href="/policies/{policy.id}/document"
				class="btn text-gray-100 bg-linear-to-r from-blue-500 to-indigo-500 h-fit"
				data-testid="edit-document-button"
			>
				<i class="fa-solid fa-file-pen mr-2"></i>
				{m.editDocument()}
			</a>
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
		{#if page.data?.featureflags?.validation_flows && policy.validation_flows}
			{#key policy.validation_flows}
				<ValidationFlowsSection validationFlows={policy.validation_flows} />
			{/key}
		{/if}

		{#if currentRevisionContent}
			<div class="card bg-white shadow rounded-lg border mt-4">
				<div class="p-4 border-b flex items-center justify-between">
					<div class="flex items-center space-x-3">
						<h3 class="font-semibold text-lg">
							<i class="fa-solid fa-file-lines mr-2 text-blue-500"></i>
							{m.policyDocument()}
						</h3>
						<span
							class="px-2 py-0.5 rounded-full text-xs font-medium {statusColors[
								currentRevisionContent.status
							] || 'bg-gray-100 text-gray-600'}"
						>
							{statusLabels[currentRevisionContent.status] || currentRevisionContent.status}
						</span>
						<span class="text-sm text-gray-500">
							v{currentRevisionContent.version_number}
						</span>
					</div>
					<a
						href="/policies/{policy.id}/document"
						class="text-sm text-blue-600 hover:text-blue-800"
					>
						<i class="fa-solid fa-pen-to-square mr-1"></i>
						{m.editDocument()}
					</a>
				</div>
				<div class="p-6 overflow-auto max-h-[600px]">
					<MarkdownRenderer content={currentRevisionContent.content} />
				</div>
				{#if currentRevisionContent.published_at}
					<div class="px-4 py-2 border-t text-xs text-gray-400">
						{m.publishedAt()}:
						{new Date(currentRevisionContent.published_at).toLocaleDateString()}
						{#if currentRevisionContent.author}
							&middot;
							{currentRevisionContent.author.first_name || ''}
							{currentRevisionContent.author.last_name || ''}
						{/if}
					</div>
				{/if}
			</div>
		{:else if policyDocument === null}
			<div class="card bg-white shadow rounded-lg border mt-4 p-6 text-center">
				<i class="fa-solid fa-file-circle-plus text-4xl text-gray-300 mb-3"></i>
				<p class="text-gray-500 mb-3">No document has been created for this policy yet.</p>
				<a
					href="/policies/{policy.id}/document"
					class="btn bg-blue-500 text-white hover:bg-blue-600 inline-flex"
				>
					<i class="fa-solid fa-plus mr-2"></i>
					{m.editDocument()}
				</a>
			</div>
		{/if}
	{/snippet}
</DetailView>
