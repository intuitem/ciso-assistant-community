<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	interface Props {
		row: any;
		handler: DataHandler;
	}

	let { row, handler }: Props = $props();

	const flash = getFlash(page);

	let options: { label: string; value: string }[] = $state([]);

	onMount(async () => {
		options = await fetch('/task-nodes/status').then((r) => r.json());
	});

	async function changeStatus(newStatus: string) {
		const endpoint = `/task-nodes/${row?.meta?.id}/status`;
		const requestInit = {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ status: newStatus })
		};
		try {
			const response = await fetch(endpoint, requestInit);
			if (!response.ok) {
				throw new Error('Network response was not ok');
			}
			const data = await response.json();
			flash.set({
				type: 'success',
				message: m.successfullyUpdatedObject({ object: m.taskNode().toLowerCase() })
			});
			handler.invalidate();
		} catch (error) {
			flash.set({
				type: 'error',
				message: m.errorUpdatingObject({ object: m.taskNode().toLowerCase() })
			});
			console.error('Error changing status:', error);
		}
	}
</script>

<ContextMenu.Sub>
	<ContextMenu.SubTrigger
		class="flex h-10 select-none items-center rounded-button py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-muted data-[state=open]:bg-surface-50"
	>
		<div class="flex items-center">{m.changeStatus()}</div>
	</ContextMenu.SubTrigger>
	<ContextMenu.SubContent
		class="z-50 w-full min-w-[180px] max-w-[209px] outline-hidden card bg-surface-50-950 px-1 py-1.5 shadow-md border border-surface-200 cursor-default data-highlighted:bg-surface-50"
		sideOffset={10}
	>
		{#each options as option}
			<ContextMenu.Item
				class="flex h-10 select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! hover:bg-surface-50"
				onclick={async () => await changeStatus(option.value)}
			>
				{safeTranslate(option.label)}
			</ContextMenu.Item>
		{/each}
	</ContextMenu.SubContent>
</ContextMenu.Sub>
