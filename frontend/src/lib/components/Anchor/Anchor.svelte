<script lang="ts">
	import { breadcrumbs, type Breadcrumb } from '$lib/utils/breadcrumbs';

	export let href = '';
	export let breadcrumbAction: 'push' | 'replace' = 'push';
	export let label = '';
	export const prefixCrumbs: Breadcrumb[] = [];

	const handleClick = (event) => {
		const navLabel: string = label || event.target.innerText;
		if (!navLabel) return;

		const crumb = { label: navLabel, href };
		const _crumbs = [...prefixCrumbs, crumb];
		breadcrumbs[breadcrumbAction](_crumbs);
	};
</script>

<a on:click={handleClick} {href} {...$$restProps}>
	<slot />
</a>
