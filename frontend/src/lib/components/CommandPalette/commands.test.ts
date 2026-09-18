import { describe, expect, it, vi } from 'vitest';

import { CREATE_INTENT_PARAM, createIntentHref } from '$lib/utils/create-intent';
import { NON_CREATABLE_URL_MODELS, URL_MODEL_MAP } from '$lib/utils/crud';
import type { User } from '$lib/utils/types';
import {
	awaitingArgument,
	buildCreateCommands,
	buildNavigationCommands,
	matchCommands,
	type PaletteCommand
} from './commands';

const ROOT = '00000000-0000-0000-0000-000000000000';

const everyPermission = Object.values(URL_MODEL_MAP).flatMap((model) => [
	`add_${model.name}`,
	`view_${model.name}`,
	`change_${model.name}`,
	`delete_${model.name}`
]);

/** Holds every permission on the root folder, and a role no sidebar entry excludes. */
const superuser = {
	root_folder_id: ROOT,
	is_admin: true,
	roles: ['BI-RL-GLA'],
	domain_permissions: { [ROOT]: everyPermission }
} as unknown as User;

/** Can see every page, but may create nothing. */
const readOnly = {
	root_folder_id: ROOT,
	is_admin: true,
	roles: ['BI-RL-GLA'],
	domain_permissions: {
		[ROOT]: everyPermission.filter((codename) => !codename.startsWith('add_'))
	}
} as unknown as User;

const nobody = { root_folder_id: ROOT, domain_permissions: {} } as unknown as User;

// Every flag on, so the derivation is exercised at its widest.
const allFlags = new Proxy({}, { get: () => true }) as Record<string, boolean>;

describe('buildCreateCommands', () => {
	it('returns nothing without the add permission', () => {
		expect(buildCreateCommands(nobody, allFlags)).toEqual([]);
		expect(buildCreateCommands(null, allFlags)).toEqual([]);
	});

	// Same gate as `ModelTable.canCreateObject`.
	it('offers nothing to a user who may view every page but create nothing', () => {
		expect(buildCreateCommands(readOnly, allFlags)).toEqual([]);
	});

	it('offers only the models a partially-privileged user may add', () => {
		const assetsOnly = {
			root_folder_id: ROOT,
			is_admin: true,
			roles: ['BI-RL-GLA'],
			domain_permissions: {
				[ROOT]: [...everyPermission.filter((c) => !c.startsWith('add_')), 'add_asset']
			}
		} as unknown as User;
		const hrefs = buildCreateCommands(assetsOnly, allFlags).map((command) => command.href);
		expect(hrefs).toEqual(['/assets']);
	});

	it('offers a create command for the models a user may add', () => {
		const commands = buildCreateCommands(superuser, allFlags);
		expect(commands.length).toBeGreaterThan(40);
		expect(commands.every((command) => command.group === 'create')).toBe(true);
		expect(commands).toContainEqual(
			expect.objectContaining({ href: '/assets', opensCreateForm: true })
		);
	});

	it('never offers a model excluded from list-page creation', () => {
		const hrefs = buildCreateCommands(superuser, allFlags).map((command) => command.href);
		for (const urlModel of NON_CREATABLE_URL_MODELS) {
			expect(hrefs).not.toContain(`/${urlModel}`);
		}
	});

	it('sends models whose creation is a page to that page, with no create intent', () => {
		const commands = buildCreateCommands(superuser, allFlags);
		expect(commands).toContainEqual(
			expect.objectContaining({ href: '/documents/new', opensCreateForm: false })
		);
		expect(commands.map((command) => command.href)).not.toContain('/documents');
	});

	it('drops commands whose feature flag is off', () => {
		const noFlags = {} as Record<string, boolean>;
		const hrefs = buildCreateCommands(superuser, noFlags).map((command) => command.href);
		expect(hrefs).not.toContain('/ebios-rm');
		// Flag-free destinations survive.
		expect(hrefs).toContain('/assets');
	});

	it('resolves every label, leaving no raw i18n key', () => {
		for (const command of buildCreateCommands(superuser, allFlags)) {
			expect(command.label).not.toMatch(/^add-/);
		}
	});
});

describe('matchCommands', () => {
	const note: PaletteCommand = {
		label: 'Add note',
		group: 'action',
		keywords: ['note', 'annoter'],
		run: () => {}
	};
	const chat: PaletteCommand = { label: 'AI engine (Chat)', group: 'action', run: () => {} };
	const pool = [note, chat];

	it('filters on labels while a single token is being typed', () => {
		expect(matchCommands(pool, 'not').items).toEqual([note]);
		expect(matchCommands(pool, 'not').verbCommand).toBeUndefined();
		expect(matchCommands(pool, 'not').argument).toBe('');
	});

	it('binds the rest of the input as the argument once a verb is followed by a space', () => {
		const match = matchCommands(pool, 'note call the auditor');
		expect(match.verbCommand).toBe(note);
		expect(match.items).toEqual([note]);
		expect(match.argument).toBe('call the auditor');
	});

	it('keeps the command selected before any argument is typed', () => {
		const match = matchCommands(pool, 'note ');
		expect(match.verbCommand).toBe(note);
		expect(match.argument).toBe('');
	});

	it('preserves the argument verbatim, including its inner spacing and case', () => {
		expect(matchCommands(pool, 'note  Rapport  ISO 27001 ').argument).toBe(' Rapport  ISO 27001 ');
	});

	it('matches a localised verb and is accent-insensitive', () => {
		expect(matchCommands(pool, 'annoter ceci').verbCommand).toBe(note);
		expect(matchCommands(pool, 'ANNOTER ceci').verbCommand).toBe(note);
	});

	it('falls back to label filtering when the first token names no command', () => {
		const match = matchCommands(pool, 'nope some text');
		expect(match.verbCommand).toBeUndefined();
		expect(match.items).toEqual([]);
		expect(match.argument).toBe('');
	});

	it('never binds an argument to a command that takes none', () => {
		expect(matchCommands(pool, 'AI engine (Chat)').verbCommand).toBeUndefined();
	});

	it('lists everything on an empty query', () => {
		expect(matchCommands(pool, '').items).toEqual(pool);
	});

	// Guards `commandKeyword*` against a locale rendering a verb as two words.
	it('cannot match a multi-word keyword, which is why verbs must be single words', () => {
		const broken: PaletteCommand = {
			label: 'Ask AI',
			group: 'action',
			keywords: ["demander à l'IA"]
		};
		expect(matchCommands([broken], "demander à l'IA something").verbCommand).toBeUndefined();
	});
});

describe('shipped command keywords', () => {
	it('are single words in every locale', async () => {
		const { baseLocale, locales } = await import('$paraglide/runtime');
		const { commandKeywordAsk, commandKeywordSearch } = await import('$paraglide/messages');
		for (const locale of locales) {
			for (const message of [commandKeywordSearch, commandKeywordAsk]) {
				const keyword = message({}, { locale });
				expect(keyword, `${keyword} in ${locale}`).not.toMatch(/\s/);
				expect(keyword.length, `${keyword} in ${locale}`).toBeGreaterThan(0);
			}
		}
		expect(locales).toContain(baseLocale);
	});
});

describe('awaitingArgument', () => {
	const note: PaletteCommand = { label: 'Add note', group: 'action', keywords: ['note'] };
	const chat: PaletteCommand = { label: 'Chat', group: 'action' };

	it('holds a keyword command until it has input', () => {
		expect(awaitingArgument(note, '')).toBe(true);
		expect(awaitingArgument(note, '   ')).toBe(true);
		expect(awaitingArgument(note, 'something')).toBe(false);
	});

	it('never holds a command that takes no argument', () => {
		expect(awaitingArgument(chat, '')).toBe(false);
	});
});

describe('createIntentHref', () => {
	it('asks the list page for its create form', () => {
		const url = new URL(createIntentHref('/assets'), 'http://localhost');
		expect(url.pathname).toBe('/assets');
		expect(url.searchParams.has(CREATE_INTENT_PARAM)).toBe(true);
	});

	it('changes over time, so re-running it on the target page is still a navigation', () => {
		const before = createIntentHref('/assets');
		vi.useFakeTimers();
		vi.setSystemTime(new Date(Date.now() + 60_000));
		const after = createIntentHref('/assets');
		vi.useRealTimers();
		expect(after).not.toBe(before);
	});
});

describe('buildNavigationCommands', () => {
	it('labels and links every visible destination', () => {
		const commands = buildNavigationCommands(superuser, allFlags);
		expect(commands.length).toBeGreaterThan(40);
		expect(commands.every((command) => command.group === 'navigation')).toBe(true);
		expect(commands.every((command) => command.href?.startsWith('/'))).toBe(true);
	});

	it('includes destinations that have no sidebar entry', () => {
		const hrefs = buildNavigationCommands(superuser, allFlags).map((command) => command.href);
		expect(hrefs).toContain('/my-profile');
	});

	// Same rule as `SideBarNavigation`, via the shared `canSeeNavItem`.
	it('hides sidebar destinations the user has no permission for', () => {
		const commands = buildNavigationCommands(nobody, allFlags);
		const hrefs = commands.map((command) => command.href);
		expect(hrefs).not.toContain('/assets');
		expect(hrefs).not.toContain('/compliance-assessments');
		// Destinations with no sidebar entry carry no permission rules of their own.
		expect(hrefs).toContain('/my-profile');
	});

	it('still offers a page to a user who may view but not create', () => {
		const hrefs = buildNavigationCommands(readOnly, allFlags).map((command) => command.href);
		expect(hrefs).toContain('/assets');
	});

	// `ServiceAccountViewSet` is `IsGlobalAdmin`; no sidebar entry means no inherited rule.
	it('hides an admin-only destination from a non-admin, flag notwithstanding', () => {
		const nonAdmin = { ...superuser, is_admin: false } as unknown as User;
		const hrefs = buildNavigationCommands(nonAdmin, allFlags).map((command) => command.href);
		expect(hrefs).not.toContain('/service-accounts');
		expect(hrefs).toContain('/my-profile');
	});

	it('offers it to an admin', () => {
		const hrefs = buildNavigationCommands(superuser, allFlags).map((command) => command.href);
		expect(hrefs).toContain('/service-accounts');
	});
});
