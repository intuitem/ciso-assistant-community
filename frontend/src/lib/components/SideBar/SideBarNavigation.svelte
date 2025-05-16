<script lang="ts">
	import { navData } from '$lib/components/SideBar/navData';

	import SideBarItem from '$lib/components/SideBar/SideBarItem.svelte';
	import SideBarCategory from '$lib/components/SideBar/SideBarCategory.svelte';
	import { Accordion } from '@skeletonlabs/skeleton-svelte';
	import { page } from '$app/state';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { driverInstance } from '$lib/utils/stores';

	const user = page.data.user;

	const items = navData.items
		.map((item) => {
			// Check and filter the sub-items based on user permissions
			const filteredSubItems = item.items.filter((subItem) => {
				if (subItem.exclude) {
					return subItem.exclude.some((role) => user?.roles && !user.roles.includes(role));
				} else if (subItem.permissions) {
					return subItem.permissions?.some(
						(permission) => user?.permissions && Object.hasOwn(user.permissions, permission)
					);
				} else if (Object.hasOwn(URL_MODEL_MAP, subItem.href.split('/')[1])) {
					const model = URL_MODEL_MAP[subItem.href.split('/')[1]];
					const canViewObject =
						user?.permissions && Object.hasOwn(user.permissions, `view_${model.name}`);
					return canViewObject;
				}
				return false;
			});

			return {
				...item,
				items: filteredSubItems
			};
		})
		.filter((item) => item.items.length > 0); // Filter out items with no sub-items

	import { lastAccordionItem } from '$lib/utils/stores';
	interface Props {
		sideBarVisibleItems: Record<string, boolean>;
	}

	let { sideBarVisibleItems }: Props = $props();

	function lastAccordionItemOpened(value: string) {
		lastAccordionItem.set(value);
	}

	function handleNavClick(item: any) {
		lastAccordionItemOpened(item.name);
		setTimeout(() => {
			$driverInstance?.moveNext();
		}, 0);
	}
</script>

<nav class="grow scrollbar">
	<Accordion
		spacing="space-y-4"
		regionPanel="space-y-2"
		caretClosed="-rotate-90"
		caretOpen=""
		value={$lastAccordionItem}
		onValueChange={(e) => ($lastAccordionItem = e.value)}
	>
		{#each items as item}
			{#if sideBarVisibleItems && sideBarVisibleItems[item.name] !== false}
				<Accordion.Item
					id={item.name.toLowerCase().replace(' ', '-')}
					onClick={() => handleNavClick(item)}
					value={item.name}
				>
					{#snippet control()}
						<SideBarCategory {item} />
					{/snippet}
					{#snippet panel()}
						<SideBarItem item={item.items} {sideBarVisibleItems} />
					{/snippet}
				</Accordion.Item>
			{/if}
		{/each}
	</Accordion>
</nav>
