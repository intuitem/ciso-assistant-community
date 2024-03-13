<script lang="ts">
	import { goto } from '$app/navigation';

	export let count = 0;
	export let label: string;
	export let faIcon = '';
	export let iconColor = '';
	export let href: string | undefined = undefined;

	const clickHandler = () => {
		if (href) {
			goto(href);
		}
	};

	$: classesHover = (href: string | undefined) => (href ? 'hover:variant-soft-secondary' : '');
</script>

<div
	class="card p-2 bg-inherit w-full flex flex-col whitespace-normal group {classesHover(href)}"
	on:click={clickHandler}
	role={href ? 'button' : ''}
>
	<div class="text-sm font-medium text-gray-500 group-hover:text-secondary-700-200-token">
		{label}
	</div>
	<div class="flex flex-row items-end h-full content-end">
		<span class="flex flex-row items-center">
			<div class="text-2xl {iconColor} mr-2"><i class={faIcon} /></div>
			<div class="text-3xl font-semibold">{count}</div>
		</span>
		<slot />
	</div>
</div>
