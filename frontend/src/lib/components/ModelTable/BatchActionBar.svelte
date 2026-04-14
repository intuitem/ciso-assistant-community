<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { getToastStore } from '$lib/components/Toast/stores';
	import {
		getModalStore,
		type ModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';
	import BatchActionModal from '$lib/components/Modals/BatchActionModal.svelte';
	import type { BatchActionConfig } from '$lib/utils/table';
	import type { urlModel } from '$lib/utils/types';
	import type { DataHandler } from '@vincjo/datatables/remote';

	interface Props {
		selectedIds: Set<string>;
		actions: BatchActionConfig[];
		URLModel: urlModel;
		handler: DataHandler;
		onClearSelection: () => void;
	}

	let { selectedIds, actions, URLModel, handler, onClearSelection }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();

	let openGroupIndex: number | null = $state(null);

	function toggleGroup(index: number) {
		openGroupIndex = openGroupIndex === index ? null : index;
	}

	function closeGroup() {
		openGroupIndex = null;
	}

	function triggerAction(action: BatchActionConfig) {
		closeGroup();
		const count = selectedIds.size;
		const ids = [...selectedIds];

		const modalComponent: ModalComponent = {
			ref: BatchActionModal,
			props: {
				actionType: action.type,
				count,
				optionsEndpoint: action.optionsEndpoint,
				multiSelect: action.multiSelect ?? false,
				onConfirm: async (value?: string | string[]) => {
					try {
						const res = await fetch(`/${URLModel}/batch-action`, {
							method: 'POST',
							headers: { 'Content-Type': 'application/json' },
							body: JSON.stringify({
								action: action.type,
								ids,
								field: action.field ?? null,
								value: value ?? null
							})
						});

						if (!res.ok) {
							toastStore.trigger({
								message: m.batchActionAllFailed({ count }),
								background: 'preset-filled-error-500'
							});
							return;
						}

						const result = await res.json();
						const succeededCount = result.succeeded?.length ?? 0;
						const failedCount = result.failed?.length ?? 0;

						if (failedCount === 0) {
							toastStore.trigger({
								message: m.batchActionSuccess({ count: succeededCount }),
								background: 'preset-filled-success-500'
							});
						} else if (succeededCount === 0) {
							toastStore.trigger({
								message: m.batchActionAllFailed({ count: failedCount }),
								background: 'preset-filled-error-500'
							});
						} else {
							toastStore.trigger({
								message: m.batchActionPartialSuccess({
									succeeded: succeededCount,
									failed: failedCount
								}),
								background: 'preset-filled-warning-500'
							});
						}

						handler.invalidate();
						onClearSelection();
					} catch (e) {
						console.error('Batch action failed', e);
						toastStore.trigger({
							message: m.batchActionAllFailed({ count }),
							background: 'preset-filled-error-500'
						});
					}
				}
			}
		};

		const title = action.type === 'delete' ? m.delete() : safeTranslate(action.label);

		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title
		};

		modalStore.trigger(modal);
	}
</script>

<div class="flex justify-between items-center w-full h-full">
	<div class="flex items-center gap-3">
		<span class="text-sm font-medium text-gray-700">
			{m.itemsSelected({ count: selectedIds.size })}
		</span>
		<button
			type="button"
			class="text-sm text-primary-600 hover:text-primary-800 underline"
			onclick={onClearSelection}
		>
			{m.clearSelection()}
		</button>
	</div>
	<div class="flex gap-2 items-center">
		{#each actions as action, index}
			{#if action.type === 'group' && action.children}
				<div class="relative">
					<button
						type="button"
						class="btn text-sm preset-tonal-primary hover:ring-2 hover:ring-primary-500"
						onclick={() => toggleGroup(index)}
					>
						<i class={action.icon}></i>
						<span>{safeTranslate(action.label)}</span>
						<i class="fa-solid fa-chevron-down text-xs ml-1"></i>
					</button>
					{#if openGroupIndex === index}
						<div
							class="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded shadow-lg z-50 min-w-max"
						>
							{#each action.children as child}
								<button
									type="button"
									class="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
									onclick={() => triggerAction(child)}
								>
									<i class={child.icon}></i>
									<span>{safeTranslate(child.label)}</span>
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{:else}
				<button
					type="button"
					class="btn text-sm {action.type === 'delete'
						? 'preset-tonal-error hover:ring-2 hover:ring-error-500'
						: 'preset-tonal-primary hover:ring-2 hover:ring-primary-500'}"
					onclick={() => triggerAction(action)}
				>
					<i class={action.icon}></i>
					<span>{safeTranslate(action.label)}</span>
				</button>
			{/if}
		{/each}
	</div>
</div>
