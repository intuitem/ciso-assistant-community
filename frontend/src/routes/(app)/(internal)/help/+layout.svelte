<script lang="ts">
	import { page } from '$app/state';
	import type { HelpNavItem } from '$lib/utils/helpNav';

	interface Props {
		data: { navTree: HelpNavItem[] };
		children?: import('svelte').Snippet;
	}

	let { data, children }: Props = $props();

	function currentSlug(): string {
		return page.params.slug ?? '';
	}
</script>

{#snippet navItem(item: HelpNavItem, depth: number)}
	<li>
		{#if item.slug !== null}
			<a
				href="/help/{item.slug}"
				class="block rounded px-2 py-1 text-sm hover:bg-surface-200-800 {currentSlug() ===
				item.slug
					? 'bg-surface-200-800 font-medium text-primary-700-300'
					: 'text-surface-800-200'}"
				style="padding-left: {0.5 + depth * 0.75}rem"
			>
				{item.title}
			</a>
		{:else}
			<span
				class="block px-2 pt-3 pb-1 text-xs font-semibold tracking-wide text-surface-500-400 uppercase"
				style="padding-left: {0.5 + depth * 0.75}rem"
			>
				{item.title}
			</span>
		{/if}
		{#if item.children.length}
			<ul>
				{#each item.children as child (child.slug ?? child.title)}
					{@render navItem(child, depth + 1)}
				{/each}
			</ul>
		{/if}
	</li>
{/snippet}

<div class="flex h-full min-h-0 gap-6">
	<nav class="w-64 shrink-0 overflow-y-auto border-r pr-3" aria-label="Help navigation">
		<ul>
			{#each data.navTree as item (item.slug ?? item.title)}
				{@render navItem(item, 0)}
			{/each}
		</ul>
	</nav>
	<div class="min-w-0 flex-1 overflow-y-auto pb-8">
		{@render children?.()}
	</div>
</div>
