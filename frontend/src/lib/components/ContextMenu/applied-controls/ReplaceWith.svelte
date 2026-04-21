<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { m } from '$paraglide/messages';
	import {
		getModalStore,
		type ModalStore,
		type ModalSettings
	} from '$lib/components/Modals/stores';
	import MergeAppliedControlsModal from '$lib/components/Modals/MergeAppliedControlsModal.svelte';

	interface Props {
		row: any;
		handler: DataHandler;
	}

	let { row, handler }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	function openReplaceModal() {
		const id = row?.meta?.id;
		if (!id) return;
		const modal: ModalSettings = {
			type: 'component',
			component: {
				ref: MergeAppliedControlsModal,
				props: {
					sourceIds: [id],
					URLModel: 'applied-controls',
					handler,
					onClearSelection: () => {}
				}
			},
			title: m.replaceWith()
		};
		modalStore.trigger(modal);
	}
</script>

<ContextMenu.Item
	class="flex h-10 select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! hover:bg-surface-50"
	onclick={openReplaceModal}
>
	<i class="fa-solid fa-code-merge mr-2"></i>
	<div class="flex items-center">{m.replaceWith()}</div>
</ContextMenu.Item>

<ContextMenu.Separator class="-mx-1 my-1 block h-px bg-surface-100" />
