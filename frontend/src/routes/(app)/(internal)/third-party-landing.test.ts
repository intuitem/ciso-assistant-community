import { existsSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { load } from './+layout.server';

const taskPage = '/(app)/(internal)/task-templates/[id=uuid]';

function open(routeId: string, isThirdParty: boolean) {
	return load({
		locals: { getUser: async () => ({ is_third_party: isThirdParty }) },
		route: { id: routeId },
		untrack: (fn: () => unknown) => fn(),
		cookies: { get: () => undefined }
	} as unknown as Parameters<typeof load>[0]);
}

describe('internal pages opened by a third party', () => {
	it('sends a task link to their own task list', async () => {
		await expect(open(taskPage, true)).rejects.toMatchObject({
			status: 302,
			location: '/my-tasks?mine'
		});
		// The route id is matched by name: a moved page must not silently lose the redirect.
		expect(existsSync(`src/routes${taskPage}/+page.svelte`)).toBe(true);
	});

	it('sends any other page to their dashboard', async () => {
		await expect(open('/(app)/(internal)/analytics', true)).rejects.toMatchObject({
			status: 302,
			location: '/auditee-dashboard'
		});
	});

	it('lets an internal user through', async () => {
		expect(await open(taskPage, false)).toMatchObject({ user: { is_third_party: false } });
	});
});
