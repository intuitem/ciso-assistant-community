<script lang="ts">
	import EntityPickerModal from './EntityPickerModal.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { invalidateAll } from '$app/navigation';
	import { getToastStore } from '$lib/components/Toast/stores';

	interface Props {
		parent: any;
		parentId: string;
		urlModel: string;
	}

	let { parent, parentId, urlModel }: Props = $props();

	const toastStore = getToastStore();

	// The picker's selection is page-scoped (max page size 100), which
	// BATCH_SIZE_LIMIT is guaranteed to accommodate — one POST per confirm.
	// Larger scopes are composed round by round: the picker stays open and its
	// exclude_bia filter drops just-added assets from the next page.
	async function onConfirm(ids: string[]) {
		const res = await fetch(`/${urlModel}/batch-create`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ bia: parentId, assets: ids })
		});
		const data = await res.json().catch(() => ({}));
		if (!res.ok) {
			toastStore.trigger({
				message: typeof data.error === 'string' ? safeTranslate(data.error) : m.anErrorOccurred(),
				background: 'preset-filled-error-500'
			});
			throw new Error('Batch add assets failed');
		}
		const created = data.created ?? 0;
		const skipped = data.skipped ?? 0;
		const errorCount = data.errors?.length ?? 0;
		const messages = [];
		if (created > 0) messages.push(m.batchAddAssetsCreated({ count: created }));
		if (skipped > 0) messages.push(m.batchAddAssetsSkipped({ count: skipped }));
		if (errorCount > 0) messages.push(m.batchAddAssetsErrors({ count: errorCount }));
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
