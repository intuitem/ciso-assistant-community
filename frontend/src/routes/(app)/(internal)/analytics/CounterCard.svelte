<script lang="ts">
	import { goto } from '$lib/utils/breadcrumbs';

	interface Props {
		count?: number;
		label: string;
		faIcon?: string;
		iconColor?: string;
		href?: string | undefined;
		children?: import('svelte').Snippet;
	}

	let {
		count = 0,
		label,
		faIcon = '',
		iconColor = '',
		href = undefined,
		children
	}: Props = $props();

	const clickHandler = () => {
		if (href) {
			goto(href, { breadcrumbAction: 'push', label });
		}
	};

	let classesHover = $derived((href: string | undefined) =>
		href ? 'hover:preset-tonal-secondary' : ''
	);
</script>

<div
	class="card p-2 bg-inherit w-full flex flex-col whitespace-normal group {classesHover(
		href
	)} bg-linear-to-br from-white to-violet-50"
	onclick={clickHandler}
	role={href ? 'button' : ''}
>
	<div class="text-sm font-medium text-gray-500 group-hover:text-secondary-800-200">
		{label}
	</div>
	<div class="flex flex-row items-end h-full content-end">
		<span class="flex flex-row items-center">
			<div class="text-2xl {iconColor} mr-2"><i class={faIcon}></i></div>
			<div class="text-3xl font-semibold">{count}</div>
		</span>
		{@render children?.()}
	</div>
</div>
