<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData, ActionData } from './$types';
    import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
    import UpdateModal from '$lib/components/Modals/UpdateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { ISO_8601_REGEX } from '$lib/utils/constants';
	import { type ModelMapEntry } from '$lib/utils/crud';
	import { getModelInfo } from '$lib/utils/crud.js';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { isURL } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { toCamelCase } from '$lib/utils/locales.js';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime.js';

	import { Tabs, Tooltip } from '@skeletonlabs/skeleton-svelte';

	import { onMount } from 'svelte';

	import { goto } from '$app/navigation';
	import { listViewFields } from '$lib/utils/table';
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
			// Data
			title: safeTranslate('add-' + model.info.localName)
		};
		modalStore.trigger(modal);
	}

    function modalUpdateForm(): void {
		let modalComponent: ModalComponent = {
			ref: UpdateModal,
			props: {
				form: data.updateForm,
				model: data.model,
				object: data.object,
				context: 'selectElementaryActions',
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.selectAsset()
		};
		modalStore.trigger(modal);
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

<DetailView {data} displayModelTable={false} />
{#if Object.keys(data.relatedModels).length > 0}
    <div class="card shadow-lg mt-8 bg-white w-full">
        <Tabs
            value={group}
            onValueChange={(e) => {
                group = e.value;
            }}
            listJustify="justify-center"
        >
            {#snippet list()}
                {#each Object.entries(data.relatedModels) as [urlmodel, model]}
                    <Tabs.Control value={urlmodel}>
                        {safeTranslate(model.info.localNamePlural)}
                        {#if model.table.body.length > 0}
                            <span class="badge preset-tonal-secondary">{model.table.body.length}</span>
                        {/if}
                    </Tabs.Control>
                {/each}
            {/snippet}
            {#snippet content()}
                {#each Object.entries(data.relatedModels) as [urlmodel, model]}
                    <Tabs.Panel value={urlmodel}>
                        <div class="flex flex-row justify-between px-4 py-2">
                            <h4 class="font-semibold lowercase capitalize-first my-auto">
                                {safeTranslate('associated-' + model.info.localNamePlural)}
                            </h4>
                        </div>
                        {#if model.table}
                            <ModelTable
                                source={model.table}
                                deleteForm={model.deleteForm}
                                URLModel={urlmodel}
                                canSelectObject={canEditObject}
                                baseEndpoint="/elementary-actions?operating_modes={page.params.id}"
                            >
                                {#snippet selectButton()}
                                    <div>
                                        <span
                                            class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs"
                                        >
                                            <button
                                                class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
                                                data-testid="select-button"
                                                title={m.selectElementaryActions()}
                                                onclick={(_) => modalUpdateForm()}
                                                ><i class="fa-solid fa-hand-pointer"></i>
                                            </button>
                                        </span>
                                    </div>
                                {/snippet}
                                {#snippet addButton()}
                                    <div>
                                        <span
                                            class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs"
                                        >
                                            <button
                                                class="inline-block border-e p-3 btn-mini-primary w-12 focus:relative"
                                                data-testid="add-button"
                                                title={safeTranslate('add-' + data.model.localName)}
                                                onclick={(_) => modalCreateForm(model)}
                                                ><i class="fa-solid fa-file-circle-plus"></i>
                                            </button>
                                        </span>
                                    </div>
                                {/snippet}
                            </ModelTable>
                        {/if}
                    </Tabs.Panel>
                {/each}
            {/snippet}
        </Tabs>
    </div>
{/if}
