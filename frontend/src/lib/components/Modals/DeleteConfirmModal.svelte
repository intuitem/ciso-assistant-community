<script lang="ts">
	import type { urlModel } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import SuperDebug from 'sveltekit-superforms';
	import { getModalStore, type ModalStore } from './stores';
	import { superForm } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import CascadePreview, {
		isCascadeBlocked,
		type CascadeInfo
	} from '$lib/components/Modals/CascadePreview.svelte';

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

	let cascadeInfo: CascadeInfo | null = $state(null);
	let loading = $state(true);
	let errorMsg = $state<string | null>(null);

	const isBlocked = $derived(isCascadeBlocked(cascadeInfo));

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
			<CascadePreview {cascadeInfo} />
		{/if}

		<form method="POST" action={formAction} use:enhance class="modal-form {cForm}">
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
