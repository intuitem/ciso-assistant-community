import { hasPermissionAnywhere } from '$lib/utils/access-control';
import { CREATE_ROUTE_OVERRIDES, NON_CREATABLE_URL_MODELS, URL_MODEL_MAP } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';
import { getSidebarVisibleItems } from '$lib/utils/sidebar-config';
import type { User } from '$lib/utils/types';
import { navData } from '../SideBar/navData';
import { canSeeNavItem, type NavItem } from '../SideBar/navVisibility';

export type PaletteGroup = 'navigation' | 'create' | 'action';

export interface PaletteCommand {
	/** Already translated — matched and rendered verbatim. */
	label: string;
	group: PaletteGroup;
	icon?: string;
	/** A destination, unless the command carries `run`. */
	href?: string;
	/** `href` is a list page to ask for its create form, not a plain destination. */
	opensCreateForm?: boolean;
	/** i18n key for the breadcrumb. */
	breadcrumb?: string;
	/**
	 * Verbs selecting this command in `/` mode; the rest of the input is its argument.
	 * Each must be a SINGLE WORD — matching compares against the first token, so a verb
	 * with a space can never match. Hence the dedicated `commandKeyword*` messages: a
	 * label may be two words in some locale. List the localised verb and the English one.
	 */
	keywords?: string[];
	run?: (argument: string) => void;
}

/** Accent-insensitive matching. */
export function normalize(str: string): string {
	return str.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

export interface CommandMatch {
	items: PaletteCommand[];
	/** The command the first token names, once an argument has been started. */
	verbCommand?: PaletteCommand;
	/** Verbatim; empty unless `verbCommand` is set. */
	argument: string;
}

/**
 * Two grammars over one input: `verb the rest`, and plain label filtering. The verb grammar
 * only engages once a space is typed, so `/sea` still filters labels.
 */
export function matchCommands(pool: PaletteCommand[], query: string): CommandMatch {
	const tokens = query.split(' ');
	if (tokens.length > 1) {
		const verb = normalize(tokens[0]);
		const verbCommand = pool.find((command) =>
			command.keywords?.some((keyword) => normalize(keyword) === verb)
		);
		if (verbCommand) {
			return { items: [verbCommand], verbCommand, argument: tokens.slice(1).join(' ') };
		}
	}
	return {
		items: pool.filter((command) => normalize(command.label).includes(normalize(query))),
		argument: ''
	};
}

/** A keyword command is only actionable once it has input. */
export function awaitingArgument(command: PaletteCommand, argument: string): boolean {
	return Boolean(command.keywords?.length) && !argument.trim();
}

interface Destination {
	name: string;
	href: string;
	icon?: string;
	/** For destinations with no sidebar entry to inherit a flag from. */
	flag?: string;
	/** Carries the permission rules. */
	nav?: NavItem;
}

type FeatureFlags = Record<string, boolean>;

const sidebarDestinations: Destination[] = ((navData.items ?? []) as { items?: NavItem[] }[])
	.flatMap((section) => section.items ?? [])
	.filter((item): item is NavItem & { name: string; href: string } =>
		Boolean(item?.name && item?.href)
	)
	.map((item) => ({ name: item.name, href: item.href, icon: item.fa_icon, nav: item }));

// Pages with no sidebar entry, so no permission rules to inherit: whatever the target's API
// enforces must be restated as a `nav` rule, or the palette offers a link that answers 403.
const EXTRA_DESTINATIONS: Destination[] = [
	{ name: 'myProfile', href: '/my-profile', icon: 'fa-solid fa-user' },
	{
		name: 'serviceAccounts',
		href: '/service-accounts',
		icon: 'fa-solid fa-user-gear',
		flag: 'service_accounts',
		// `ServiceAccountViewSet` is IsGlobalAdmin. The href keeps the rule degrading to
		// `view_serviceaccount` rather than to `false` if `adminOnly` is ever dropped.
		nav: { name: 'serviceAccounts', href: '/service-accounts', adminOnly: true }
	},
	{ name: 'licenseManagement', href: '/license-management', icon: 'fa-solid fa-certificate' },
	{ name: 'journeys', href: '/journeys', icon: 'fa-solid fa-route', flag: 'journeys' }
];

// Sidebar entries whose href is not the model's own list route.
const HREF_URL_MODEL: Record<string, string> = {
	'/documents': 'document-containers'
};

const destinations = [...sidebarDestinations, ...EXTRA_DESTINATIONS];

/** Two axes: feature flags, and the user's permissions. Both must allow it. */
function isVisible(
	destination: Destination,
	user: User | null | undefined,
	featureFlags: FeatureFlags,
	visible: Record<string, boolean>
): boolean {
	if (destination.nav && !canSeeNavItem(destination.nav, user)) return false;
	if (destination.flag) return featureFlags[destination.flag] === true;
	return visible[destination.name] !== false;
}

export function buildNavigationCommands(
	user: User | null | undefined,
	featureFlags: FeatureFlags
): PaletteCommand[] {
	const visible = getSidebarVisibleItems(featureFlags);
	return destinations
		.filter((destination) => isVisible(destination, user, featureFlags, visible))
		.map((destination) => ({
			label: safeTranslate(destination.name),
			breadcrumb: destination.name,
			group: 'navigation' as const,
			icon: destination.icon,
			href: destination.href
		}));
}

/**
 * Derived from the sidebar, not from `URL_MODEL_MAP`: that keeps the set in step with feature
 * flags and guarantees the landing route exists. `EXTRA_DESTINATIONS` are navigation-only.
 */
export function buildCreateCommands(
	user: User | null | undefined,
	featureFlags: FeatureFlags
): PaletteCommand[] {
	const visible = getSidebarVisibleItems(featureFlags);
	const commands: PaletteCommand[] = [];
	for (const destination of sidebarDestinations) {
		if (!isVisible(destination, user, featureFlags, visible)) continue;

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
