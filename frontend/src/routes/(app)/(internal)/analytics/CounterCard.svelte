<script lang="ts">
	import { goto } from '#lib/utils/breadcrumbs.js';
	import AnimatedNumber from '#lib/components/utils/AnimatedNumber.svelte';

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

	// Keep the breadcrumb trail the plain link would skip.
	const onclick = (e: MouseEvent) => {
		if (!href || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
		e.preventDefault();
		goto(href, { breadcrumbAction: 'push', label });
	};
</script>

<svelte:element
	this={href ? 'a' : 'div'}
	{href}
	onclick={href ? onclick : undefined}
	class="w-full flex flex-col justify-between gap-3 rounded-lg border border-surface-200-800 bg-surface-50-950 p-4 transition-colors
		{href
		? 'hover:bg-surface-100-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500'
		: ''}"
>
	<span class="flex items-start gap-2 text-[13px] leading-snug text-surface-600-400">
		{#if faIcon}
			<i class="{faIcon} {iconColor || 'text-primary-500'} mt-0.5 text-sm" aria-hidden="true"></i>
		{/if}
		{label}
	</span>
	<span class="flex items-end justify-between">
		<span
			class="text-[1.75rem] leading-none font-semibold tabular-nums tracking-tight text-surface-950-50"
			data-testid="card-{label}"><AnimatedNumber value={count ?? 0} countUp /></span
		>
		{@render children?.()}
	</span>
</svelte:element>
