<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData } from './$types';
	import { page } from '$app/state';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import OperatingModeGraph from './graph/OperatingModeGraph.svelte';
	import { invalidateAll } from '$app/navigation';

	import { Tabs } from '@skeletonlabs/skeleton-svelte';

	import { canPerformAction } from '$lib/utils/access-control';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let group = $state(Object.keys(data.relatedModels)[0]);
	let editMode = $state(false);

	function modalCreateForm(model: Record<string, any>): void {
		let modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: model.createForm,
				model: model,
				debug: false
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate('add-' + model.info.localName)
		};
		modalStore.trigger(modal);
	}

	function handleSaved() {
		invalidateAll();
	}

	const user = page.data.user;
	const canEditObject: boolean = canPerformAction({
		user,
		action: 'change',
		model: data.model.name,
		domain:
			data.model.name === 'folder'
				? data.data.id
				: (data.data.folder?.id ?? data.data.folder ?? user.root_folder_id)
	});
</script>

<Anchor
	breadcrumbAction="push"
	href={`/ebios-rm/${data.data.ebios_rm_study.id}`}
	class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
>
	<i class="fa-solid fa-arrow-left"></i>
	<p>{m.goBackToEbiosRmStudy()}</p>
</Anchor>
<DetailView {data} displayModelTable={false} />
{#if Object.keys(data.relatedModels).length > 0}
	<div class="card shadow-lg mt-8 bg-white w-full">
		<Tabs
			value={group}
			onValueChange={(e) => {
				group = e.value;
			}}
		>
			<Tabs.List>
				{#each Object.entries(data.relatedModels).sort( ([a], [b]) => a.localeCompare(b) ) as [urlmodel, model]}
					<Tabs.Trigger value={urlmodel} data-testid="tabs-control">
						{safeTranslate(model.info.localNamePlural)}
						{#if model.table.body.length > 0}
							<span class="badge preset-tonal-secondary">{model.table.body.length}</span>
						{/if}
					</Tabs.Trigger>
				{/each}
				<Tabs.Indicator />
			</Tabs.List>
			{#each Object.entries(data.relatedModels) as [urlmodel, model]}
				<Tabs.Content value={urlmodel}>
					<div class="py-2"></div>
					{#if model.table}
						{@const field = data.model.reverseForeignKeyFields.find(
							(item) => item.urlModel === urlmodel
						)}
						<ModelTable
							source={model.table}
							deleteForm={model.deleteForm}
							URLModel={urlmodel}
							canSelectObject={canEditObject}
							baseEndpoint="/{urlmodel}?{field.field}={page.params.id}"
							disableDelete={field?.disableDelete ?? false}
						>
							{#snippet addButton()}
								<div>
									<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
										<button
											class="inline-block border-e p-3 btn-mini-primary w-12 focus:relative"
											data-testid="add-button"
											title={safeTranslate('add-' + model.info.localName)}
											onclick={(_) => modalCreateForm(model)}
											><i class="fa-solid fa-file-circle-plus"></i>
										</button>
									</span>
								</div>
							{/snippet}
						</ModelTable>
					{/if}
				</Tabs.Content>
			{/each}
		</Tabs>
	</div>
{/if}

<div class="card shadow-lg mt-8 bg-surface-50 w-full p-4">
	<div class="flex justify-between items-center mb-4">
		<h3 class="text-lg font-semibold text-surface-800">
			<i class="fa-solid fa-diagram-project mr-2"></i>{m.moGraph()}
		</h3>
		{#if canEditObject}
			<button
				class="btn text-sm {editMode ? 'preset-tonal-primary' : 'preset-filled-primary-500'}"
				onclick={() => (editMode = !editMode)}
			>
				{#if editMode}
					<i class="fa-solid fa-eye"></i>
					{m.viewMode()}
				{:else}
					<i class="fa-solid fa-pen"></i>
					{m.editMode()}
				{/if}
			</button>
		{/if}
	</div>
	<div class="h-[80vh]">
		<OperatingModeGraph
			elementaryActions={data.elementaryActions}
			killChainSteps={data.killChainSteps}
			operatingModeId={data.operatingModeId}
			graphColumns={data.data.graph_columns ?? {}}
			readonly={!editMode}
			onSaved={handleSaved}
		/>
	</div>
</div>
