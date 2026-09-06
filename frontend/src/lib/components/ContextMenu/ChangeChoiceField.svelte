<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';
	import { getModelInfo } from '$lib/utils/crud';

	interface Props {
		row: any;
		handler: DataHandler;
		URLModel: string;
		// `{ field, labelKey }` from the contextMenuActions entry.
		action: { props: { field: string; labelKey: string } };
	}

	let { row, handler, URLModel, action }: Props = $props();

	const { field, labelKey } = action.props;
	const flash = getFlash(page);

	let options: { label: string; value: string }[] = $state([]);

	onMount(async () => {
		// `[filter=filters]` turns the backend's `{value: label}` into a list.
		const res = await fetch(`/${URLModel}/${field}`);
		if (res.ok) options = await res.json();
	});

	const objectLabel = $derived(
		safeTranslate(getModelInfo(URLModel)?.localName ?? URLModel).toLowerCase()
	);

	async function change(value: string) {
		try {
			const res = await fetch(`/${URLModel}/${row?.meta?.id}/${field}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ [field]: value })
			});
			if (!res.ok) throw new Error(String(res.status));
			flash.set({
				type: 'success',
				message: m.successfullyUpdatedObject({ object: objectLabel })
			});
			handler.invalidate();
		} catch (error) {
			flash.set({
				type: 'error',
				message: m.errorUpdatingObject({ object: objectLabel })
			});
			console.error(`Error changing ${field}:`, error);
		}
	}
</script>

<ContextMenu.Sub>
	<ContextMenu.SubTrigger
		class="flex h-10 select-none items-center rounded-button py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-muted data-[state=open]:bg-surface-50"
	>
		<div class="flex items-center">{safeTranslate(labelKey)}</div>
	</ContextMenu.SubTrigger>
	<ContextMenu.SubContent
		class="z-50 w-full min-w-[180px] max-w-[209px] outline-hidden card bg-surface-50-950 px-1 py-1.5 shadow-md border border-surface-200 cursor-default data-highlighted:bg-surface-50"
		sideOffset={10}
	>
		{#each options as option}
			<ContextMenu.Item
				class="flex h-10 select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! hover:bg-surface-50"
				onclick={async () => await change(option.value)}
			>
				{safeTranslate(option.label)}
			</ContextMenu.Item>
		{/each}
	</ContextMenu.SubContent>
</ContextMenu.Sub>
