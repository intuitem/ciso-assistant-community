import type { RequestEvent } from '@sveltejs/kit';

// The route ids that have a page, and those that have an endpoint. Only the keys of these
// globs are read: their modules are never imported from here.
function routeIds(files: Record<string, unknown>): ReadonlySet<string> {
	return new Set(
		Object.keys(files).map(
			(file) => file.slice('/src/routes'.length, file.lastIndexOf('/')) || '/'
		)
	);
}

const PAGES = routeIds(
	import.meta.glob([
		'/src/routes/**/+page.svelte',
		'/src/routes/**/+page.ts',
		'/src/routes/**/+page.server.ts'
	])
);
const ENDPOINTS = routeIds(import.meta.glob('/src/routes/**/+server.ts'));

/**
 * Whether SvelteKit will hand this request to a page — to render it, load its data or run
 * one of its form actions — rather than to an endpoint. Follows kit's own dispatch
 * (runtime/server/respond.js), so a check made on it sees what a page load would see.
 */
export function reachesPage(
	event: Pick<RequestEvent, 'route' | 'request' | 'isDataRequest'>
): boolean {
	const id = event.route.id;
	if (!id || !PAGES.has(id)) return false;
	if (event.isDataRequest) return true;
	return !(ENDPOINTS.has(id) && isEndpointRequest(event.request));
}

// kit's `is_endpoint_request` (runtime/server/endpoint.js), for the methods a page answers.
function isEndpointRequest(request: Request): boolean {
	if (!['GET', 'HEAD', 'POST'].includes(request.method)) return true;
	if (request.method === 'POST' && request.headers.get('x-sveltekit-action') === 'true') {
		return false;
	}
	return !prefersHtml(request.headers.get('accept') ?? '*/*');
}

// kit's `negotiate(accept, ['*', 'text/html']) === 'text/html'` (utils/http.js): some part
// accepting html ranks above every `*/*` part.
function prefersHtml(accept: string): boolean {
	const parts = accept.split(',').flatMap((part, i) => {
		const match = /^[ \t]*([^/ \t]+)\/([^; \t]+)[ \t]*(?:;[ \t]*q=([0-9.]+))?/.exec(part);
		return match ? [{ type: match[1], subtype: match[2], q: +(match[3] ?? '1'), i }] : [];
	});
	parts.sort(
		(a, b) =>
			b.q - a.q ||
			Number(a.subtype === '*') - Number(b.subtype === '*') ||
			Number(a.type === '*') - Number(b.type === '*') ||
			a.i - b.i
	);
	const html = parts.findIndex(
		(p) => (p.type === 'text' || p.type === '*') && (p.subtype === 'html' || p.subtype === '*')
	);
	const any = parts.findIndex((p) => p.type === '*' && p.subtype === '*');
	return html !== -1 && (any === -1 || html < any);
}
