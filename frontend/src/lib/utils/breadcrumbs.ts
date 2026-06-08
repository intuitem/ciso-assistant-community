import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { goto as _goto } from '$app/navigation';
import { m } from '$paraglide/messages';

const STORAGE_KEY = 'ciso:breadcrumbs';

export interface Breadcrumb {
	label: string;
	href?: string;
	icon?: string;
}

const BREADCRUMBS_MAX_DEPTH = 5;

const homeCrumb: Breadcrumb = {
	get label() {
		return m.home();
	},
	href: '/',
	icon: 'fa-regular fa-compass'
};

export function hrefPathname(href: string | undefined): string | undefined {
	if (!href) return undefined;
	const queryIdx = href.indexOf('?');
	return queryIdx === -1 ? href : href.slice(0, queryIdx);
}

// Same depth + same first segment.
export function isSiblingPath(a: string | undefined, b: string): boolean {
	if (!a) return false;
	const aSegs = a.split('/').filter(Boolean);
	const bSegs = b.split('/').filter(Boolean);
	if (aSegs.length === 0 || aSegs.length !== bSegs.length) return false;
	return aSegs[0] === bSegs[0];
}

export function syncBreadcrumbsToCurrentUrl(
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

function isValidCrumb(value: unknown): value is Breadcrumb {
	if (!value || typeof value !== 'object') return false;
	const c = value as Record<string, unknown>;
	if (typeof c.label !== 'string') return false;
	if (c.href !== undefined && typeof c.href !== 'string') return false;
	if (c.icon !== undefined && typeof c.icon !== 'string') return false;
	return true;
}

export function loadFromSession(initialValue: Breadcrumb[]): Breadcrumb[] {
	if (!browser) return initialValue;
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return initialValue;
		const parsed = JSON.parse(raw);
		if (!Array.isArray(parsed)) return initialValue;
		const tail = parsed.slice(1).filter(isValidCrumb).slice(0, BREADCRUMBS_MAX_DEPTH);
		return [homeCrumb, ...tail];
	} catch {
		return initialValue;
	}
}

const createBreadcrumbs = (initialValue: Breadcrumb[]) => {
	const breadcrumbs = writable<Breadcrumb[]>(loadFromSession(initialValue));

	if (browser) {
		breadcrumbs.subscribe((value) => {
			try {
				sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
			} catch {}
		});
	}

	function mergeCrumbs(crumbs: Breadcrumb[]) {
		const mergedCrumbs: Breadcrumb[] = [];
		for (const crumb of crumbs) {
			const lastCrumb = mergedCrumbs[mergedCrumbs.length - 1];
			if (lastCrumb?.href !== crumb.href) {
				mergedCrumbs.push(crumb);
			}
		}
		return mergedCrumbs;
	}

	function push(crumb: Breadcrumb[]) {
		breadcrumbs.update((value) => {
			const newCrumbs = mergeCrumbs([...value.slice(1, value.length), ...crumb]);
			return [homeCrumb, ...newCrumbs.slice(-BREADCRUMBS_MAX_DEPTH)];
		});
	}

	function updateCrumb(hrefPattern: RegExp, updatedCrumb: Breadcrumb) {
		breadcrumbs.update((crumbs) => {
			for (let i = 0; i < crumbs.length; i++) {
				const crumb = crumbs[i];
				if (hrefPattern.test(crumb.href ?? '')) {
					crumbs[i] = { ...crumb, ...updatedCrumb };
				}
			}
			return crumbs;
		});
	}

	function replace(crumb: Breadcrumb[]) {
		breadcrumbs.update(() => {
			return mergeCrumbs([homeCrumb, ...crumb]);
		});
	}

	function slice(index: number) {
		breadcrumbs.update((value) => {
			return value.slice(0, index + 1);
		});
	}

	function clear() {
		if (browser) {
			try {
				sessionStorage.removeItem(STORAGE_KEY);
			} catch {}
		}
		breadcrumbs.set([homeCrumb]);
	}

	return {
		...breadcrumbs,
		push,
		updateCrumb,
		replace,
		slice,
		clear
	};
};

export const breadcrumbs = createBreadcrumbs([homeCrumb]);

export function goto(
	url: string,
	_opts: { crumbs?: typeof breadcrumbs; label: string; breadcrumbAction: 'push' | 'replace' } = {}
) {
	const opts = {
		crumbs: breadcrumbs,
		label: '',
		breadcrumbAction: 'push',
		..._opts
	};

	const { crumbs, label, breadcrumbAction } = opts;
	const crumb = { label, href: url };
	crumbs[breadcrumbAction]([crumb]);
	return _goto(url, opts);
}
