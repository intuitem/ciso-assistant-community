<script lang="ts">
	import DpiaRequiredBadge from '$lib/components/ModelTable/field/DpiaRequiredBadge.svelte';
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { m } from '$paraglide/messages';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	interface Props {
		row: { meta?: { id: string; dpia_required?: boolean; role?: string } } | undefined;
		handler: DataHandler;
	}

	let { row, handler }: Props = $props();

	const flash = getFlash(page);

	const current = $derived(row?.meta?.dpia_required);

	async function change(value: boolean) {
		try {
			const res = await fetch(`/processings/${row?.meta?.id}/dpia_required`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ dpia_required: value })
			});
			if (!res.ok) throw new Error(String(res.status));
			flash.set({
				type: 'success',
				message: m.successfullyUpdatedObject({ object: m.processing().toLowerCase() })
			});
			handler.invalidate();
		} catch (error) {
			flash.set({
				type: 'error',
				message: m.errorUpdatingObject({ object: m.processing().toLowerCase() })
			});
			console.error('Error changing DPIA requirement:', error);
		}
	}

	const itemClass =
		'flex h-10 select-none items-center gap-2 rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! hover:bg-surface-50';
</script>

<!-- A processor's DPIA is the controller's: nothing to set. -->
{#if row?.meta?.role !== 'privacy_data_processor'}
	<ContextMenu.Sub>
		<ContextMenu.SubTrigger
			class="flex h-10 select-none items-center rounded-base py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-muted data-[state=open]:bg-surface-50"
		>
			<div class="flex items-center">{m.setDpiaRequirementManually()}</div>
		</ContextMenu.SubTrigger>
		<ContextMenu.SubContent
			class="z-50 w-full min-w-[180px] max-w-[220px] outline-hidden card bg-surface-50-950 px-1 py-1.5 shadow-md border border-surface-200 cursor-default data-highlighted:bg-surface-50"
			sideOffset={10}
		>
			{#each [true, false] as value (value)}
				<ContextMenu.Item
					class={itemClass}
					disabled={value === current}
					onclick={async () => await change(value)}
				>
					<DpiaRequiredBadge cell={value} />
					{#if value === current}<i class="fa-solid fa-check text-xs"></i>{/if}
				</ContextMenu.Item>
			{/each}
		</ContextMenu.SubContent>
	</ContextMenu.Sub>
{/if}
