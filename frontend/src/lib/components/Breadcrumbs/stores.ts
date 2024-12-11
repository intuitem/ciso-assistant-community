import { writable } from 'svelte/store';

interface Breadcrumb {
	label: string;
	href: string;
}

export const breadcrumbs = writable<Breadcrumb[]>([]);
