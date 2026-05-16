<script lang="ts">
	import { getModalStore, type ModalStore } from './stores';
	import { m } from '$paraglide/messages';
	import { invalidateAll } from '$app/navigation';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	const modalStore: ModalStore = getModalStore();
	const flash = getFlash(page);

	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	type SuggestionStatus = 'create' | 'reuse' | 'linked';

	interface Item {
		id: string;
		label: string;
		status: SuggestionStatus;
	}

	interface Props {
		parent: any;
		items: Item[];
		endpoint: string;
	}

	let { parent, items, endpoint }: Props = $props();

	const createItems = $derived(items.filter((i) => i.status === 'create'));
	const reuseItems = $derived(items.filter((i) => i.status === 'reuse'));
	const linkedItems = $derived(items.filter((i) => i.status === 'linked'));
	const selectableItems = $derived([...createItems, ...reuseItems]);

	let selectedIds = $state(
		new Set<string>(items.filter((i) => i.status !== 'linked').map((i) => i.id))
	);
	let submitting = $state(false);

	function toggle(id: string) {
		const next = new Set(selectedIds);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedIds = next;
	}

	function toggleAll() {
		if (selectedIds.size === selectableItems.length) {
			selectedIds = new Set();
		} else {
			selectedIds = new Set(selectableItems.map((i) => i.id));
		}
	}

	const allSelected = $derived(
		selectableItems.length > 0 && selectedIds.size === selectableItems.length
	);

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

{#snippet badge(status: SuggestionStatus)}
	{#if status === 'create'}
		<span class="badge preset-tonal-success text-xs whitespace-nowrap"
			><i class="fa-solid fa-plus mr-1"></i>{m.suggestionStatusNew()}</span
		>
	{:else if status === 'reuse'}
		<span class="badge preset-tonal-warning text-xs whitespace-nowrap"
			><i class="fa-solid fa-link mr-1"></i>{m.suggestionStatusReuse()}</span
		>
	{:else}
		<span class="badge preset-tonal-surface text-xs whitespace-nowrap"
			><i class="fa-solid fa-check mr-1"></i>{m.suggestionStatusLinked()}</span
		>
	{/if}
{/snippet}

{#snippet selectableRow(item: Item)}
	<li class="py-1">
		<label class="flex items-center gap-2 cursor-pointer">
			<input
				type="checkbox"
				checked={selectedIds.has(item.id)}
				onchange={() => toggle(item.id)}
				class="checkbox"
			/>
			<span class="flex-1">{item.label}</span>
			{@render badge(item.status)}
		</label>
	</li>
{/snippet}

{#if $modalStore[0]}
	<div class={cBase}>
		<header class={cHeader}>{$modalStore[0].title ?? m.suggestControls()}</header>
		<article>{$modalStore[0].body ?? ''}</article>

		<div class="max-h-96 overflow-y-auto card bg-surface-100">
			{#if selectableItems.length > 1}
				<div class="px-4 py-2 border-b border-surface-300 sticky top-0 bg-surface-100">
					<label class="flex items-center gap-2 cursor-pointer font-semibold text-sm">
						<input type="checkbox" checked={allSelected} onchange={toggleAll} class="checkbox" />
						{m.selectAll()} ({selectedIds.size}/{selectableItems.length})
					</label>
				</div>
			{/if}

			{#if createItems.length > 0}
				<section class="px-4 py-2">
					<p class="font-semibold text-sm mb-1">
						<i class="fa-solid fa-plus text-success-500 mr-1"></i>
						{m.suggestionSectionCreate()} ({createItems.length})
					</p>
					<p class="text-xs text-gray-500 mb-2">{m.suggestionSectionCreateHelp()}</p>
					<ul class="ml-2">
						{#each createItems as item (item.id)}
							{@render selectableRow(item)}
						{/each}
					</ul>
				</section>
			{/if}

			{#if reuseItems.length > 0}
				<section class="px-4 py-2 border-t border-surface-300">
					<p class="font-semibold text-sm mb-1">
						<i class="fa-solid fa-link text-warning-500 mr-1"></i>
						{m.suggestionSectionReuse()} ({reuseItems.length})
					</p>
					<p class="text-xs text-gray-500 mb-2">{m.suggestionSectionReuseHelp()}</p>
					<ul class="ml-2">
						{#each reuseItems as item (item.id)}
							{@render selectableRow(item)}
						{/each}
					</ul>
				</section>
			{/if}

			{#if linkedItems.length > 0}
				<section class="px-4 py-2 border-t border-surface-300 opacity-70">
					<p class="font-semibold text-sm mb-1">
						<i class="fa-solid fa-check text-gray-500 mr-1"></i>
						{m.suggestionSectionLinked()} ({linkedItems.length})
					</p>
					<p class="text-xs text-gray-500 mb-2">{m.suggestionSectionLinkedHelp()}</p>
					<ul class="ml-2">
						{#each linkedItems as item (item.id)}
							<li class="py-1">
								<div class="flex items-center gap-2">
									<i class="fa-regular fa-circle-check text-gray-500"></i>
									<span class="flex-1">{item.label}</span>
									{@render badge(item.status)}
								</div>
							</li>
						{/each}
					</ul>
				</section>
			{/if}
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
