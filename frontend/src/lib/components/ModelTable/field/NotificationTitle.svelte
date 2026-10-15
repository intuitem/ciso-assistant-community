<script lang="ts">
	import { m } from '$paraglide/messages';

	/**
	 * Title rendered from `type` + `context` against the message catalogs, so it
	 * follows the viewer's language rather than the one it fired in.
	 *
	 * A computed column: the API returns no title field, so `cell` is empty and
	 * everything comes from `meta`.
	 *
	 * The audience badge rides along here rather than taking a column of its own: it
	 * is blank for the common case of one recipient, and a column that is usually
	 * empty is worse than no column.
	 */
	interface Props {
		cell: any;
		meta?: any;
	}

	let { cell, meta }: Props = $props();

	const messageKey = $derived(
		meta?.type
			? 'notificationTitle' +
					String(meta.type)
						.split('_')
						.map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
						.join('')
			: undefined
	);

	const title = $derived.by(() => {
		const message = messageKey ? (m as Record<string, any>)[messageKey] : undefined;
		// No catalog entry yet: show the key, so the gap is visible.
		if (typeof message !== 'function') return meta?.type ?? '';
		try {
			return message(meta?.context ?? {});
		} catch (error) {
			console.error(`Could not render ${messageKey}:`, error);
			return meta?.type ?? '';
		}
	});

	const others = $derived(Math.max(0, Number(meta?.recipient_count ?? 1) - 1));
</script>

<span class="inline-flex items-center gap-2">
	<span>{title}</span>
	{#if others > 0}
		<span
			class="inline-flex items-center gap-1 rounded-full bg-surface-200-800 px-2 py-0.5 text-[10px] text-surface-700-300"
			title={m.alsoNotified({ count: others })}
		>
			<i class="fa-solid fa-user-group"></i>{others + 1}
		</span>
	{/if}
</span>
