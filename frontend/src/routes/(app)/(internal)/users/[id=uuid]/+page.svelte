<script lang="ts">
	import { page } from '$app/state';
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import CreateSAKeyModal from '$lib/components/CreateSAKeyModal.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
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
	const user = $derived(page.data.user);
	const isServiceAccount = $derived(data.data.is_service_account === true);

	let group = $state(
		isServiceAccount && Object.keys(data.relatedModels ?? {}).length > 0
			? Object.keys(data.relatedModels)[0]
			: undefined
	);

	function openCreateKeyModal() {
		const relatedModel = data.relatedModels?.['service-account-keys'];
		if (!relatedModel) return;
		const modalComponent: ModalComponent = {
			ref: CreateSAKeyModal,
			props: {
				form: relatedModel.createForm,
				formAction: '?/create'
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.serviceAccountKey()
		};
		modalStore.trigger(modal);
	}
</script>

<DetailView {data} displayModelTable={false} />

{#if isServiceAccount && Object.keys(data.relatedModels ?? {}).length > 0}
	<div class="card shadow-lg mt-8 bg-white px-2 py-6">
		<Tabs
			value={group}
			onValueChange={(e) => (group = e.value)}
			orientation="vertical"
			class="w-full"
		>
			<Tabs.List class="shrink-0 gap-3">
				{#each Object.entries(data.relatedModels) as [urlmodel, model]}
					<Tabs.Trigger
						value={urlmodel}
						class="justify-between w-full rounded-md px-3 py-2 transition-colors aria-[selected=true]:!bg-gray-200"
						data-testid="tabs-control"
					>
						{safeTranslate(model.info.localNamePlural)}
						{#if model.count !== undefined && model.count > 0}
							<span
								class="ml-2 rounded-full px-2 py-0.5 text-xs preset-tonal-secondary text-gray-700"
							>
								{model.count}
							</span>
						{/if}
					</Tabs.Trigger>
				{/each}
			</Tabs.List>
			{#each Object.entries(data.relatedModels) as [urlmodel, model]}
				<Tabs.Content value={urlmodel} class="flex-1 min-w-0">
					{#if model.table}
						<ModelTable
							interactive={false}
							source={model.table}
							deleteForm={model.deleteForm}
							URLModel={urlmodel}
							baseEndpoint="/{urlmodel}?service_account={data.data.id}"
							disableView={true}
						>
							{#snippet optButton()}
								{#if user?.is_admin}
									<button
										class="btn preset-filled-primary-500 self-end my-auto"
										data-testid="add-button"
										onclick={openCreateKeyModal}
									>
										<i class="fa-solid fa-plus mr-2"></i>{safeTranslate(
											'add-' + model.info.localName
										)}
									</button>
								{/if}
							{/snippet}
						</ModelTable>
					{/if}
				</Tabs.Content>
			{/each}
		</Tabs>
	</div>
{/if}
