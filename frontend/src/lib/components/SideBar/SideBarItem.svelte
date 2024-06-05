<script lang="ts">
	import { page } from '$app/stores';
	import type { ModalSettings } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import { localItems } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';
	import * as m from '$paraglide/messages';

	export let item: any; // TODO: type this

	const modalStore = getModalStore();

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
			<span class="text-sm tracking-wide truncate">{localItems()[item.name]}</span>
		</span></a
	>
{/each}
