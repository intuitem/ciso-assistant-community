<script lang="ts">
	import { run } from 'svelte/legacy';

	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/stores';
	import { breadcrumbs, type Breadcrumb } from '$lib/utils/breadcrumbs';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import { pageTitle } from '$lib/utils/stores';

	async function trimBreadcrumbsToCurrentPath(
		breadcrumbs: Breadcrumb[],
		currentPath: string
	): Promise<Breadcrumb[]> {
		const idx = breadcrumbs.findIndex((c) => c.href?.startsWith(currentPath));
		// First breadcrumb is home, its href is always '/'
		if (idx > 0 && idx < breadcrumbs.length - 1) {
			breadcrumbs = breadcrumbs.slice(0, idx + 1);
		}
		return breadcrumbs;
	}

	function getPageTitle(): string {
		// Check each source in priority order
		const title =
			$page.data.title ??
			$page.data.str ??
			$page.data.name ??
			getBreadcrumbTitle() ??
			getUrlModelTitle();

		return safeTranslate(title);
	}

	function getBreadcrumbTitle(): string | undefined {
		return $breadcrumbs.length > 1 ? $breadcrumbs[$breadcrumbs.length - 1]?.label : undefined;
	}

	function getUrlModelTitle(): string | undefined {
		const lastPathSegment = $page.url.pathname.split('/').pop() as string;
		return URL_MODEL_MAP[lastPathSegment]?.localNamePlural;
	}

	afterNavigate(async () => {
		$breadcrumbs = await trimBreadcrumbsToCurrentPath($breadcrumbs, $page.url.pathname);
	});

	run(() => {
		$pageTitle = getPageTitle();
		if ($breadcrumbs.length < 2)
			breadcrumbs.push([{ label: $pageTitle, href: $page.url.pathname }]);
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
					<i class={c.icon}></i>
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
						onclick={() => breadcrumbs.slice(i)}
					>
						{#if c.icon}
							<i class={c.icon}></i>
						{/if}
						{safeTranslate(c.label)}
					</a>
				{:else}
					<span
						class="max-w-[64ch] overflow-hidden text-sm text-gray-500 font-semibold antialiased"
						data-testid="crumb-item"
					>
						{#if c.icon}
							<i class={c.icon}></i>
						{/if}
						{safeTranslate(c.label)}
					</span>
				{/if}
			</li>
			<li class="crumb-separator" aria-hidden>&rsaquo;</li>
		{/if}
	{/each}
</ol>
