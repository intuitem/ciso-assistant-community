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
		spaceY="space-y-4"
		regionPanel="space-y-2"
		caretClosed="-rotate-90"
		caretOpen=""
		value={$lastAccordionItem}
		onValueChange={(e) => ($lastAccordionItem = e.value)}
		collapsible
	>
		{#snippet iconOpen()}
			<svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512">
				<path
					d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
				/>
			</svg>
		{/snippet}
		{#snippet iconClosed()}
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="-rotate-90"
				width="14px"
				height="14px"
				viewBox="0 0 448 512"
			>
				<path
					d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
				/>
			</svg>
		{/snippet}
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
