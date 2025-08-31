<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	interface Props {
		row: {
			meta?: {
				id: string | number;
			};
			[key: string]: any;
		};
		handler: DataHandler;
	}

	let { row, handler }: Props = $props();

	const flash = getFlash(page);

	let options: { label: string; value: string }[] = $state([]);

	onMount(async () => {
		options = await fetch('/applied-controls/effort').then((r) => r.json());
	});

	async function changeEffort(newEffort: string) {
		const endpoint = `/applied-controls/${row?.meta?.id}/effort`;
		const requestInit = {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ effort: newEffort })
		};
		try {
			const response = await fetch(endpoint, requestInit);
			if (!response.ok) {
				throw new Error('Network response was not ok');
			}
			const data = await response.json();
			flash.set({
				type: 'success',
				message: m.successfullyUpdatedObject({ object: m.appliedControl().toLowerCase() })
			});
			handler.invalidate();
		} catch (error) {
			flash.set({
				type: 'error',
				message: m.errorUpdatingObject({ object: m.appliedControl().toLowerCase() })
			});
			console.error('Error changing effort:', error);
		}
	}
</script>

<ContextMenu.Sub>
	<ContextMenu.SubTrigger
		class="flex h-10 select-none items-center rounded-button py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-muted data-[state=open]:bg-surface-50"
	>
		<div class="flex items-center">{m.changeEffort()}</div>
	</ContextMenu.SubTrigger>
	<ContextMenu.SubContent
		class="z-50 w-full max-w-[209px] outline-hidden card bg-white px-1 py-1.5 shadow-md cursor-default data-highlighted:bg-surface-50"
		sideOffset={10}
	>
		{#each options as option}
			<ContextMenu.Item
				class="flex h-10 select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! hover:bg-surface-50"
				on:click={async () => await changeEffort(option.value)}
			>
				{safeTranslate(option.label)}
			</ContextMenu.Item>
		{/each}
	</ContextMenu.SubContent>
</ContextMenu.Sub>
