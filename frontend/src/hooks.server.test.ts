import { isRedirect } from '@sveltejs/kit';
import { describe, expect, it, vi } from 'vitest';

// $lib/server/logger reads $env/dynamic/private, a SvelteKit virtual module
// vitest cannot resolve; mocking it keeps hooks.server.ts importable here.
vi.mock('$lib/server/logger', () => ({
	installJsonConsole: () => {},
	logger: { debug: () => {}, info: () => {}, warning: () => {}, error: () => {} }
}));

const { handleFetch } = await import('./hooks.server');
const { ALLAUTH_API_URL } = await import('$lib/utils/constants');

const SSO_USER = { is_sso: true };
const LOCAL_USER = { is_sso: false };

const REAUTHENTICATION_REQUIRED = {
	status: 401,
	data: { flows: [{ id: 'reauthenticate' }] },
	meta: { is_authenticated: true }
};
const SESSION_GONE = { status: 401, meta: { is_authenticated: false } };

function buildEvent(user: Record<string, unknown>) {
	const jar = new Map([
		['token', 'knox-token'],
		['allauth_session_token', 'allauth-token']
	]);
	return {
		url: new URL('http://localhost:5173/my-profile/settings'),
		cookies: {
			get: (name: string) => jar.get(name),
			set: (name: string, value: string) => jar.set(name, value),
			delete: (name: string) => jar.delete(name)
		},
		// Only getUser, never locals.user: a form action runs before any load,
		// so nothing has resolved it by the time handleFetch decides.
		locals: { getUser: async () => user }
	} as never;
}

function callWith(user: Record<string, unknown>, body: unknown) {
	return handleFetch({
		request: new Request(`${ALLAUTH_API_URL}/account/authenticators`),
		fetch: vi.fn(
			async () =>
				new Response(JSON.stringify(body), {
					status: 401,
					headers: { 'content-type': 'application/json' }
				})
		),
		event: buildEvent(user)
	} as never);
}

describe('handleFetch, 401 from an allauth account endpoint', () => {
	it('signs out a local user so they can re-enter their password', async () => {
		await expect(callWith(LOCAL_USER, REAUTHENTICATION_REQUIRED)).rejects.toSatisfy(isRedirect);
	});

	it('keeps an SSO user, who has no password to re-enter', async () => {
		expect((await callWith(SSO_USER, REAUTHENTICATION_REQUIRED)).status).toBe(401);
	});

	it('signs out an SSO user whose allauth session is gone', async () => {
		await expect(callWith(SSO_USER, SESSION_GONE)).rejects.toSatisfy(isRedirect);
	});
});
