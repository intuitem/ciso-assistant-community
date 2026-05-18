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

function loadFromSession(initialValue: Breadcrumb[]): Breadcrumb[] {
	if (!browser) return initialValue;
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return initialValue;
		const parsed = JSON.parse(raw) as Breadcrumb[];
		return [homeCrumb, ...parsed.slice(1)];
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

	return {
		...breadcrumbs,
		push,
		updateCrumb,
		replace,
		slice
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
