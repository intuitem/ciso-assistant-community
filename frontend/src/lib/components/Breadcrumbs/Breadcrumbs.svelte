<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { breadcrumbs, syncBreadcrumbsToCurrentUrl } from '$lib/utils/breadcrumbs';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import { pageTitle } from '$lib/utils/stores';

	function getPageTitle(): string {
		// Check each source in priority order
		const title =
			page.data.title ??
			page.data.str ??
			page.data.name ??
			getUrlModelTitle() ??
			getBreadcrumbTitle();
		return safeTranslate(title);
	}

	function getBreadcrumbTitle(): string | undefined {
		return $breadcrumbs.length > 1 ? $breadcrumbs[$breadcrumbs.length - 1]?.label : undefined;
	}

	function getUrlModelTitle(): string | undefined {
		const lastPathSegment = page.url.pathname.split('/').pop() as string;
		return URL_MODEL_MAP[lastPathSegment]?.localNamePlural;
	}

	function sync(fallbackLabel: string, isFreshLoad: boolean) {
		const currentPath = page.url.pathname;
		const currentUrl = currentPath + page.url.search;
		const current = $breadcrumbs;
		const next = syncBreadcrumbsToCurrentUrl(
			current,
			currentPath,
			currentUrl,
			fallbackLabel,
			isFreshLoad
		);
		// No-op if unchanged.
		if (
			next.length !== current.length ||
			next.some((c, i) => c.href !== current[i].href || c.label !== current[i].label)
		) {
			$breadcrumbs = next;
		}
	}

	afterNavigate((nav) => sync(getPageTitle(), nav.type === 'enter'));

	$effect(() => {
		$pageTitle = getPageTitle();
	});
</script>

<ol class="flex items-center gap-4 h-6 overflow-hidden whitespace-nowrap">
	{#each $breadcrumbs as c, i}
		{#if i == $breadcrumbs.length - 1}
			<span
				class="max-w-[64ch] overflow-hidden whitespace-nowrap text-ellipsis text-sm text-surface-600-400 font-semibold antialiased"
				data-testid="crumb-item"
				title={safeTranslate(c.label)}
			>
				{#if c.icon}
					<i class={c.icon}></i>
				{/if}
				{safeTranslate(c.label)}
			</span>
		{:else}
			<li>
				{#if c.href}
					<a
						class="max-w-[64ch] block overflow-hidden whitespace-nowrap text-ellipsis text-sm font-semibold antialiased hover:text-primary-500"
						data-testid="crumb-item"
						href={c.href}
						title={safeTranslate(c.label)}
						onclick={() => breadcrumbs.slice(i)}
					>
						{#if c.icon}
							<i class={c.icon}></i>
						{/if}
						{safeTranslate(c.label)}
					</a>
				{:else}
					<span
						class="max-w-[64ch] overflow-hidden whitespace-nowrap text-ellipsis text-sm text-surface-600-400 font-semibold antialiased"
						data-testid="crumb-item"
						title={safeTranslate(c.label)}
					>
						{#if c.icon}
							<i class={c.icon}></i>
						{/if}
						{safeTranslate(c.label)}
					</span>
				{/if}
			</li>
			<li class="crumb-separator" aria-hidden="true">›</li>
		{/if}
	{/each}
</ol>
