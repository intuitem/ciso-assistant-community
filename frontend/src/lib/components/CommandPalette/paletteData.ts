import * as m from '$paraglide/messages';
import { navData } from '../SideBar/navData';

export interface NavigationLink {
	label: string;
	href: string;
}
const flattenNavData = (navData) => {
	const result = [];

	// Handle potentially incomplete/malformed data
	if (!navData?.items) return result;

	for (const section of navData.items) {
		if (!section.items) continue;

		for (const item of section.items) {
			if (item.name && item.href) {
				result.push({
					label: item.name,
					href: item.href
				});
			}
		}
	}

	return result;
};
export let navigationLinks: NavigationLink[] = flattenNavData(navData);
navigationLinks.push({
	label: 'myProfile',
	href: '/my-profile'
});

// wre can use the same trick later on for dynamic actions
