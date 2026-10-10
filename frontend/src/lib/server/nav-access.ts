import { match } from '$app/paths';
import { navData } from '$lib/components/SideBar/navData';
import type { NavItem } from '$lib/components/SideBar/navVisibility';
import { thirdPartyMayOpen } from '$lib/utils/route-access';

/**
 * The sidebar hrefs whose page a third party may open, each resolved to its route the way the
 * router resolves it, so the sidebar never offers a page the guard in hooks.server.ts refuses.
 */
export async function thirdPartyNavHrefs(): Promise<string[]> {
	const hrefs = navData.items.flatMap((category) =>
		(category.items as NavItem[]).flatMap((item) => (item.href ? [item.href] : []))
	);
	const routes = await Promise.all(hrefs.map((href) => match(href)));
	return hrefs.filter((_, i) => {
		const route = routes[i];
		return route !== null && thirdPartyMayOpen(route.id);
	});
}
