<script lang="ts">
	interface Props {
		open: boolean;
	}

	let { open = $bindable() }: Props = $props();

	function toggle() {
		open = !open;
	}

	let classesSidebarOpenButton = $derived((open: boolean) => (open ? 'left-[15.3rem]' : 'rotate-180 left-5'));
</script>

<!-- SIDEBAR TOGGLE -->
<button
	onclick={toggle}
	class="{classesSidebarOpenButton(
		open
	)} z-20 fixed w-6 h-6 rounded-full content-center self-center bg-white shadow border text-gray-600 hover:scale-105 hover:bg-primary-700 hover:text-white transition-all duration-300 top-1/2 bottom-1/2"
	data-testid="sidebar-toggle-btn"
>
	<i class="fa-solid fa-angle-left"></i>
</button>
