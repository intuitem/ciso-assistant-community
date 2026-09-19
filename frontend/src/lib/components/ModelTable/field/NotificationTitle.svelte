<script lang="ts">
	import { m } from '$paraglide/messages';

	/**
	 * Render a notification's title in the *viewer's* current language.
	 *
	 * The row stores a title rendered once, in whatever language the recipient
	 * preferred when it was written — so switching language left old rows stranded,
	 * and the 25 locales with no backend title file were stranded permanently. The
	 * row also carries the variables it was rendered from, so the title can be
	 * rebuilt here from the normal message catalogs instead.
	 *
	 * The stored title remains the fallback: an unknown type, or a locale whose
	 * catalog has not been filled yet, still shows something rather than nothing.
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
		const context = meta?.context;
		// Rows written before the context was stored have none. Re-rendering those
		// would print the parameter names verbatim, which is worse than a title in
		// the wrong language.
		if (typeof message !== 'function' || !context || Object.keys(context).length === 0) {
			return cell;
		}
		try {
			const rendered = message(context);
			// A message whose parameters do not match the stored context leaves them
			// unsubstituted; the frozen title is at least complete.
			return /\{[a-z_]+\}/.test(rendered) ? cell : rendered;
		} catch (error) {
			console.error(`Could not render ${messageKey}:`, error);
			return cell;
		}
	});
</script>

<span>{title}</span>
