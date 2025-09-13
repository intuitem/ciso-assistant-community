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
</script>

<div
	class="card p-4 w-full flex flex-col whitespace-normal group transition-all duration-200 ease-in-out
		   bg-gradient-to-br from-white via-white to-violet-25
		   border border-gray-100 shadow-sm hover:shadow-lg hover:border-violet-200
		   {href ? 'cursor-pointer hover:scale-[1.02] hover:-translate-y-1' : ''}"
	onclick={clickHandler}
	role={href ? 'button' : ''}
>
	<div class="text-xs font-medium text-gray-600 uppercase tracking-wide mb-3 group-hover:text-violet-700 transition-colors duration-200">
		{label}
	</div>
	<div class="flex flex-row items-center justify-between">
		<div class="flex flex-row items-center">
			{#if faIcon}
				<div class="text-3xl {iconColor || 'text-violet-500'} mr-3 group-hover:scale-110 transition-transform duration-200">
					<i class={faIcon}></i>
				</div>
			{/if}
			<div class="text-4xl font-bold text-gray-800 group-hover:text-violet-800 transition-colors duration-200" data-testid="card-{label}">
				{count?.toLocaleString()}
			</div>
		</div>
		{@render children?.()}
	</div>
</div>
