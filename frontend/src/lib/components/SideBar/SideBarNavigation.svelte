<script lang="ts">
	import { navData } from '$lib/components/SideBar/navData';

	import SideBarItem from '$lib/components/SideBar/SideBarItem.svelte';
	import SideBarCategory from '$lib/components/SideBar/SideBarCategory.svelte';
	import { Accordion, AccordionItem } from '@skeletonlabs/skeleton';
	import { page } from '$app/stores';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { driverInstance } from '$lib/utils/stores';

	const user = $page.data.user;

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

	function lastAccordionItemOpened(value: string) {
		lastAccordionItem.set(value);
	}

	function handleNavClick() {
		setTimeout(() => {
			$driverInstance?.moveNext();
		}, 0);
	}
</script>

<nav class="flex-grow scrollbar">
	<Accordion
		autocollapse
		spacing="space-y-4"
		regionPanel="space-y-2"
		caretClosed="-rotate-90"
		caretOpen=""
	>
		{#each items as item}
			<!-- This commented code adds Accordion persistency but changes its visual behavior -->
			<!-- {#if $lastAccordionItem === item.name}
				<AccordionItem id={item.name} on:click={() => lastAccordionItemOpened(item.name)}  open>
					<svelte:fragment slot="summary"><SideBarCategory {item} /></svelte:fragment>
					<svelte:fragment slot="content"><SideBarItem item={item.items} /></svelte:fragment>
				</AccordionItem>
			{:else} -->
			<AccordionItem
				id={item.name.toLowerCase().replace(' ', '-')}
				on:click={() => lastAccordionItemOpened(item.name)}
				on:click={handleNavClick}
				open={$lastAccordionItem === item.name}
			>
				<svelte:fragment slot="summary"><SideBarCategory {item} /></svelte:fragment>
				<svelte:fragment slot="content"><SideBarItem item={item.items} /></svelte:fragment>
			</AccordionItem>
			<!-- {/if} -->
		{/each}
	</Accordion>
</nav>
