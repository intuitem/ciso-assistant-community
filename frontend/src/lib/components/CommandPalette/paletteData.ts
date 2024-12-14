import { goto } from '$app/navigation';
import * as m from '$paraglide/messages';

export interface NavigationLink {
	label: string;
	href: string;
}

export const navigationLinks: NavigationLink[] = [
	{
		label: m.analytics(),
		href: '/'
	},
	{
		label: m.settings(),
		href: '/settings'
	}
];
