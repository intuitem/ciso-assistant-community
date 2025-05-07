<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	export let row: any;
	export let handler: DataHandler;

	const flash = getFlash(page);

	let options: { label: string; value: string }[] = [];

	onMount(async () => {
		options = await fetch('/applied-controls/status').then((r) => r.json());
	});

	async function changeStatus(newStatus: string) {
		const endpoint = `/applied-controls/${row?.meta?.id}/status`;
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
			console.log('Status changed successfully:', data);
			flash.set({
				type: 'success',
				message: m.successfullyUpdatedObject({ object: m.appliedControl().toLowerCase() })
			});
			handler.invalidate();
		} catch (error) {
			console.error('Error changing status:', error);
		}
	}
</script>

<ContextMenu.Sub>
	<ContextMenu.SubTrigger
		class="flex h-10 select-none items-center rounded-button py-3 pl-3 pr-1.5 text-sm font-medium outline-none !ring-0 !ring-transparent data-[highlighted]:bg-muted data-[state=open]:bg-surface-50"
	>
		<div class="flex items-center">{m.changeStatus()}</div>
	</ContextMenu.SubTrigger>
	<ContextMenu.SubContent
		class="z-50 w-full max-w-[209px] outline-none card bg-white px-1 py-1.5 shadow-md cursor-default data-[highlighted]:bg-surface-50"
		sideOffset={10}
	>
		{#each options as option}
			<ContextMenu.Item
				class="flex h-10 select-none items-center rounded-sm py-3 pl-3 pr-1.5 text-sm font-medium outline-none !ring-0 !ring-transparent hover:bg-surface-50"
				on:click={async () => await changeStatus(option.value)}
			>
				{safeTranslate(option.label)}
			</ContextMenu.Item>
		{/each}
	</ContextMenu.SubContent>
</ContextMenu.Sub>
