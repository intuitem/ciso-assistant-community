<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { m } from '$paraglide/messages';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	interface Props {
		row: any;
		handler: DataHandler;
	}

	let { row, handler }: Props = $props();

	const flash = getFlash(page);
	const isActive = $derived(row?.meta?.is_active !== false);

	async function toggleActive() {
		const endpoint = `/workflows/${row?.meta?.id}/ops?action=set-active`;
		try {
			const response = await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ is_active: !isActive })
			});
			if (!response.ok) throw new Error('Network response was not ok');
			flash.set({
				type: 'success',
				message: m.successfullyUpdatedObject({ object: m.workflow().toLowerCase() })
			});
			handler.invalidate();
		} catch (error) {
			flash.set({ type: 'error', message: `Error updating workflow: ${String(error)}` });
		}
	}
</script>

<ContextMenu.Item
	class="flex h-10 select-none items-center rounded-button py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-muted cursor-pointer"
	onclick={toggleActive}
>
	<div class="flex items-center">
		<i class="fa-solid {isActive ? 'fa-pause' : 'fa-play'} mr-2 text-surface-500"></i>
		{isActive ? m.disableWorkflow() : m.enableWorkflow()}
	</div>
</ContextMenu.Item>
