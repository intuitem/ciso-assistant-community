import { hasPermissionAnywhere } from '$lib/utils/access-control';
import { CREATE_ROUTE_OVERRIDES, NON_CREATABLE_URL_MODELS, URL_MODEL_MAP } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';
import { getSidebarVisibleItems } from '$lib/utils/sidebar-config';
import type { User } from '$lib/utils/types';
import { navData } from '../SideBar/navData';

export type PaletteGroup = 'navigation' | 'create' | 'action';

export interface PaletteCommand {
	/** Already translated — the palette matches and renders this verbatim. */
	label: string;
	group: PaletteGroup;
	icon?: string;
	/** Navigation target. Every command is a destination unless it carries `run`. */
	href?: string;
	/** `href` is a list page to be asked to open its create form, not a plain destination. */
	opensCreateForm?: boolean;
	/** Breadcrumb label for the navigation, defaulting to the i18n key behind `label`. */
	breadcrumb?: string;
	run?: () => void;
}

interface Destination {
	name: string;
	href: string;
	icon?: string;
	/** Feature flag gating a destination that has no sidebar entry to inherit one from. */
	flag?: string;
}

type FeatureFlags = Record<string, boolean>;

// `navData` entries carry per-section shapes that widen to a union; the palette only ever
// needs the three fields every leaf has.
interface NavLeaf {
	name?: string;
	href?: string;
	fa_icon?: string;
}

const sidebarDestinations: Destination[] = ((navData.items ?? []) as { items?: NavLeaf[] }[])
	.flatMap((section) => section.items ?? [])
	.filter((item): item is NavLeaf & { name: string; href: string } =>
		Boolean(item?.name && item?.href)
	)
	.map((item) => ({ name: item.name, href: item.href, icon: item.fa_icon }));

// Reachable pages with no sidebar entry of their own.
const EXTRA_DESTINATIONS: Destination[] = [
	{ name: 'myProfile', href: '/my-profile', icon: 'fa-solid fa-user' },
	{
		name: 'serviceAccounts',
		href: '/service-accounts',
		icon: 'fa-solid fa-user-gear',
		flag: 'service_accounts'
	},
	{ name: 'licenseManagement', href: '/license-management', icon: 'fa-solid fa-certificate' },
	{ name: 'journeys', href: '/journeys', icon: 'fa-solid fa-route', flag: 'journeys' }
];

// Sidebar entries whose href is not the model's own list route.
const HREF_URL_MODEL: Record<string, string> = {
	'/documents': 'document-containers'
};

const destinations = [...sidebarDestinations, ...EXTRA_DESTINATIONS];

function isVisible(
	destination: Destination,
	featureFlags: FeatureFlags,
	visible: Record<string, boolean>
): boolean {
	if (destination.flag) return featureFlags[destination.flag] === true;
	return visible[destination.name] !== false;
}

export function buildNavigationCommands(featureFlags: FeatureFlags): PaletteCommand[] {
	const visible = getSidebarVisibleItems(featureFlags);
	return destinations
		.filter((destination) => isVisible(destination, featureFlags, visible))
		.map((destination) => ({
			label: safeTranslate(destination.name),
			breadcrumb: destination.name,
			group: 'navigation' as const,
			icon: destination.icon,
			href: destination.href
		}));
}

/**
 * One create command per sidebar destination backed by a model the user may create.
 * Deriving from the sidebar rather than from `URL_MODEL_MAP` keeps the command set in step
 * with feature flags and guarantees the list route it lands on exists; the page opens its
 * own create modal on `?create`. `EXTRA_DESTINATIONS` are navigation-only — they are pages
 * we reach past the sidebar, not lists that own a create form.
 */
export function buildCreateCommands(
	user: User | null | undefined,
	featureFlags: FeatureFlags
): PaletteCommand[] {
	const visible = getSidebarVisibleItems(featureFlags);
	const commands: PaletteCommand[] = [];
	for (const destination of sidebarDestinations) {
		if (!isVisible(destination, featureFlags, visible)) continue;

		const urlModel = HREF_URL_MODEL[destination.href] ?? destination.href.replace(/^\//, '');
		const model = URL_MODEL_MAP[urlModel];
		if (!model) continue;
		if (NON_CREATABLE_URL_MODELS.includes(urlModel)) continue;
		if (!hasPermissionAnywhere(user, `add_${model.name}`)) continue;

		const createPage = CREATE_ROUTE_OVERRIDES[urlModel];
		commands.push({
			label: safeTranslate(`add-${model.localName}`),
			breadcrumb: destination.name,
			group: 'create',
			icon: destination.icon,
			href: createPage ?? destination.href,
			opensCreateForm: !createPage
		});
	}
	return commands;
}
