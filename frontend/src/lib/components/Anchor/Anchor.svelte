<script lang="ts">
	import { breadcrumbs, goto, type Breadcrumb } from '$lib/utils/breadcrumbs';

	interface Props {
		href?: string;
		breadcrumbAction?: 'push' | 'replace';
		label?: string;
		prefixCrumbs?: Breadcrumb[];
		stopPropagation?: boolean;
		children?: import('svelte').Snippet;
		[key: string]: any;
	}

	let {
		href = '',
		breadcrumbAction = 'push',
		label = '',
		prefixCrumbs = [],
		stopPropagation = false,
		children,
		...rest
	}: Props = $props();

	const handleClick = (event) => {
		// Modified clicks (cmd/ctrl/shift/alt or non-primary button) open in a new tab/window:
		// let the browser handle them natively and keep parent handlers (e.g. table rows)
		// from also navigating the current tab.
		if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) {
			event.stopPropagation();
			return;
		}

		const navLabel: string = label || event.target.innerText;
		if (!navLabel) return;

		const crumb = { label: navLabel, href };
		const _crumbs = [...prefixCrumbs, crumb];
		breadcrumbs[breadcrumbAction](_crumbs);

		if (stopPropagation) {
			event.stopPropagation();
			event.preventDefault();
			goto(href, { breadcrumbAction });
		}
	};
</script>

<a aria-label={label || undefined} onclick={handleClick} {href} {...rest}>
	{@render children?.()}
</a>
