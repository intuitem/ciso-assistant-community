<script lang="ts">
	import { navData } from '#lib/components/SideBar/navData.js';

	import SideBarItem from '#lib/components/SideBar/SideBarItem.svelte';
	import SideBarCategory from '#lib/components/SideBar/SideBarCategory.svelte';
	import { Accordion } from '@skeletonlabs/skeleton-svelte';
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import { canSeeNavItem } from '#lib/components/SideBar/navVisibility.js';
	import { driverInstance } from '#lib/utils/stores.js';

	const user = page.data.user;

	const items = navData.items
		.map((item) => ({
			...item,
			// Shared with the command palette so the two cannot offer different sets of pages.
			items: item.items.filter((subItem) => canSeeNavItem(subItem, user))
		}))
		.filter((item) => item.items.length > 0); // Filter out items with no sub-items

	import { lastAccordionItem } from '#lib/utils/stores.js';
	interface Props {
		sideBarVisibleItems: Record<string, boolean>;
	}

	let { sideBarVisibleItems }: Props = $props();

	// Open the section holding the current page, e.g. after jumping there from the command palette.
	$effect(() => {
		const { pathname, searchParams } = page.url;
		let best: { section: string; length: number } | undefined;
		for (const item of items) {
			if (sideBarVisibleItems?.[item.name] === false) continue;
			for (const subItem of item.items) {
				if (!subItem.href || subItem.href === '/') continue;
				if (sideBarVisibleItems?.[subItem.name] === false) continue;
				const [href, query] = subItem.href.split('?');
				const pathMatches = pathname === href || pathname.startsWith(href + '/');
				const queryMatches = [...new URLSearchParams(query)].every(
					([k, v]) => searchParams.get(k) === v
				);
				if (pathMatches && queryMatches && subItem.href.length > (best?.length ?? 0)) {
					best = { section: item.name, length: subItem.href.length };
				}
			}
		}
		const section = best?.section;
		untrack(() => {
			if (section && !$lastAccordionItem.includes(section)) $lastAccordionItem = [section];
		});
	});

	function handleValueChange(details: { value: string[] }) {
		$lastAccordionItem = details.value;
		setTimeout(() => {
			$driverInstance?.moveNext();
		}, 0);
	}
</script>

<nav class="grow scrollbar">
	<Accordion
		value={$lastAccordionItem}
		onValueChange={handleValueChange}
		collapsible
		class="space-y-4"
	>
		{#each items as item}
			{#if sideBarVisibleItems && sideBarVisibleItems[item.name] !== false && item.items.some((subItem) => sideBarVisibleItems[subItem.name] !== false)}
				<Accordion.Item value={item.name} id={item.name.toLowerCase().replace(' ', '-')}>
					<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
						<SideBarCategory {item} />
						<Accordion.ItemIndicator
							class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90 text-primary-700-300"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="14px"
								height="14px"
								viewBox="0 0 448 512"
								fill="currentColor"
							>
								<path
									d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
								/>
							</svg>
						</Accordion.ItemIndicator>
					</Accordion.ItemTrigger>
					<Accordion.ItemContent class="space-y-2">
						<SideBarItem item={item.items} {sideBarVisibleItems} />
					</Accordion.ItemContent>
				</Accordion.Item>
			{/if}
		{/each}
	</Accordion>
</nav>
