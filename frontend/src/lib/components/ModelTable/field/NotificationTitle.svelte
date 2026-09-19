<script lang="ts">
	import { m } from '$paraglide/messages';

	/**
	 * Render a notification's title in the viewer's current language.
	 *
	 * Nothing about the title is stored: the row carries its `type` and the variables
	 * it needs, and the wording lives in the message catalogs like every other string
	 * in the product. That is what lets a language switch take effect on rows already
	 * written, and what gives the other 25 locales titles for free.
	 *
	 * This is a computed column: `cell` is empty because the API returns no title
	 * field at all. Everything comes from `meta`.
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
		// A type with no catalog entry yet: show the key rather than an empty cell, so
		// the gap is visible instead of looking like a row with nothing in it.
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
