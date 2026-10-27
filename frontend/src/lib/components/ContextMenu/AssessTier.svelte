<script lang="ts">
	import { gotoOrLoad } from '#lib/utils/breadcrumbs.js';
	import { page } from '$app/state';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';
	import { ContextMenu } from 'bits-ui';
	import { onMount } from 'svelte';
	import { getFlash } from 'sveltekit-flash-message';

	interface Props {
		row: { meta?: { id: string; builtin?: boolean } } | undefined;
		URLModel: 'entities' | 'solutions';
	}

	let { row, URLModel }: Props = $props();

	const flash = getFlash(page);

	// Forms the viewer may fill in-house, else publications they may file,
	// that set this object's tier.
	type Option = { kind: 'form' | 'publication'; id: string; name: string };
	let options: Option[] = $state([]);

	onMount(async () => {
		if (!row?.meta?.id || row.meta.builtin) return;
		try {
			const res = await fetch(`/${URLModel}/${row.meta.id}/assess-tier`);
			const rows = res.ok ? await res.json() : [];
			options = Array.isArray(rows) ? rows : [];
		} catch {
			options = [];
		}
	});

	// One start at a time: repeated clicks must not open several drafts.
	let starting = $state(false);

	async function assess(option: Option) {
		if (starting) return;
		starting = true;
		try {
			const res = await fetch(`/${URLModel}/${row?.meta?.id}/assess-tier`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ kind: option.kind, id: option.id })
			});
			const body = await res.json().catch(() => ({}));
			if (!res.ok || !body.redirect) {
				flash.set({
					type: 'error',
					message: body.error ? safeTranslate(body.error) : m.anErrorOccurred()
				});
				return;
			}
			await gotoOrLoad(body.redirect);
		} catch {
			flash.set({ type: 'error', message: m.anErrorOccurred() });
		} finally {
			starting = false;
		}
	}

	const itemClass =
		'flex h-10 select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! hover:bg-surface-50';
</script>

{#if options.length === 1}
	<ContextMenu.Item class={itemClass} disabled={starting} onclick={() => assess(options[0])}>
		{m.assessTier()}
	</ContextMenu.Item>
{:else if options.length > 1}
	<ContextMenu.Sub>
		<ContextMenu.SubTrigger
			class="flex h-10 select-none items-center rounded-base py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-muted data-[state=open]:bg-surface-50"
		>
			<div class="flex items-center">{m.assessTier()}</div>
		</ContextMenu.SubTrigger>
		<ContextMenu.SubContent
			class="z-50 w-full min-w-[180px] max-w-[260px] outline-hidden card bg-surface-50-950 px-1 py-1.5 shadow-md border border-surface-200 cursor-default data-highlighted:bg-surface-50"
			sideOffset={10}
		>
			{#each options as option (option.id)}
				<ContextMenu.Item class={itemClass} disabled={starting} onclick={() => assess(option)}>
					{option.name}
				</ContextMenu.Item>
			{/each}
		</ContextMenu.SubContent>
	</ContextMenu.Sub>
{/if}
