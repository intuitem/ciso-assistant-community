<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';
	import { invalidateAll } from '$app/navigation';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { onMount } from 'svelte';

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();

	const cBase = 'card bg-surface-50-950 p-6 w-modal space-y-6';
	const cHeader = 'text-xl font-medium text-surface-900-100';

	interface Props {
		parent: any;
		parentId: string;
		urlModel: string;
	}

	let { parent, parentId, urlModel }: Props = $props();

	let options: { label: string; value: string; included: boolean }[] = $state([]);
	let selectedValues: string[] = $state([]);
	let searchQuery: string = $state('');
	let loading = $state(true);
	let submitting = $state(false);

	const filteredOptions = $derived(
		searchQuery.trim()
			? options.filter((o) => o.label.toLowerCase().includes(searchQuery.trim().toLowerCase()))
			: options
	);

	const selectableCount = $derived(options.filter((o) => !o.included).length);

	const canSubmit = $derived(selectedValues.length > 0 && !submitting);

	onMount(async () => {
		try {
			const [assetsRes, existingRes] = await Promise.all([
				fetch('/assets/autocomplete'),
				fetch(`/asset-assessments?bia=${parentId}`)
			]);
			const included: Set<string> = new Set();
			if (existingRes.ok) {
				const data = await existingRes.json();
				for (const aa of data.results ?? data ?? []) {
					if (aa.asset?.id) included.add(String(aa.asset.id));
				}
			}
			if (assetsRes.ok) {
				const data = await assetsRes.json();
				options = (data.results ?? data ?? []).map((a: any) => ({
					label: a.folder?.str ? `${a.name} (${a.folder.str})` : a.name,
					value: String(a.id),
					included: included.has(String(a.id))
				}));
			}
		} catch (e) {
			console.error('Failed to fetch assets', e);
		} finally {
			loading = false;
		}
	});

	function toggleValue(value: string) {
		if (selectedValues.includes(value)) {
			selectedValues = selectedValues.filter((v) => v !== value);
		} else {
			selectedValues = [...selectedValues, value];
		}
	}

	function selectAll() {
		selectedValues = [
			...new Set([
				...selectedValues,
				...filteredOptions.filter((o) => !o.included).map((o) => o.value)
			])
		];
	}

	function deselectAll() {
		selectedValues = [];
	}

	async function handleSubmit() {
		submitting = true;
		try {
			const res = await fetch(`/${urlModel}/batch-create`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ bia: parentId, assets: selectedValues })
			});
			const data = await res.json();
			if (res.ok && data.success) {
				const messages = [];
				if (data.created > 0) {
					messages.push(m.batchAddAssetsCreated({ count: data.created }));
				}
				if (data.skipped > 0) {
					messages.push(m.batchAddAssetsSkipped({ count: data.skipped }));
				}
				if (data.errors?.length > 0) {
					messages.push(`${data.errors.length} error(s)`);
				}
				toastStore.trigger({ message: messages.join(', ') });
				await invalidateAll();
				parent.onClose();
			} else {
				toastStore.trigger({
					message:
						data.error ||
						(data.errors?.length ? `${data.errors.length} error(s)` : m.anErrorOccurred()),
					background: 'preset-filled-error-500'
				});
			}
		} catch (e) {
			console.error('Batch add assets failed', e);
			toastStore.trigger({
				message: m.anErrorOccurred(),
				background: 'preset-filled-error-500'
			});
		} finally {
			submitting = false;
		}
	}
</script>

{#if $modalStore[0]}
	<div class={cBase} role="dialog" aria-modal="true" aria-labelledby="modal-title">
		<header id="modal-title" class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>

		{#if loading}
			<div class="text-sm text-surface-600-400">{m.loading()}...</div>
		{:else}
			<div class="space-y-2">
				<input
					type="text"
					class="input w-full border border-surface-300-700 rounded px-3 py-2 text-sm"
					aria-label={m.search()}
					placeholder={m.searchPlaceholder()}
					bind:value={searchQuery}
				/>
				<div class="flex items-center justify-between text-sm">
					<div class="space-x-3">
						<button type="button" class="anchor" onclick={selectAll}>{m.selectAll()}</button>
						<button type="button" class="anchor" onclick={deselectAll}>{m.deselectAll()}</button>
					</div>
					<span class="text-surface-600-400">{selectedValues.length} / {selectableCount}</span>
				</div>
				<div class="max-h-64 overflow-y-auto border border-surface-200-800 rounded">
					{#each filteredOptions as option (option.value)}
						<label
							class="flex items-center gap-2 px-3 py-1.5 border-b border-surface-100-900 last:border-b-0 {option.included
								? 'opacity-50'
								: 'hover:bg-surface-50-950 cursor-pointer'}"
						>
							<input
								type="checkbox"
								checked={option.included || selectedValues.includes(option.value)}
								disabled={option.included}
								onchange={() => toggleValue(option.value)}
								class="checkbox"
							/>
							<span class="text-sm">{option.label}</span>
							{#if option.included}
								<span class="ml-auto text-xs text-surface-500">{m.alreadyIncluded()}</span>
							{/if}
						</label>
					{/each}
					{#if filteredOptions.length === 0}
						<div class="px-3 py-2 text-sm text-surface-400-600">{m.noEntriesFound()}</div>
					{/if}
				</div>
			</div>
		{/if}

		<footer class="flex gap-3 justify-end pt-4 border-t border-surface-200-800">
			<button type="button" class="btn preset-outlined-surface-500" onclick={parent.onClose}>
				{m.cancel()}
			</button>
			<button
				class="btn preset-filled-primary-500"
				data-testid="batch-add-assets-confirm-button"
				disabled={!canSubmit}
				onclick={handleSubmit}
			>
				{m.submit()}
			</button>
		</footer>
	</div>
{/if}
