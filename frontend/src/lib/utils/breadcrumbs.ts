import { writable } from 'svelte/store';
import { goto as _goto } from '$app/navigation';
import * as m from '$paraglide/messages';

export interface Breadcrumb {
	label: string;
	href?: string;
	icon?: string;
}

const BREADCRUMBS_MAX_DEPTH = 5;

const homeCrumb: Breadcrumb = { label: m.home(), href: '/', icon: 'fa-regular fa-compass' };

const createBreadcrumbs = (initialValue: Breadcrumb[]) => {
	const breadcrumbs = writable<Breadcrumb[]>(initialValue);

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
		replace,
		slice
	};
};

export const breadcrumbs = createBreadcrumbs([homeCrumb]);

export function goto(
	url: string,
	_opts: { crumbs: typeof breadcrumbs; label: string; breadcrumbAction: 'push' | 'replace' } = {}
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
