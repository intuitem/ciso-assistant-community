<script lang="ts">
	import { getModalStore, type ModalStore } from './stores';
	import { m } from '$paraglide/messages';
	import SelectableList from '$lib/components/List/SelectableList.svelte';
	import { invalidateAll } from '$app/navigation';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	const modalStore: ModalStore = getModalStore();
	const flash = getFlash(page);

	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		parent: any;
		items: { id: string; label: string }[];
		endpoint: string;
	}

	let { parent, items, endpoint }: Props = $props();

	let selectedIds = $state(new Set(items.map((item) => item.id)));
	let submitting = $state(false);

	async function handleSubmit() {
		submitting = true;
		try {
			const response = await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ selected_reference_control_ids: [...selectedIds] })
			});
			if (response.ok) {
				const createdControls = await response.json();
				const newControlIds = createdControls.map((c: any) => c.id);
				flash.set({
					type: 'success',
					message: m.createAppliedControlsFromSuggestionsSuccess()
				});
				if ($modalStore[0]) {
					$modalStore[0].response?.(newControlIds);
				}
				modalStore.close();
				await invalidateAll();
			} else {
				flash.set({
					type: 'error',
					message: m.createAppliedControlsFromSuggestionsError()
				});
				if ($modalStore[0]) {
					$modalStore[0].response?.(false);
				}
				modalStore.close();
			}
		} catch {
			flash.set({
				type: 'error',
				message: m.createAppliedControlsFromSuggestionsError()
			});
			if ($modalStore[0]) {
				$modalStore[0].response?.(false);
			}
			modalStore.close();
		}
	}
</script>

{#if $modalStore[0]}
	<div class={cBase}>
		<header class={cHeader}>{$modalStore[0].title ?? m.suggestControls()}</header>
		<article>{$modalStore[0].body ?? ''}</article>
		<div class="max-h-96 overflow-y-auto scroll card">
			<SelectableList {items} bind:selectedIds message={m.theFollowingControlsWillBeAddedColon()} />
		</div>
		<footer class="flex justify-end gap-2">
			<button
				type="button"
				class="btn {parent.buttonNeutral}"
				onclick={() => {
					if ($modalStore[0]) {
						$modalStore[0].response?.(false);
					}
					parent.onClose();
				}}>{m.cancel()}</button
			>
			<button
				class="btn preset-filled-primary-500"
				disabled={selectedIds.size === 0 || submitting}
				onclick={handleSubmit}
			>
				{#if submitting}
					<i class="fa-solid fa-spinner fa-spin mr-2"></i>
				{/if}
				{m.submit()} ({selectedIds.size})
			</button>
		</footer>
	</div>
{/if}
