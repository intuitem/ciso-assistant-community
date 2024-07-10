<script lang="ts">
	import { page } from '$app/stores';
	import * as m from '$paraglide/messages';

	export let item: any; // TODO: type this

	$: classesActive = (href: string) =>
		href === $page.url.pathname
			? 'bg-primary-100 text-primary-800'
			: 'hover:bg-primary-50 text-gray-800 ';
</script>

{#each item as item}
	<a
		href={item.href}
		class="unstyled flex whitespace-nowrap items-center py-2 text-sm font-normal rounded-token {classesActive(
			item.href ?? ''
		)}"
		data-testid={'accordion-item-' + item.href.substring(1)}
	>
		<span class="px-4 flex items-center w-full space-x-2 text-xs">
			<i class="{item.fa_icon} w-1/12" />
			<span class="text-sm tracking-wide truncate">{m[item.name]() ?? item.name}</span>
		</span></a
	>
{/each}
