<script lang="ts">
	import { goto } from '$app/navigation';

	export let count: string = '0';
	export let label: string;
	export let href: string | undefined = undefined;
	export let help: string;

	const clickHandler = () => {
		if (href) {
			goto(href);
		}
	};

	$: classesHover = (href: string | undefined) => (href ? 'hover:variant-soft-secondary' : '');
</script>

<div
	class="flex flex-col justify-center shadow-lg text-purple-800 p-2 h-32 hover:bg-violet-50 hover:border"
>
	<div class="text-3xl font-semibold text-left">{count}</div>
	<div class="text-normal font-normal text-left">{label}</div>
</div>

<style>
	@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');

	.custom-font {
		font-family: 'Inter', sans-serif;
		font-optical-sizing: auto;
		font-style: normal;
	}
</style>
