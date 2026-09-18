import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { CREATE_ROUTE_OVERRIDES, URL_MODEL_MAP } from '$lib/utils/crud';
import { THIRD_PARTY_URL_MODEL } from '$lib/utils/types';
import type { User } from '$lib/utils/types';
import { buildCreateCommands } from './commands';

const ROOT = '00000000-0000-0000-0000-000000000000';
const ROUTES = resolve(__dirname, '../../../routes/(app)');

const superuser = {
	root_folder_id: ROOT,
	is_admin: true,
	roles: ['BI-RL-GLA'],
	domain_permissions: {
		[ROOT]: Object.values(URL_MODEL_MAP).flatMap((model) => [
			`add_${model.name}`,
			`view_${model.name}`
		])
	}
} as unknown as User;

const allFlags = new Proxy({}, { get: () => true }) as Record<string, boolean>;

/**
 * Two generic routes exist with overlapping matchers: `THIRD_PARTY_URL_MODEL` models are
 * served by the `(third-party)` one. A dedicated directory wins over both.
 */
function servingPage(urlModel: string): string {
	const dedicated = `${ROUTES}/(internal)/${urlModel}/+page.svelte`;
	if (existsSync(dedicated)) return dedicated;
	if ((THIRD_PARTY_URL_MODEL as readonly string[]).includes(urlModel)) {
		return `${ROUTES}/(third-party)/[model=thirdparty_urlmodels]/+page.svelte`;
	}
	return `${ROUTES}/(internal)/[model=urlmodel]/+page.svelte`;
}

/**
 * Nothing at runtime connects a command to its landing page, so walk each one back to the
 * route file that serves it. Caught `compliance-assessments` and `evidences` resolving to
 * the `(third-party)` route, which had no `consumeCreateIntent`.
 */
describe('every create command lands on a page that opens the form', () => {
	const commands = buildCreateCommands(superuser, allFlags);

	it('generates commands to check', () => {
		expect(commands.length).toBeGreaterThan(40);
	});

	for (const command of commands) {
		const urlModel = command.href!.replace(/^\//, '');
		const overridden = Object.values(CREATE_ROUTE_OVERRIDES).includes(command.href!);

		it(`${command.href} (${command.label})`, () => {
			if (overridden) {
				// Creation is its own page; there is no intent to consume, just a route to exist.
				const page = `${ROUTES}/(internal)/${urlModel}/+page.svelte`;
				expect(existsSync(page), `${command.href} has no page`).toBe(true);
				expect(command.opensCreateForm).toBe(false);
				return;
			}

			const page = servingPage(urlModel);
			expect(existsSync(page), `no page serves ${command.href}`).toBe(true);
			// Word-boundary anchored: a renamed or shadowed identifier must not satisfy this.
			expect(
				readFileSync(page, 'utf8'),
				`${page} serves ${command.href} but never calls consumeCreateIntent`
			).toMatch(/(?<![\w$])consumeCreateIntent\s*\(/);
		});
	}
});
