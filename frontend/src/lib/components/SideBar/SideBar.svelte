<script lang="ts" type="module">
	import SideBarFooter from './SideBarFooter.svelte';
	import SideBarHeader from './SideBarHeader.svelte';
	import SideBarNavigation from './SideBarNavigation.svelte';
	import SideBarToggle from './SideBarToggle.svelte';

	export let open: boolean;

	$: classesSidebarOpen = (open: boolean) => (open ? '' : '-ml-[14rem]');
</script>

<aside
	class="flex w-64 shadow transition-all duration-300 fixed h-screen overflow-visible top-0 left-0 z-20 {classesSidebarOpen(
		open
	)}"
>
	<nav class="flex-1 flex flex-col overflow-y-auto overflow-x-hidden bg-gray-50 py-4 px-3">
		<SideBarHeader />
		<SideBarNavigation />
		<SideBarFooter />
	</nav>
</aside>

<SideBarToggle bind:open />
