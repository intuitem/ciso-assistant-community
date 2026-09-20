<script lang="ts">
	import { m } from '$paraglide/messages';

	/**
	 * Title rendered from `type` + `context` against the message catalogs, so it
	 * follows the viewer's language rather than the one it fired in.
	 *
	 * A computed column: the API returns no title field, so `cell` is empty and
	 * everything comes from `meta`.
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
</script>

<span>{title}</span>
