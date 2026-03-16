/**
 * Thin fetch wrapper for builder CRUD calls to the +server.ts proxy.
 * All calls go to /frameworks/{frameworkId}/builder/ which proxies to Django.
 */

type BuilderFetch = typeof globalThis.fetch;

let _fetch: BuilderFetch = globalThis.fetch;
let _frameworkId = '';

export function initBuilderApi(fetchFn: BuilderFetch, frameworkId: string) {
	_fetch = fetchFn;
	_frameworkId = frameworkId;
}

function baseUrl() {
	return `/frameworks/${_frameworkId}/builder`;
}

export async function apiCreate(endpoint: string, payload: Record<string, unknown>) {
	const res = await _fetch(baseUrl(), {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ endpoint, payload })
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: 'Request failed' }));
		throw new Error(err.detail ?? JSON.stringify(err));
	}
	return res.json();
}

export async function apiUpdate(endpoint: string, id: string, payload: Record<string, unknown>) {
	const res = await _fetch(baseUrl(), {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ endpoint, id, payload })
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: 'Request failed' }));
		throw new Error(err.detail ?? JSON.stringify(err));
	}
	return res.json();
}

export async function apiDelete(endpoint: string, id: string) {
	const res = await _fetch(baseUrl(), {
		method: 'DELETE',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ endpoint, id })
	});
	if (!res.ok && res.status !== 204) {
		const err = await res.json().catch(() => ({ detail: 'Request failed' }));
		throw new Error(err.detail ?? JSON.stringify(err));
	}
}
