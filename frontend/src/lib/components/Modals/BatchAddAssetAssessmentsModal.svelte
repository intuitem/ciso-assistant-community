<script lang="ts">
	import EntityPickerModal from './EntityPickerModal.svelte';
	import { m } from '$paraglide/messages';
	import { invalidateAll } from '$app/navigation';
	import { getToastStore } from '$lib/components/Toast/stores';

	interface Props {
		parent: any;
		parentId: string;
		urlModel: string;
	}

	let { parent, parentId, urlModel }: Props = $props();

	const toastStore = getToastStore();

	async function postChunk(ids: string[]) {
		const res = await fetch(`/${urlModel}/batch-create`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ bia: parentId, assets: ids })
		});
		const data = await res.json().catch(() => ({}));
		return { ok: res.ok, data };
	}

	async function onConfirm(ids: string[]) {
		let created = 0;
		let skipped = 0;
		let errorCount = 0;
		const queue: string[][] = [ids];
		while (queue.length) {
			const chunk = queue.shift()!;
			const { ok, data } = await postChunk(chunk);
			if (!ok && typeof data.max === 'number' && chunk.length > data.max) {
				for (let i = 0; i < chunk.length; i += data.max) {
					queue.push(chunk.slice(i, i + data.max));
				}
				continue;
			}
			if (!ok) {
				toastStore.trigger({
					message: data.error || m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				throw new Error('Batch add assets failed');
			}
			created += data.created ?? 0;
			skipped += data.skipped ?? 0;
			errorCount += data.errors?.length ?? 0;
		}
		const messages = [];
		if (created > 0) messages.push(m.batchAddAssetsCreated({ count: created }));
		if (skipped > 0) messages.push(m.batchAddAssetsSkipped({ count: skipped }));
		if (errorCount > 0) messages.push(`${errorCount} error(s)`);
		toastStore.trigger({
			message: messages.join(', ') || m.anErrorOccurred(),
			...(created === 0 && errorCount > 0 ? { background: 'preset-filled-error-500' } : {})
		});
		await invalidateAll();
	}
</script>

<EntityPickerModal
	{parent}
	endpoint="assets"
	title={m.batchAddAssets()}
	scopeFilters={{ exclude_bia: parentId }}
	secondaryField="folder.str"
	confirmLabel={m.batchAddAssets()}
	{onConfirm}
/>
