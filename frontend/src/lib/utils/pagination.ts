/**
 * Helpers for consuming the backend's paginated list endpoints.
 *
 * Every list endpoint returns a `{count, next, previous, results}` envelope
 * and never more than PAGINATE_MAX rows per response, so a single GET only
 * ever yields the first page. Any consumer that semantically needs the whole
 * collection must page through it.
 */

/** Request the server's hard ceiling (PAGINATE_MAX default) per page — the
 * server clamps anything higher, so this stays correct if the ceiling moves,
 * and cuts round-trips 4× versus the 50-row default page size. */
const MAX_PAGE_SIZE = 200;

interface FetchAllPagesOptions {
	/** Explicit page size (default MAX_PAGE_SIZE). */
	pageSize?: number;
	/** Abort guard against runaway loops (default 1000 pages). */
	maxPages?: number;
}

function withPageParams(url: string, offset: number, limit?: number): string {
	const params = new URLSearchParams();
	if (offset > 0) params.set('offset', String(offset));
	if (limit) params.set('limit', String(limit));
	const qs = params.toString();
	if (!qs) return url;
	return `${url}${url.includes('?') ? '&' : '?'}${qs}`;
}

/**
 * Fetch every page of a paginated list endpoint and return the concatenated
 * results. Pages by explicit offset (not the `next` URL) so it works both
 * server-side against BASE_API_URL and client-side through the SvelteKit
 * proxy routes. Non-paginated responses (plain arrays) are returned as-is.
 *
 * The url must not already carry limit/offset params. Rows created or deleted
 * while paging can still shift across page boundaries (inherent to offset
 * pagination) — callers needing a transactional snapshot should use a
 * dedicated export endpoint instead.
 */
export async function fetchAllPages<T = Record<string, any>>(
	fetchFn: typeof fetch,
	url: string,
	{ pageSize = MAX_PAGE_SIZE, maxPages = 1000 }: FetchAllPagesOptions = {}
): Promise<T[]> {
	const results: T[] = [];
	let offset = 0;
	for (let page = 0; page < maxPages; page++) {
		const res = await fetchFn(withPageParams(url, offset, pageSize));
		if (!res.ok) {
			const err = new Error(
				`fetchAllPages: ${res.status} ${res.statusText} for ${url}`
			) as Error & { status: number };
			err.status = res.status;
			throw err;
		}
		const data = await res.json();
		if (Array.isArray(data)) {
			// Non-paginated endpoint — nothing to page through.
			results.push(...data);
			return results;
		}
		const rows: T[] = data.results ?? [];
		results.push(...rows);
		offset += rows.length;
		if (!data.next || rows.length === 0) {
			return results;
		}
	}
	console.error(`fetchAllPages: aborted after ${maxPages} pages for ${url}`);
	return results;
}
