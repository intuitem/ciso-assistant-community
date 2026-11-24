<script lang="ts">
	import type { urlModel } from '#lib/utils/types.js';
	import { m } from '#paraglide/messages.js';
	import SuperDebug from 'sveltekit-superforms';
	import { getModalStore, type ModalStore } from './stores';
	import { superForm } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import CascadeGroupList, {
		type CascadeGroup,
		type CascadeObject
	} from '#lib/components/Modals/CascadeGroupList.svelte';

	const modalStore: ModalStore = getModalStore();

	const cBase = 'card bg-surface-100-900 border border-surface-500 p-6 w-modal space-y-6';
	const cHeader = 'text-xl font-medium text-surface-950-50';
	const cForm = 'space-y-4';

	interface Props {
		parent: any;
		_form: any;
		URLModel: urlModel;
		formAction?: string;
		invalidateAll?: boolean;
		id: string;
		debug?: boolean;
	}

	let {
		parent,
		_form,
		URLModel,
		formAction = '?/delete',
		invalidateAll = true,
		id,
		debug = false
	}: Props = $props();

	const { form, enhance } = superForm(_form, { invalidateAll });

	type Bucket = {
		count: number;
		grouped_objects: CascadeGroup[];
		related_objects?: CascadeObject[];
		message?: string;
		level?: string;
	};

	let cascadeInfo: { deleted: Bucket; affected: Bucket; blocked?: Bucket } | null = $state(null);
	let loading = $state(true);
	let errorMsg = $state<string | null>(null);

	// PROTECT/RESTRICT references make the delete fail server-side.
	const isBlocked = $derived((cascadeInfo?.blocked?.count ?? 0) > 0);

	onMount(async () => {
		try {
			const res = await fetch(`/fe-api/cascade-info/${URLModel}/${id}`);
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			cascadeInfo = await res.json();
		} catch (e) {
			errorMsg = m.errorFetching();
			console.error(e);
		} finally {
			loading = false;
		}
	});
</script>

{#if $modalStore[0]}
	<div
		class="modal-example-form {cBase}"
		role="dialog"
		aria-modal="true"
		aria-labelledby="modal-title"
	>
		<header id="modal-title" class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>

		<article>{$modalStore[0].body ?? '(body missing)'}</article>

		{#if loading}
			<div class="text-sm text-surface-600-400">Loading...</div>
		{:else if errorMsg}
			<div class="p-4 bg-error-50-950 text-error-900-100 text-sm">
				{errorMsg}
			</div>
		{:else if cascadeInfo}
			{#if isBlocked && cascadeInfo.blocked}
				<div class="p-4 bg-error-50 dark:bg-error-500/15 border-l-2 border-error-500">
					<div class="text-sm font-medium text-surface-950-50 mb-3">
						{m.cascadeBlockedWarning({ count: cascadeInfo.blocked.count })}
					</div>

					<div class="max-h-64 overflow-y-auto space-y-1">
						<CascadeGroupList groups={cascadeInfo.blocked.grouped_objects} idPrefix="blk" />
					</div>
				</div>
			{/if}

			{#if !isBlocked && cascadeInfo.deleted?.count > 0}
				<div class="p-4 bg-orange-50 dark:bg-orange-500/15 border-l-2 border-orange-400">
					<div class="text-sm font-medium text-surface-950-50 mb-3">
						{m.cascadeDeleteWarning({ count: cascadeInfo.deleted.count })}
					</div>

					<div class="max-h-64 overflow-y-auto space-y-1">
						<CascadeGroupList groups={cascadeInfo.deleted.grouped_objects} idPrefix="del" />
					</div>
				</div>
			{/if}

			{#if !isBlocked && cascadeInfo.affected?.count > 0}
				<div class="p-4 bg-blue-50 dark:bg-blue-500/15 border-l-2 border-blue-400">
					<div class="text-sm font-medium text-surface-950-50 mb-1">
						{m.cascadeAffectedNotice({ count: cascadeInfo.affected.count })}
					</div>
					<p class="text-xs text-surface-600-400 mb-3">
						{m.cascadeAffectedHint()}
					</p>

					<div class="max-h-64 overflow-y-auto space-y-1">
						<CascadeGroupList groups={cascadeInfo.affected.grouped_objects} idPrefix="aff" />
					</div>
				</div>
			{/if}
		{/if}

		<form
			method="POST"
			action={formAction}
			use:enhance={() =>
				({ update }) =>
					update({ navigate: false })}
			class="modal-form {cForm}"
		>
			<footer class="flex gap-3 justify-end pt-4 border-t border-surface-200-800">
				<button
					type="button"
					class="px-4 py-2 text-sm font-medium text-surface-700-300 bg-surface-50-950 border border-surface-300-700 hover:bg-surface-50-950"
					data-testid="delete-cancel-button"
					onclick={parent.onClose}
				>
					{isBlocked ? m.close() : m.cancel()}
				</button>
				<input type="hidden" name="urlmodel" value={URLModel} />
				<input type="hidden" name="id" value={id} />
				{#if !isBlocked}
					<button
						class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800"
						data-testid="delete-confirm-button"
						type="submit"
						onclick={parent.onClose}
					>
						{m.submit()}
					</button>
				{/if}
			</footer>
		</form>

		{#if debug === true}
			<SuperDebug data={$form} />
		{/if}
	</div>
{/if}
