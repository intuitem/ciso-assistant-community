import { BASE_API_URL, DEFAULT_LANGUAGE } from '$lib/utils/constants';
import { safeTranslate, setUseRiskCategoryLabel } from '$lib/utils/i18n';
import type { User } from '$lib/utils/types';
import {
	error,
	isRedirect,
	redirect,
	type Handle,
	type HandleFetch,
	type HandleServerError,
	type RequestEvent
} from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';

import { loadFeatureFlags } from '$lib/feature-flags';
import { logger, installJsonConsole } from '$lib/server/logger';
import { paraglideMiddleware } from '$paraglide/server';
import { sequence } from '@sveltejs/kit/hooks';
import { defineCustomServerStrategy, toLocale } from '$paraglide/runtime';

// Runs once at server start. When LOG_FORMAT=json, routes the whole SSR stdout
// stream (including not-yet-migrated console.* call sites) through JSON output.
installJsonConsole();

const fallbackLocaleStore = new WeakMap<Request, string>();

defineCustomServerStrategy('custom-fallback', {
	getLocale: (request) => fallbackLocaleStore.get(request) ?? DEFAULT_LANGUAGE
});

const RETRYABLE_STATUSES = new Set([429, 502, 503, 504]);

function memoize<T>(fn: () => Promise<T>): () => Promise<T> {
	let pending: Promise<T> | undefined;
	return () => (pending ??= fn());
}

async function fetchWithRetry(
	url: string,
	init?: RequestInit,
	retries = 3,
	delay = 2000
): Promise<Response> {
	for (let attempt = 0; attempt < retries; attempt++) {
		try {
			const response = await fetch(url, { ...init, signal: AbortSignal.timeout(1000) });
			if (response.ok || !RETRYABLE_STATUSES.has(response.status) || attempt === retries - 1) {
				return response;
			}
		} catch (error) {
			if (attempt === retries - 1) throw error;
		}
		await new Promise((r) => setTimeout(r, delay * (attempt + 1)));
	}
	throw new Error('unreachable');
}

async function fetchDefaultLanguage(): Promise<string> {
	try {
		const response = await fetchWithRetry(`${BASE_API_URL}/settings/general/default-language/`, {
			headers: { 'content-type': 'application/json' }
		});
		if (response.ok) {
			const data = await response.json();
			const language = data?.default_language;
			if (typeof language === 'string' && language.length > 0) return language;
		}
	} catch (error) {
		logger.error('Unable to fetch default language', { error });
	}
	return DEFAULT_LANGUAGE;
}

async function ensureDefaultLocale(event: RequestEvent): Promise<string> {
	const existingLocale = event.cookies.get('LOCALE');
	if (existingLocale) return existingLocale;

	const locale = await fetchDefaultLanguage();
	setLocaleCookie(event, locale);
	return locale;
}

function setLocaleCookie(event: RequestEvent, locale: string) {
	event.cookies.set('LOCALE', locale, {
		httpOnly: false,
		sameSite: 'lax',
		path: '/',
		secure: true
	});
}

function applyUserLocale(event: RequestEvent, user: User | undefined) {
	const preferredLanguage = user?.preferences?.lang;
	if (typeof preferredLanguage !== 'string' || preferredLanguage.length === 0) return;

	setLocaleCookie(event, preferredLanguage);
	fallbackLocaleStore.set(event.request, preferredLanguage);
}

async function ensureCsrfToken(event: RequestEvent): Promise<string> {
	let csrfToken = event.cookies.get('csrftoken') || '';
	if (!csrfToken) {
		try {
			const response = await fetchWithRetry(`${BASE_API_URL}/csrf/`, {
				credentials: 'include',
				headers: { 'content-type': 'application/json' }
			});
			if (!response.ok) {
				logger.error('CSRF endpoint returned an error status', {
					status: response.status
				});
				return csrfToken;
			}
			const data = await response.json();
			const token = data?.csrfToken;
			if (typeof token !== 'string' || token.length === 0) {
				logger.error('CSRF endpoint returned an invalid token payload');
				return csrfToken;
			}
			csrfToken = token;
			event.cookies.set('csrftoken', csrfToken, {
				httpOnly: false,
				sameSite: 'lax',
				path: '/',
				secure: true
			});
		} catch (error) {
			logger.error('Unable to fetch CSRF token', { error });
		}
	}
	return csrfToken;
}

function logoutUser(event: RequestEvent) {
	event.cookies.delete('token', {
		path: '/'
	});
	const allauthSessionToken = event.cookies.get('allauth_session_token');
	if (allauthSessionToken) {
		event.cookies.delete('allauth_session_token', { path: '/' });
	}
	redirect(302, `/login?next=${event.url.pathname}`);
}

async function validateUserSession(event: RequestEvent): Promise<User | null> {
	const token = event.cookies.get('token');
	if (!token) return null;

	const allauthSessionToken = event.cookies.get('allauth_session_token');
	if (!allauthSessionToken) logoutUser(event);

	const res = await fetch(`${BASE_API_URL}/iam/current-user/`, {
		credentials: 'include',
		headers: {
			'content-type': 'application/json',
			Authorization: `Token ${token}`
		}
	});

	if (!res.ok) logoutUser(event);

	return res.json();
}

/**
 * Authenticated JSON, never cached.
 *
 * Every `/fe-api/` route proxies a cookie-authenticated backend call, and the browser
 * cache key is the constant proxy URL rather than the session — so a cached response
 * can outlive a sign-out or an account switch in the same browser. One place rather
 * than 17, and it covers routes nobody has written yet.
 */
const noStoreForFeApi: Handle = async ({ event, resolve }) => {
	const response = await resolve(event);
	if (event.url.pathname.startsWith('/fe-api/')) {
		response.headers.set('Cache-Control', 'no-store');
	}
	return response;
};

const handleRequest: Handle = async ({ event, resolve }) => {
	// Inbound webhook passthrough: unauthenticated by design (the
	// URL secret is the credential) — skip locale middleware, CSRF-token fetch
	// and session validation, none of which apply to machine deliveries.
	if (event.url.pathname.startsWith('/api/workflows/hooks/')) {
		return resolve(event);
	}

	// No route matched: the 404 page needs no session, CSRF or locale, and without
	// this each unmatched path costs two backend round-trips. route.id is set by now.
	if (!event.route.id) {
		event.locals.featureFlags = loadFeatureFlags();
		// %lang% is an unescaped HTML attribute and LOCALE is not httpOnly, so the
		// cookie must be validated here the way paraglide would on the normal path.
		const locale = toLocale(event.cookies.get('LOCALE')) ?? DEFAULT_LANGUAGE;
		return resolve(event, {
			transformPageChunk: ({ html }) => html.replace('%lang%', locale).replace('%theme%', '')
		});
	}

	const localeForRequest = await ensureDefaultLocale(event);
	fallbackLocaleStore.set(event.request, localeForRequest);

	return paraglideMiddleware(event.request, async ({ request: localizedRequest, locale }) => {
		event.request = localizedRequest;

		event.locals.featureFlags = loadFeatureFlags();

		await ensureCsrfToken(event);

		const errorId = new URL(event.request.url).searchParams.get('error');
		if (errorId) {
			setFlash({ type: 'error', message: safeTranslate(errorId) }, event);
			redirect(302, '/login');
		}

		// Skip session validation for SSO authenticate route — the token cookie
		// has just been set by the backend but the allauth session token hasn't
		// been fetched yet; that happens in the page's load function.
		const isSSOAuthenticate = event.url.pathname.endsWith('/sso/authenticate');

		// On demand: the endpoint routes that only proxy a query read none of these.
		event.locals.getUser = memoize(async () => {
			if (isSSOAuthenticate) return null;
			const user = await validateUserSession(event);
			if (user) {
				event.locals.user = user;
				applyUserLocale(event, user);
			}
			return user;
		});

		// Token-gated, not getUser()-gated: a flag lookup must not pull in current-user.
		const authorized = () => {
			const token = event.cookies.get('token');
			return token
				? { 'content-type': 'application/json', Authorization: `Token ${token}` }
				: undefined;
		};

		event.locals.getSettings = memoize(async () => {
			const headers = authorized();
			if (!headers) return undefined;
			const generalSettings = await fetch(`${BASE_API_URL}/settings/general/object/`, {
				credentials: 'include',
				headers
			});
			if (!generalSettings.ok) {
				logger.error('Error fetching general settings', { status: generalSettings.status });
				error(503, 'Settings unavailable');
			}
			event.locals.settings = await generalSettings.json();
			setUseRiskCategoryLabel(event.locals.settings?.use_risk_category_label);
			return event.locals.settings;
		});

		event.locals.getFeatureFlags = memoize(async () => {
			const headers = authorized();
			if (!headers) return undefined;
			try {
				// `effective`, not the raw row: the raw row stays the admin form's
				// source, and it PUTs the whole body back.
				const featureFlagSettings = await fetch(
					`${BASE_API_URL}/settings/feature-flags/effective/`,
					{
						credentials: 'include',
						headers
					}
				);
				if (!featureFlagSettings.ok) throw new Error(`status ${featureFlagSettings.status}`);
				event.locals.featureflags = (await featureFlagSettings.json()).flags;
			} catch (e) {
				logger.error('Error fetching feature flags', { error: e });
				event.locals.featureflags = {};
			}
			return event.locals.featureflags;
		});

		return await resolve(event, {
			transformPageChunk: ({ html }) => {
				return html
					.replace('%lang%', locale)
					.replace('%theme%', event.locals.user?.preferences?.ui?.theme ?? '');
			}
		});
	});
};

export const handle: Handle = sequence(noStoreForFeApi, handleRequest);

// Replaces SvelteKit's default error logger, which printed every unmatched path
// as a two-line stderr entry. A 404 on a path that was never a route is not an
// application error: vulnerability scanners alone can produce tens of thousands
// of those lines. Real failures still go out through the structured logger.
export const handleError: HandleServerError = ({ error, status, message, event }) => {
	if (status !== 404) {
		// The global Error type does not declare Node's syscall code.
		const errno = (e: Error) => (e as NodeJS.ErrnoException).code;
		// `TypeError: fetch failed` serializes to just that: undici puts the
		// reason on `cause`, and the stack says which call made it.
		const cause = error instanceof Error ? error.cause : undefined;
		logger.error('unhandled_server_error', {
			status,
			method: event.request.method,
			path: event.url.pathname,
			error,
			cause:
				cause instanceof Error
					? `${cause.name}: ${cause.message}${errno(cause) ? ` (${errno(cause)})` : ''}`
					: cause,
			stack: error instanceof Error ? error.stack : undefined
		});
	}
	return { message };
};

export const handleFetch: HandleFetch = async ({ request, fetch, event }) => {
	const unsafeMethods = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
	// Not awaiting getUser(): the LOCALE cookie carries the same preference.
	const currentLang =
		event.locals.user?.preferences?.lang || event.cookies.get('LOCALE') || DEFAULT_LANGUAGE;
	if (request.url.startsWith(BASE_API_URL)) {
		// Default to JSON unless the request is already a multipart upload (FormData)
		const ct = request.headers.get('Content-Type') || '';
		if (!ct.includes('multipart')) {
			request.headers.set('Content-Type', 'application/json');
		}
		request.headers.set('Accept-Language', currentLang);

		const token = event.cookies.get('token');
		const csrfToken = event.cookies.get('csrftoken');

		if (token) {
			request.headers.append('Authorization', `Token ${token}`);
		}

		// FocusModeMiddleware re-checks the flag and drops the header when it is off,
		// so gating here would only cost a feature-flag round-trip per proxied call.
		const focusFolderId = event.cookies.get('focus_folder_id');
		if (focusFolderId) {
			request.headers.set('X-Focus-Folder-Id', focusFolderId);
		}
		if (unsafeMethods.has(request.method) && csrfToken) {
			request.headers.append('X-CSRFToken', csrfToken);
			request.headers.append('Cookie', `csrftoken=${csrfToken}`);
		}
	}

	if (request.url.startsWith(`${BASE_API_URL}/_allauth/app`)) {
		const allauthSessionToken = event.cookies.get('allauth_session_token');
		if (allauthSessionToken) {
			request.headers.append('X-Session-Token', allauthSessionToken);
		}
		const response = await fetch(request);
		const clonedResponse = response.clone();

		// Session is invalid
		if (clonedResponse.status === 410) logoutUser(event);

		// Skip 401 interception for auth endpoints (/auth/login, /auth/2fa/authenticate, etc.)
		// because 401 is an expected response during login/MFA flows (e.g. "MFA required").
		// Only intercept 401 on account management endpoints (/account/...).
		const isAuthEndpoint = request.url.includes('/_allauth/app/v1/auth/');

		if (clonedResponse.status === 401 && request.method !== 'DELETE' && !isAuthEndpoint) {
			try {
				const data = await clonedResponse.json();
				const reauthenticationFlows = ['reauthenticate', 'mfa_reauthenticate'];

				if (!data.meta?.is_authenticated) {
					// Allauth session has fully expired — force logout
					logoutUser(event);
				} else if (
					data.data?.flows?.some((flow: Record<string, any>) =>
						reauthenticationFlows.includes(flow.id)
					)
				) {
					// locals.user is unset here: a form action runs before any load.
					// Only a positively identified local account is signed out, so
					// that they can re-enter their password; a lookup that fails
					// says nothing, and an SSO logout costs a full IdP round-trip.
					let user: User | null = null;
					try {
						user = await event.locals.getUser();
					} catch (lookupError) {
						if (isRedirect(lookupError)) throw lookupError;
						logger.error('Could not resolve the current user on a 401', {
							error: lookupError
						});
					}
					if (user && !user.is_sso) {
						setFlash(
							{ type: 'warning', message: safeTranslate('reauthenticateForSensitiveAction') },
							event
						);
						logoutUser(event);
					}
				}
			} catch {
				// Malformed response — force logout to be safe
				logoutUser(event);
			}
		}

		return response;
	}

	return fetch(request);
};
