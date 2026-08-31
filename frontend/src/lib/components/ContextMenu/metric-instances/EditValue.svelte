<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { m } from '$paraglide/messages';
	import { superValidate } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { modelSchema } from '$lib/utils/schemas';
	import { getModelInfo } from '$lib/utils/crud';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import {
		getModalStore,
		type ModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';

	interface Props {
		row: any;
		handler: DataHandler;
	}

	let { row }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	async function openAddSampleModal() {
		const id = row?.meta?.id;
		if (!id) return;
		const initialData = {
			metric_instance: id,
			folder: row.meta.folder?.id ?? row.meta.folder,
			_metric_definition: row.meta.metric_definition,
			_evidences: row.meta.evidences
		};
		const createForm = await superValidate(initialData, zod(modelSchema('custom-metric-samples')), {
			errors: false
		});
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: createForm,
				model: getModelInfo('custom-metric-samples'),
				additionalInitialData: initialData,
				formAction: '/custom-metric-samples?/create'
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.addCustomMetricSample()
		};
		modalStore.trigger(modal);
	}
</script>

<ContextMenu.Item
	class="flex h-10 select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium cursor-pointer data-highlighted:bg-surface-100-900"
	onclick={openAddSampleModal}
>
	<i class="fa-solid fa-plus mr-2"></i>
	<div class="flex items-center">{m.addCustomMetricSample()}</div>
</ContextMenu.Item>
