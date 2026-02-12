<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { onMount } from 'svelte';

	const modalStore: ModalStore = getModalStore();

	const cBase = 'card bg-white p-6 w-modal space-y-6';
	const cHeader = 'text-xl font-medium text-gray-900';

	interface Props {
		parent: any;
		actionType: 'delete' | 'change_status' | 'change_owner';
		count: number;
		optionsEndpoint?: string;
		onConfirm: (value?: string | string[]) => void;
	}

	let { parent, actionType, count, optionsEndpoint, onConfirm }: Props = $props();

	let options: { label: string; value: string }[] = $state([]);
	let selectedValue: string = $state('');
	let selectedValues: string[] = $state([]);
	let loading = $state(false);

	const isValueAction = actionType === 'change_status' || actionType === 'change_owner';
	const isMultiSelect = actionType === 'change_owner';

	onMount(async () => {
		if (isValueAction && optionsEndpoint) {
			loading = true;
			try {
				const res = await fetch(`/${optionsEndpoint}`);
				if (res.ok) {
					const data = await res.json();
					options = Array.isArray(data)
						? data.map((item: any) => ({
								label: item.label || item.str || item.name || String(item.value),
								value: String(item.value || item.id)
							}))
						: Object.entries(data).map(([key, val]) => ({
								label: String(val),
								value: key
							}));
				}
			} catch (e) {
				console.error('Failed to fetch options', e);
			} finally {
				loading = false;
			}
		}
	});

	function handleConfirm() {
		if (actionType === 'delete') {
			onConfirm();
		} else if (isMultiSelect) {
			onConfirm(selectedValues);
		} else {
			onConfirm(selectedValue);
		}
		parent.onClose();
	}

	function toggleOwnerValue(value: string) {
		if (selectedValues.includes(value)) {
			selectedValues = selectedValues.filter((v) => v !== value);
		} else {
			selectedValues = [...selectedValues, value];
		}
	}

	const canConfirm = $derived(
		actionType === 'delete' || (isMultiSelect ? selectedValues.length > 0 : selectedValue !== '')
	);
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

		{#if actionType === 'delete'}
			<article>{m.batchActionConfirmDelete({ count })}</article>
		{:else}
			<article>{m.batchActionConfirmChange({ count })}</article>

			{#if loading}
				<div class="text-sm text-gray-500">Loading...</div>
			{:else if isMultiSelect}
				<div class="max-h-64 overflow-y-auto space-y-1">
					{#each options as option}
						<label class="flex items-center gap-2 px-2 py-1 hover:bg-gray-50 cursor-pointer">
							<input
								type="checkbox"
								checked={selectedValues.includes(option.value)}
								onchange={() => toggleOwnerValue(option.value)}
								class="checkbox"
							/>
							<span class="text-sm">{safeTranslate(option.label)}</span>
						</label>
					{/each}
				</div>
			{:else}
				<select
					class="select w-full border border-gray-300 rounded px-3 py-2"
					bind:value={selectedValue}
				>
					<option value="" disabled>--</option>
					{#each options as option}
						<option value={option.value}>{safeTranslate(option.label)}</option>
					{/each}
				</select>
			{/if}
		{/if}

		<footer class="flex gap-3 justify-end pt-4 border-t border-gray-200">
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
				data-testid="batch-cancel-button"
				onclick={parent.onClose}
			>
				{m.cancel()}
			</button>
			<button
				class="px-4 py-2 text-sm font-medium text-white {actionType === 'delete'
					? 'bg-red-600 hover:bg-red-700'
					: 'bg-indigo-600 hover:bg-indigo-700'}"
				data-testid="batch-confirm-button"
				disabled={!canConfirm}
				onclick={handleConfirm}
			>
				{m.submit()}
			</button>
		</footer>
	</div>
{/if}
