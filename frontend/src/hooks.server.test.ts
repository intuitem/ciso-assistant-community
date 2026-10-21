import { describe, expect, it, vi } from 'vitest';

// $lib/server/logger reads $env/dynamic/private, a SvelteKit virtual module
// vitest cannot resolve; mocking it keeps hooks.server.ts importable here.
vi.mock('$lib/server/logger', () => ({
	installJsonConsole: () => {},
	logger: { debug: () => {}, info: () => {}, warning: () => {}, error: () => {} }
}));

const { handleFetch } = await import('./hooks.server');
const { ALLAUTH_API_URL } = await import('$lib/utils/constants');

const SESSION_COOKIES = ['token', 'allauth_session_token'];

const PASSWORD = { id: 'reauthenticate' };
const mfa = (...types: string[]) => ({ id: 'mfa_reauthenticate', types });
const reauthenticationRequired = (...flows: Record<string, unknown>[]) => ({
	status: 401,
	data: { flows },
	meta: { is_authenticated: true }
});
const SESSION_GONE = { status: 401, meta: { is_authenticated: false } };

function callWith(body: unknown) {
	const jar = new Map(SESSION_COOKIES.map((name) => [name, `${name}-value`]));
	const response = handleFetch({
		request: new Request(`${ALLAUTH_API_URL}/account/authenticators`),
		fetch: vi.fn(
			async () =>
				new Response(JSON.stringify(body), {
					status: 401,
					headers: { 'content-type': 'application/json' }
				})
		),
		event: {
			url: new URL('http://localhost:5173/my-profile/settings?tab=security'),
			cookies: {
				get: (name: string) => jar.get(name),
				set: (name: string, value: string) => jar.set(name, value),
				delete: (name: string) => jar.delete(name)
			},
			locals: {}
		}
	} as never);
	return { response, jar };
}

const NEXT = encodeURIComponent('/my-profile/settings?tab=security');

describe('handleFetch, 401 from an allauth account endpoint', () => {
	it('asks for the second factor when the account has one, keeping the session', async () => {
		const { response, jar } = callWith(reauthenticationRequired(PASSWORD, mfa('totp', 'webauthn')));

		await expect(response).rejects.toMatchObject({
			status: 302,
			location: `/reauthenticate?method=mfa&types=totp,webauthn&next=${NEXT}`
		});
		expect([...jar.keys()]).toEqual(SESSION_COOKIES);
	});

	it('asks for the password when the account has no second factor', async () => {
		await expect(callWith(reauthenticationRequired(PASSWORD)).response).rejects.toMatchObject({
			status: 302,
			location: `/reauthenticate?method=password&next=${NEXT}`
		});
	});

	it('passes the 401 through when no reauthentication flow is offered', async () => {
		const { response, jar } = callWith(reauthenticationRequired());

		expect((await response).status).toBe(401);
		expect([...jar.keys()]).toEqual(SESSION_COOKIES);
	});

	it('signs out a user whose allauth session is gone', async () => {
		await expect(callWith(SESSION_GONE).response).rejects.toMatchObject({
			status: 302,
			location: '/login?next=/my-profile/settings'
		});
	});
});
