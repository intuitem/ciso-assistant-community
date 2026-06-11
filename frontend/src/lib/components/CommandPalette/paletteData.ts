import { navData } from '../SideBar/navData';

export interface NavigationLink {
	label: string;
	href: string;
	icon?: string;
}
const flattenNavData = (navData: typeof import('../SideBar/navData').navData) => {
	const result: NavigationLink[] = [];

	if (!navData?.items) return result;

	for (const section of navData.items) {
		if (!section.items) continue;

		for (const item of section.items) {
			if (item.name && item.href) {
				result.push({
					label: item.name,
					href: item.href,
					icon: item.fa_icon
				});
			}
		}
	}

	return result;
};
export let navigationLinks: NavigationLink[] = flattenNavData(navData);
navigationLinks.push({
	label: 'myProfile',
	href: '/my-profile',
	icon: 'fa-solid fa-user'
});

// we can use the same trick later on for dynamic actions
