<script lang="ts">
	import { deserialize } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import ValidationFlowActionModal from '$lib/components/Modals/ValidationFlowActionModal.svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { formatDateOrDateTime, timeAgo } from '$lib/utils/datetime';
	import { safeTranslate } from '$lib/utils/i18n';
	import {
		VALIDATION_ACTION_CLASSES,
		VALIDATION_ACTION_ICONS,
		validationActionLabels,
		validationFlowActions,
		validationFlowLinkedObjects,
		validationFlowModelLabels,
		validationStatusColor,
		type ValidationFlowAction
	} from '$lib/utils/validationFlows';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime.js';

	interface Props {
		flow: any;
		userId: string;
		/** Sent flows are about the approver; received and past ones about the requester. */
		counterpart?: 'requester' | 'approver';
	}

	let { flow, userId, counterpart = 'requester' }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const modelLabels = validationFlowModelLabels();
	const actionLabels = validationActionLabels();

	const linkedObjects = $derived(validationFlowLinkedObjects(flow));
	const actions = $derived(validationFlowActions(flow, userId));
	const person = $derived(flow[counterpart]);
	const isOverdue = $derived(
		Boolean(flow.validation_deadline) &&
			['submitted', 'change_requested'].includes(flow.status) &&
			new Date(`${flow.validation_deadline}T23:59:59`) < new Date()
	);
	const notes = $derived(flow.request_notes ?? '');

	function personName(user: any): string {
		if (!user) return '--';
		const name = [user.first_name, user.last_name].filter(Boolean).join(' ');
		return name || user.email;
	}

	function runAction(action: ValidationFlowAction) {
		modalStore.trigger({
			type: 'component',
			component: {
				ref: ValidationFlowActionModal,
				props: {
					action,
					onConfirm: async (eventNotes: string) => {
						const formData = new FormData();
						formData.append('id', flow.id);
						formData.append('notes', eventNotes);
						const response = await fetch(`?/${action}`, {
							method: 'POST',
							body: formData,
							headers: { 'x-sveltekit-action': 'true' }
						});
						const result = deserialize(await response.text());
						if (result.type === 'failure' || result.type === 'error') {
							throw new Error(m.anErrorOccurred());
						}
					},
					onSuccess: () => invalidateAll()
				}
			}
		});
	}
</script>

<div
	class="card bg-surface-50-950 border border-surface-200-800 hover:border-primary-300 transition p-4 flex flex-col gap-3 md:flex-row md:items-start md:justify-between"
	data-testid="validation-flow-card"
>
	<div class="flex flex-col gap-2 min-w-0 flex-1">
		<div class="flex items-center gap-2 flex-wrap">
			<span
				class="badge {validationStatusColor(
					flow.status
				)} px-2 py-0.5 rounded-full text-xs font-medium"
			>
				{safeTranslate(flow.status)}
			</span>
			<Anchor href="/validation-flows/{flow.id}" class="anchor font-semibold">
				{flow.ref_id ?? flow.str}
			</Anchor>
			{#if isOverdue}
				<span class="badge bg-red-100 text-red-800 px-2 py-0.5 rounded-full text-xs font-medium">
					<i class="fa-solid fa-triangle-exclamation mr-1"></i>{m.overdue()}
				</span>
			{/if}
		</div>

		{#if linkedObjects.length}
			<div class="flex flex-col gap-1">
				{#each linkedObjects.slice(0, 3) as { key, item, href }}
					<div class="flex items-baseline gap-2 min-w-0">
						<span class="text-xs text-surface-500 whitespace-nowrap">{modelLabels[key]}</span>
						<Anchor {href} class="anchor text-sm truncate">{item.str}</Anchor>
					</div>
				{/each}
				{#if linkedObjects.length > 3}
					<span class="text-xs text-surface-500"
						>{m.andNMoreObjects({ count: String(linkedObjects.length - 3) })}</span
					>
				{/if}
			</div>
		{:else}
			<span class="text-sm text-surface-500 italic">{m.noLinkedObjects()}</span>
		{/if}

		{#if notes}
			<p class="text-sm text-surface-600-400 line-clamp-2">{notes}</p>
		{/if}

		<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-surface-600-400">
			<span>
				<i class="fa-solid fa-user mr-1 text-surface-400-600"></i>
				{counterpart === 'approver' ? m.approver() : m.requester()}: {personName(person)}
			</span>
			<span title={formatDateOrDateTime(flow.created_at, getLocale()) ?? ''}>
				<i class="fa-solid fa-clock mr-1 text-surface-400-600"></i>
				{timeAgo(flow.created_at, getLocale())}
			</span>
			{#if flow.validation_deadline}
				<span class={isOverdue ? 'text-red-700 font-medium' : ''}>
					<i class="fa-solid fa-calendar-day mr-1 text-surface-400-600"></i>
					{m.validationDeadline()}: {formatDateOrDateTime(flow.validation_deadline, getLocale())}
				</span>
			{/if}
			{#if flow.folder}
				<span>
					<i class="fa-solid fa-folder mr-1 text-surface-400-600"></i>
					{flow.folder.str}
				</span>
			{/if}
		</div>
	</div>

	<div class="flex flex-wrap items-center gap-2 md:justify-end md:shrink-0">
		{#each actions as action}
			<button
				type="button"
				class="btn btn-sm {VALIDATION_ACTION_CLASSES[action]}"
				data-testid="{action.replace('_', '-')}-button"
				onclick={() => runAction(action)}
			>
				<i class="fa-solid {VALIDATION_ACTION_ICONS[action]} mr-1"></i>
				{actionLabels[action]}
			</button>
		{/each}
		<Anchor
			href="/validation-flows/{flow.id}"
			class="btn btn-sm preset-tonal-surface"
			label={m.details()}
		>
			{m.details()}
			<i class="fa-solid fa-chevron-right ml-1"></i>
		</Anchor>
	</div>
</div>
