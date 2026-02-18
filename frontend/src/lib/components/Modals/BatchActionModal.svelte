<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { onMount } from 'svelte';

	const modalStore: ModalStore = getModalStore();

	const cBase = 'card bg-surface-50-950 p-6 w-modal space-y-6';
	const cHeader = 'text-xl font-medium text-surface-950-50';

	interface Props {
		parent: any;
		actionType: 'delete' | 'change_field' | 'change_m2m' | 'change_folder';
		count: number;
		optionsEndpoint?: string;
		multiSelect?: boolean;
		onConfirm: (value?: string | string[]) => void;
	}

	let {
		parent,
		actionType,
		count,
		optionsEndpoint,
		multiSelect = false,
		onConfirm
	}: Props = $props();

	let options: { label: string; value: string }[] = $state([]);
	let selectedValue: string = $state('');
	let selectedValues: string[] = $state([]);
	let loading = $state(false);
	let searchQuery: string = $state('');
	let deleteConfirmInput: string = $state('');

	const isValueAction = actionType !== 'delete';
	const yes = m.yes().toLowerCase();

	const filteredOptions = $derived(
		searchQuery.trim()
			? options.filter((o) => o.label.toLowerCase().includes(searchQuery.trim().toLowerCase()))
			: options
	);

	function parseOptions(data: any): { label: string; value: string }[] {
		// Handle paginated responses (e.g. { results: [...], count: N })
		const items = data?.results ?? data;

		if (Array.isArray(items)) {
			return items.map((item: any) => ({
				label: item.label || item.str || item.name || String(item.value ?? item.id),
				value: String(item.value ?? item.id)
			}));
		}
		// Handle dict responses (e.g. { "open": "Open", "closed": "Closed" })
		return Object.entries(items).map(([key, val]) => ({
			label: String(val),
			value: key
		}));
	}

	onMount(async () => {
		if (isValueAction && optionsEndpoint) {
			loading = true;
			try {
				const res = await fetch(`/${optionsEndpoint}`);
				if (res.ok) {
					const data = await res.json();
					options = parseOptions(data);
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
		} else if (multiSelect) {
			onConfirm(selectedValues);
		} else {
			onConfirm(selectedValue);
		}
		parent.onClose();
	}

	function toggleValue(value: string) {
		if (selectedValues.includes(value)) {
			selectedValues = selectedValues.filter((v) => v !== value);
		} else {
			selectedValues = [...selectedValues, value];
		}
	}

	const canConfirm = $derived(
		actionType === 'delete'
			? !!deleteConfirmInput && deleteConfirmInput.trim().toLowerCase() === yes
			: multiSelect
				? selectedValues.length > 0
				: selectedValue !== ''
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
			<div class="space-y-2">
				<p class="text-sm font-medium text-red-600">{m.confirmYes()}</p>
				<input
					type="text"
					data-testid="batch-delete-confirm-textfield"
					bind:value={deleteConfirmInput}
					placeholder={m.confirmYesPlaceHolder()}
					class="input w-full"
					aria-label={m.confirmYes()}
				/>
			</div>
		{:else}
			<article>{m.batchActionConfirmChange({ count })}</article>

			{#if loading}
				<div class="text-sm text-surface-600-400">Loading...</div>
			{:else if multiSelect}
				<div class="space-y-2">
					<input
						type="text"
						class="input w-full border border-surface-300-700 rounded px-3 py-2 text-sm"
						placeholder={m.searchPlaceholder()}
						bind:value={searchQuery}
					/>
					{#if selectedValues.length > 0}
						<div class="flex flex-wrap gap-1">
							{#each selectedValues as val}
								{@const opt = options.find((o) => o.value === val)}
								{#if opt}
									<span
										class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary-100 text-primary-800 text-xs"
									>
										{safeTranslate(opt.label)}
										<button
											type="button"
											class="hover:text-primary-600"
											onclick={() => toggleValue(val)}
										>
											<i class="fa-solid fa-xmark text-xs"></i>
										</button>
									</span>
								{/if}
							{/each}
						</div>
					{/if}
					<div class="max-h-48 overflow-y-auto border border-surface-200-800 rounded">
						{#each filteredOptions as option}
							<label
								class="flex items-center gap-2 px-3 py-1.5 hover:bg-surface-50-950 cursor-pointer border-b border-surface-100-900 last:border-b-0"
							>
								<input
									type="checkbox"
									checked={selectedValues.includes(option.value)}
									onchange={() => toggleValue(option.value)}
									class="checkbox"
								/>
								<span class="text-sm">{safeTranslate(option.label)}</span>
							</label>
						{/each}
						{#if filteredOptions.length === 0}
							<div class="px-3 py-2 text-sm text-surface-400-600">
								{m.noResultsFound()}
							</div>
						{/if}
					</div>
				</div>
			{:else}
				<select
					class="select w-full border border-surface-300-700 rounded px-3 py-2"
					bind:value={selectedValue}
				>
					<option value="" disabled>--</option>
					{#each options as option}
						<option value={option.value}>{safeTranslate(option.label)}</option>
					{/each}
				</select>
			{/if}
		{/if}

		<footer class="flex gap-3 justify-end pt-4 border-t border-surface-200-800">
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-surface-700-300 bg-surface-50-950 border border-surface-300-700 hover:bg-surface-50-950"
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
