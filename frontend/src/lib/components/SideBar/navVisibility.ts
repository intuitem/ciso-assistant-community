import { hasPermissionAnywhere } from '$lib/utils/access-control';
import { URL_MODEL_MAP } from '$lib/utils/crud';
import type { User } from '$lib/utils/types';

export interface NavItem {
	name?: string;
	href?: string;
	fa_icon?: string;
	adminOnly?: boolean;
	exclude?: string[];
	permissions?: string[];
}

/**
 * Whether a sidebar entry is visible to this user, independently of feature flags.
 *
 * Shared by the sidebar and the command palette: an entry the sidebar hides must not be
 * reachable from the palette either, or we offer a page that answers 403. Feature-flag
 * visibility is a separate axis, handled by `getSidebarVisibleItems`.
 */
export function canSeeNavItem(item: NavItem, user: User | null | undefined): boolean {
	if (item.adminOnly) return Boolean(user?.is_admin);
	// Preserved verbatim from the sidebar: true when the user holds any role that is not
	// excluded, not when they hold none of the excluded ones.
	if (item.exclude) {
		return user?.roles?.some((role: string) => !item.exclude!.includes(role)) ?? false;
	}
	if (item.permissions) {
		return item.permissions.some((permission) => hasPermissionAnywhere(user, permission));
	}
	// An entry may preselect a filter (`/campaigns?kind=internal`); the model it maps to is
	// the path alone.
	const urlModel = item.href?.split('?')[0].split('/')[1] ?? '';
	if (Object.hasOwn(URL_MODEL_MAP, urlModel)) {
		return hasPermissionAnywhere(user, `view_${URL_MODEL_MAP[urlModel].name}`);
	}
	return false;
}
