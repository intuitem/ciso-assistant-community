<script lang="ts">
	import { breadcrumbs, goto, type Breadcrumb } from '$lib/utils/breadcrumbs';

	export let href = '';
	export let breadcrumbAction: 'push' | 'replace' = 'push';
	export let label = '';
	export let prefixCrumbs: Breadcrumb[] = [];
	export let stopPropagation: boolean = false;

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

<a on:click={handleClick} {href} {...$$restProps}>
	<slot />
</a>
