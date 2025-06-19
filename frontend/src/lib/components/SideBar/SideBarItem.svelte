<script lang="ts">
	import { page } from '$app/state';
	import { safeTranslate } from '$lib/utils/i18n';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	interface Props {
		item?: { name: string; href: string; fa_icon: string }[];
		sideBarVisibleItems: Record<string, boolean>;
	}

	let { item = [], sideBarVisibleItems }: Props = $props();

	let classesActive = $derived((href: string) =>
		href === page.url.pathname
			? 'bg-primary-100 text-primary-800'
			: 'hover:bg-primary-50 text-gray-800 '
	);
</script>

{#each item as item}
	<!-- undefined and true must be shown -->
	{#if sideBarVisibleItems[item.name] !== false}
		<Anchor
			href={item.href}
			breadcrumbAction="replace"
			class="unstyled flex whitespace-nowrap items-center py-2 text-sm font-normal rounded-base {classesActive(
				item.href ?? ''
			)}"
			data-testid={'accordion-item-' + item.href.substring(1)}
		>
			<span
				class="px-4 flex items-center w-full space-x-2 text-xs"
				id={item.name}
				title={safeTranslate(item.name)}
			>
				<i class="{item.fa_icon} w-1/12"></i>
				<span class="text-sm tracking-wide truncate">{safeTranslate(item.name)}</span>
			</span>
		</Anchor>
	{/if}
{/each}
