<script lang="ts">
	import TierBadge from '$lib/components/ModelTable/field/TierBadge.svelte';
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	interface Props {
		row: { meta?: { id: string; tier?: { id: string } | null } } | undefined;
		handler: DataHandler;
	}

	let { row, handler }: Props = $props();

	const flash = getFlash(page);

	let tiers: { id: string; name: string; hexcolor?: string }[] = $state([]);
	const currentId = $derived(row?.meta?.tier?.id ?? null);

	onMount(async () => {
		const res = await fetch('/tiers?is_visible=true');
		if (!res.ok) return;
		const data = await res.json();
		tiers = Array.isArray(data) ? data : (data?.results ?? []);
	});

	async function changeTier(tierId: string | null) {
		try {
			const res = await fetch(`/entities/${row?.meta?.id}/tier`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ tier: tierId })
			});
			if (!res.ok) throw new Error(String(res.status));
			flash.set({
				type: 'success',
				message: m.successfullyUpdatedObject({ object: m.entity().toLowerCase() })
			});
			handler.invalidate();
		} catch (error) {
			flash.set({
				type: 'error',
				message: m.errorUpdatingObject({ object: m.entity().toLowerCase() })
			});
			console.error('Error changing tier:', error);
		}
	}
</script>

<ContextMenu.Sub>
	<ContextMenu.SubTrigger
		class="flex h-10 select-none items-center rounded-base py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-muted data-[state=open]:bg-surface-50"
	>
		<div class="flex items-center">{m.changeTier()}</div>
	</ContextMenu.SubTrigger>
	<ContextMenu.SubContent
		class="z-50 w-full min-w-[180px] max-w-[209px] outline-hidden card bg-surface-50-950 px-1 py-1.5 shadow-md border border-surface-200 cursor-default data-highlighted:bg-surface-50"
		sideOffset={10}
	>
		{#each tiers as tier (tier.id)}
			<ContextMenu.Item
				class="flex h-10 select-none items-center gap-2 rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! hover:bg-surface-50"
				disabled={tier.id === currentId}
				onclick={async () => await changeTier(tier.id)}
			>
				<TierBadge cell={tier} />
				{#if tier.id === currentId}<i class="fa-solid fa-check text-xs"></i>{/if}
			</ContextMenu.Item>
		{/each}
		{#if currentId}
			<ContextMenu.Separator class="-mx-1 my-1 block h-px bg-surface-100-900" />
			<ContextMenu.Item
				class="flex h-10 select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! hover:bg-surface-50"
				onclick={async () => await changeTier(null)}
			>
				{m.none()}
			</ContextMenu.Item>
		{/if}
	</ContextMenu.SubContent>
</ContextMenu.Sub>
