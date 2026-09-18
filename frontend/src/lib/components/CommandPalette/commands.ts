import { hasPermissionAnywhere } from '$lib/utils/access-control';
import { CREATE_ROUTE_OVERRIDES, NON_CREATABLE_URL_MODELS, URL_MODEL_MAP } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';
import { getSidebarVisibleItems } from '$lib/utils/sidebar-config';
import type { User } from '$lib/utils/types';
import { navData } from '../SideBar/navData';
import { canSeeNavItem, type NavItem } from '../SideBar/navVisibility';

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
	/**
	 * Verbs selecting this command in `/` mode, the rest of the input becoming its argument —
	 * `/search acme` runs the `search` command with `acme`. List the localised verb and the
	 * English one, so both work whatever the locale. A command with keywords takes an
	 * argument and does nothing without one.
	 *
	 * Each verb must be a SINGLE WORD: matching compares it to the first token, so anything
	 * containing a space can never match. Translate them through their own `commandKeyword*`
	 * messages rather than reusing a label, which a locale may well render as two words.
	 */
	keywords?: string[];
	run?: (argument: string) => void;
}

/** Strip accents/diacritics so matching is accent-insensitive. */
export function normalize(str: string): string {
	return str.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

export interface CommandMatch {
	items: PaletteCommand[];
	/** The command the first token names, once an argument has been started. */
	verbCommand?: PaletteCommand;
	/** Everything after the verb, verbatim — empty unless `verbCommand` is set. */
	argument: string;
}

/**
 * Resolve what the typed query selects. Two grammars share one input: `verb the rest`, where
 * the first token names a command and the remainder is its argument, and plain filtering over
 * labels. The verb grammar only engages once a space is typed, so `/sea` still filters labels
 * normally and only `/search acme` binds an argument.
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

/** A keyword command is only actionable once it has input to act on. */
export function awaitingArgument(command: PaletteCommand, argument: string): boolean {
	return Boolean(command.keywords?.length) && !argument.trim();
}

interface Destination {
	name: string;
	href: string;
	icon?: string;
	/** Feature flag gating a destination that has no sidebar entry to inherit one from. */
	flag?: string;
	/** The sidebar entry this came from, carrying its permission rules. */
	nav?: NavItem;
}

type FeatureFlags = Record<string, boolean>;

const sidebarDestinations: Destination[] = ((navData.items ?? []) as { items?: NavItem[] }[])
	.flatMap((section) => section.items ?? [])
	.filter((item): item is NavItem & { name: string; href: string } =>
		Boolean(item?.name && item?.href)
	)
	.map((item) => ({ name: item.name, href: item.href, icon: item.fa_icon, nav: item }));

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

/**
 * Two independent axes decide whether a destination is offered: the feature flags, and the
 * user's own permissions. A destination the sidebar hides must not be reachable here either,
 * otherwise the palette offers a page that answers 403.
 */
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
