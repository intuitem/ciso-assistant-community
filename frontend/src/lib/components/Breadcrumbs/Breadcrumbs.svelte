<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/stores';
	import { breadcrumbs, type Breadcrumb } from '$lib/utils/breadcrumbs';
	import { safeTranslate } from '$lib/utils/i18n';

	async function trimBreadcrumbsToCurrentPath(
		breadcrumbs: Breadcrumb[],
		currentPath: string
	): Promise<Breadcrumb[]> {
		const idx = breadcrumbs.findIndex((c) => c.href === currentPath);
		if (idx >= 0 && idx < breadcrumbs.length - 1) {
			breadcrumbs = breadcrumbs.slice(0, idx + 1);
		}
		return breadcrumbs;
	}

	afterNavigate(async () => {
		$breadcrumbs = await trimBreadcrumbsToCurrentPath($breadcrumbs, $page.url.pathname);
	});
</script>

<ol class="breadcrumb-nonresponsive h-6 overflow-hidden whitespace-nowrap">
	{#each $breadcrumbs as c, i}
		{#if i == $breadcrumbs.length - 1}
			<span
				class="max-w-[64ch] overflow-hidden text-sm text-gray-500 font-semibold antialiased"
				data-testid="crumb-item"
			>
				{#if c.icon}
					<i class={c.icon} />
				{/if}
				{safeTranslate(c.label)}
			</span>
		{:else}
			<li class="crumb">
				{#if c.href}
					<a
						class="max-w-[64ch] overflow-hidden unstyled text-sm hover:text-primary-500 font-semibold antialiased whitespace-nowrap"
						data-testid="crumb-item"
						href={c.href}
						on:click={() => breadcrumbs.slice(i)}
					>
						{#if c.icon}
							<i class={c.icon} />
						{/if}
						{safeTranslate(c.label)}
					</a>
				{:else}
					<span
						class="max-w-[64ch] overflow-hidden text-sm text-gray-500 font-semibold antialiased"
						data-testid="crumb-item"
					>
						{#if c.icon}
							<i class={c.icon} />
						{/if}
						{safeTranslate(c.label)}
					</span>
				{/if}
			</li>
			<li class="crumb-separator" aria-hidden>&rsaquo;</li>
		{/if}
	{/each}
</ol>
