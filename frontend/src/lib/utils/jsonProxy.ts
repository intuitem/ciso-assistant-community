// Shared JSON proxy for the inline editors (workflow canvas, responsibility
// matrix) that bypass form actions for fast JSON mutations. One implementation
// of the request/response plumbing; each route keeps its own thin wrapper and
// UUID error shape.
import { json, error, type NumericRange } from '@sveltejs/kit';

export const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Proxy a JSON request to the backend: forward JSON bodies, short-circuit 204,
// and map backend errors to SvelteKit errors. With `passThrough400`, structured
// 400 payloads are returned as-is (the canvas renders publish-validation errors
// in place instead of raising).
export async function proxyJson(
	fetchFn: typeof fetch,
	url: string,
	method: string,
	body?: unknown,
	{ passThrough400 = false }: { passThrough400?: boolean } = {}
): Promise<Response> {
	const opts: RequestInit = {
		method,
		headers: { 'Content-Type': 'application/json' }
	};
	if (body !== undefined) opts.body = JSON.stringify(body);
	const res = await fetchFn(url, opts);
	if (res.status === 204) return new Response(null, { status: 204 });
	const data = await res.json().catch(() => ({}));
	if (!res.ok) {
		if (passThrough400 && res.status === 400) return json(data, { status: 400 });
		error(res.status as NumericRange<400, 599>, data);
	}
	return json(data, { status: res.status });
}
