<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { DataHandler } from '@vincjo/datatables/remote';
	import type { urlModel } from '$lib/utils/types';
	import { ContextMenu } from 'bits-ui';
	import { getFlash } from 'sveltekit-flash-message';
	import { m } from '$paraglide/messages';
	import { page } from '$app/stores';
	import { getModelInfo } from '$lib/utils/crud';

	const flash = getFlash(page);

	interface Props {
		row?: any;
		handler: DataHandler;
		URLModel?: urlModel;
	}
	let { row, handler, URLModel }: Props = $props();

	async function changeSelected() {
		if (!URLModel) {
			console.error(
				'The URLModel is undefined in the SelectObject component, which prevents the object selected/selected from the ContextMenu.'
			);
			return;
		}
		const endpoint = `/${URLModel}/${row?.meta?.id}/is_selected`;
		const requestInit = {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ is_selected: !row.is_selected })
		};
		console.log(row);
		const model = getModelInfo(URLModel);
		const objectTypeName = safeTranslate(model.localName);

		try {
			const response = await fetch(endpoint, requestInit);
			if (!response.ok) {
				throw new Error('Network response was not ok');
			}
			const data = await response.json();
			flash.set({
				type: 'success',
				message: m.successfullyUpdatedObject({ object: objectTypeName.toLowerCase() })
			});
			handler.invalidate();
		} catch (error) {
			flash.set({
				type: 'error',
				message: m.errorUpdatingObject({ object: objectTypeName.toLowerCase() })
			});
			console.error('Error changing status:', error);
		}
	}
</script>

{#if row}
	<ContextMenu.Item
		onclick={changeSelected}
		class="flex h-10 select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-surface-50"
	>
		<span class="flex items-center">{row.is_selected ? m.deselect() : m.select()}</span>
	</ContextMenu.Item>
{/if}
