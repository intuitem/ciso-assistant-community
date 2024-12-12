<script lang="ts">
	import { breadcrumbs } from '$lib/utils/breadcrumbs';

	export let href = '';
	export let breadcrumbAction: 'push' | 'replace' = 'replace';

	const handleClick = (event) => {
		const crumb = { label: event.target.innerText, href };
		breadcrumbs[breadcrumbAction](crumb);
	};
</script>

<a on:click={handleClick} {href} {...$$restProps}>
	<slot />
</a>
