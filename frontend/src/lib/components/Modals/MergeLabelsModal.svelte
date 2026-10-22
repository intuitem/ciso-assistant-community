<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { onMount } from 'svelte';
	import type { DataHandler } from '@vincjo/datatables/remote';

	interface Props {
		parent: any;
		sourceIds: string[];
		handler: DataHandler;
		onClearSelection: () => void;
	}

	let { parent, sourceIds, handler, onClearSelection }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();

	type LabelSummary = { id: string; label: string; usage: number };

	let labels: LabelSummary[] = $state([]);
	let targetId = $state('');
	let submitting = $state(false);

	const target = $derived(labels.find((l) => l.id === targetId));
	const others = $derived(labels.filter((l) => l.id !== targetId));

	onMount(async () => {
		const rows = await Promise.all(
			sourceIds.map((id) =>
				fetch(`/filtering-labels/${id}`)
					.then((r) => (r.ok ? r.json() : null))
					.catch(() => null)
			)
		);
		labels = rows
			.filter(Boolean)
			.map((r: any) => ({
				id: r.id,
				label: r.label,
				usage: r.usage_count ?? 0
			}))
			.sort((a, b) => b.usage - a.usage);
		targetId = labels[0]?.id ?? '';
	});

	async function handleConfirm() {
		submitting = true;
		try {
			const res = await fetch('/filtering-labels/merge', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ target: targetId, sources: others.map((l) => l.id) })
			});
			if (!res.ok) {
				toastStore.trigger({
					message: m.mergeLabelsError(),
					background: 'preset-filled-error-500'
				});
				return;
			}
			toastStore.trigger({
				message: m.mergeLabelsSuccess({ label: target?.label ?? '' }),
				background: 'preset-filled-success-500'
			});
			handler.invalidate();
			onClearSelection();
			parent.onClose();
		} finally {
			submitting = false;
		}
	}
</script>

{#if $modalStore[0]}
	<div
		class="card bg-surface-100-900 border border-surface-500 p-6 w-modal max-w-xl space-y-4"
		role="dialog"
		aria-modal="true"
		aria-labelledby="merge-labels-title"
	>
		<header id="merge-labels-title" class="text-xl font-medium text-surface-900-100">
			{m.mergeLabels()}
		</header>
		<p class="text-sm text-surface-600-400">{m.mergeLabelsHelp()}</p>

		<fieldset class="space-y-2">
			<legend class="text-sm font-semibold text-surface-700-300 mb-2">{m.labelToKeep()}</legend>
			{#each labels as l (l.id)}
				<label
					class="flex items-center gap-3 rounded border px-3 py-2 cursor-pointer text-sm
					{l.id === targetId
						? 'border-primary-500 bg-primary-50 dark:bg-primary-950'
						: 'border-surface-300-700'}"
				>
					<input type="radio" name="merge-target" value={l.id} bind:group={targetId} />
					<span class="badge preset-tonal-secondary font-medium">{l.label}</span>
					<span class="ml-auto text-surface-700-300">{m.objectsCount({ count: l.usage })}</span>
				</label>
			{/each}
		</fieldset>

		{#if target}
			<div class="rounded border border-surface-300-700 bg-surface-50-950 p-3 text-sm space-y-1">
				<p>
					{m.mergeLabelsSummary({
						labels: others.map((l) => l.label).join(', '),
						target: target.label
					})}
				</p>
			</div>
		{/if}

		<footer class="flex gap-3 justify-end pt-2">
			<button type="button" class="btn preset-tonal" onclick={parent.onClose} disabled={submitting}>
				{m.cancel()}
			</button>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				disabled={!target || others.length === 0 || submitting}
				onclick={handleConfirm}
				data-testid="merge-labels-confirm"
			>
				{m.mergeInto({ label: target?.label ?? '' })}
			</button>
		</footer>
	</div>
{/if}
