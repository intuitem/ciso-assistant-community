<script lang="ts">
	import { breadcrumbs, type Breadcrumb } from '$lib/utils/breadcrumbs';

	export let href = '';
	export let breadcrumbAction: 'push' | 'replace' = 'replace';
	export const prefixCrumbs: Breadcrumb[] = [];

	const handleClick = (event) => {
		const crumb = { label: event.target.innerText, href };
		const _crumbs = [...prefixCrumbs, crumb];
		breadcrumbs[breadcrumbAction](_crumbs);
	};
</script>

<a on:click={handleClick} {href} {...$$restProps}>
	<slot />
</a>
