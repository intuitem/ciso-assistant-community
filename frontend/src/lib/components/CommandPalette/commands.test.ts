import { describe, expect, it, vi } from 'vitest';

import { CREATE_INTENT_PARAM, createIntentHref } from '$lib/utils/create-intent';
import { NON_CREATABLE_URL_MODELS, URL_MODEL_MAP } from '$lib/utils/crud';
import type { User } from '$lib/utils/types';
import { buildCreateCommands, buildNavigationCommands } from './commands';

const ROOT = '00000000-0000-0000-0000-000000000000';

/** A user holding `add_<model>` on the root folder for every model in the map. */
const superuser = {
	root_folder_id: ROOT,
	domain_permissions: {
		[ROOT]: Object.values(URL_MODEL_MAP).map((model) => `add_${model.name}`)
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
		const commands = buildNavigationCommands(allFlags);
		expect(commands.length).toBeGreaterThan(40);
		expect(commands.every((command) => command.group === 'navigation')).toBe(true);
		expect(commands.every((command) => command.href?.startsWith('/'))).toBe(true);
	});

	it('includes destinations that have no sidebar entry', () => {
		const hrefs = buildNavigationCommands(allFlags).map((command) => command.href);
		expect(hrefs).toContain('/my-profile');
	});
});
