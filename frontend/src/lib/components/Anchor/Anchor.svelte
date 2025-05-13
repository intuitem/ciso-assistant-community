<script lang="ts">
	import { breadcrumbs, goto, type Breadcrumb } from '$lib/utils/breadcrumbs';

	interface Props {
		href?: string;
		breadcrumbAction?: 'push' | 'replace';
		label?: string;
		prefixCrumbs?: Breadcrumb[];
		stopPropagation?: boolean;
		children?: import('svelte').Snippet;
		[key: string]: any
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

<a onclick={handleClick} {href} {...rest}>
	{@render children?.()}
</a>
