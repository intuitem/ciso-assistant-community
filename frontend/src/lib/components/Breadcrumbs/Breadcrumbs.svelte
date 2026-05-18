<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { breadcrumbs, type Breadcrumb } from '$lib/utils/breadcrumbs';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import { pageTitle } from '$lib/utils/stores';

	function hrefPathname(href: string | undefined): string | undefined {
		if (!href) return undefined;
		const queryIdx = href.indexOf('?');
		return queryIdx === -1 ? href : href.slice(0, queryIdx);
	}

	// Same depth + same first segment.
	function isSiblingPath(a: string | undefined, b: string): boolean {
		if (!a) return false;
		const aSegs = a.split('/').filter(Boolean);
		const bSegs = b.split('/').filter(Boolean);
		if (aSegs.length === 0 || aSegs.length !== bSegs.length) return false;
		return aSegs[0] === bSegs[0];
	}

	function syncBreadcrumbsToCurrentUrl(
		breadcrumbs: Breadcrumb[],
		currentPath: string,
		currentUrl: string,
		fallbackLabel: string,
		isFreshLoad: boolean
	): Breadcrumb[] {
		const idx = breadcrumbs.findIndex((c, i) => i > 0 && hrefPathname(c.href) === currentPath);
		if (idx > 0) {
			const trimmed = breadcrumbs.slice(0, idx + 1);
			const matched = trimmed[idx];
			trimmed[idx] = { ...matched, href: currentUrl };
			return trimmed;
		}
		// Fresh load with no match: reset trail.
		if (isFreshLoad) {
			return [breadcrumbs[0], { label: fallbackLabel, href: currentUrl }];
		}
		// Replace last crumb on sibling nav.
		const last = breadcrumbs[breadcrumbs.length - 1];
		if (breadcrumbs.length > 1 && isSiblingPath(hrefPathname(last?.href), currentPath)) {
			const replaced = breadcrumbs.slice();
			replaced[replaced.length - 1] = { label: fallbackLabel, href: currentUrl };
			return replaced;
		}
		return [...breadcrumbs, { label: fallbackLabel, href: currentUrl }];
	}

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
				class="max-w-[64ch] overflow-hidden whitespace-nowrap text-ellipsis text-sm text-gray-500 font-semibold antialiased"
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
						class="max-w-[64ch] overflow-hidden whitespace-nowrap text-ellipsis text-sm text-gray-500 font-semibold antialiased"
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
