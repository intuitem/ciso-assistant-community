<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { ContextMenu } from 'bits-ui';
	import { invalidateAll } from '$app/navigation';
	import { m } from '$paraglide/messages';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	interface Props {
		row: any;
		handler: DataHandler;
	}

	let { row, handler }: Props = $props();

	const flash = getFlash(page);

	const flags = [
		{ field: 'recovery_documented', label: m.recoveryDocumented },
		{ field: 'recovery_tested', label: m.recoveryTested },
		{ field: 'recovery_targets_met', label: m.recoveryTargetsMet }
	] as const;

	const locked = $derived(Boolean(row?.meta?.bia?.is_locked));

	async function toggle(field: string) {
		if (!row?.meta?.id) return;
		try {
			const response = await fetch(`/asset-assessments/${row?.meta?.id}/${field}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ [field]: !row?.meta?.[field] })
			});
			if (!response.ok) {
				throw new Error('Network response was not ok');
			}
			flash.set({
				type: 'success',
				message: m.successfullyUpdatedObject({ object: m.assetAssessment().toLowerCase() })
			});
			handler.invalidate();
			await invalidateAll();
		} catch (error) {
			console.error('Error toggling recovery flag:', error);
			flash.set({ type: 'error', message: m.anErrorOccurred() });
		}
	}
</script>

{#each flags as flag}
	<ContextMenu.Item
		class="flex h-10 select-none items-center rounded-base py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-muted hover:bg-surface-50-950 data-disabled:opacity-50"
		disabled={locked}
		onclick={async () => await toggle(flag.field)}
	>
		<i class="fa-regular {row?.meta?.[flag.field] ? 'fa-square-check' : 'fa-square'} mr-2 w-4"></i>
		{flag.label()}
	</ContextMenu.Item>
{/each}
