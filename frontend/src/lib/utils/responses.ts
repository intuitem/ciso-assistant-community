/**
 * Release the body of responses that will not be read.
 *
 * An unread body over undici's highWaterMark pauses its parser; if the backend then
 * closes the socket (gunicorn sync workers always do), undici throws an uncatchable
 * `assert(!this.paused)` and the whole Node process exits (nodejs/undici#5360, #4903).
 */
export async function discardBody(...responses: (Response | null | undefined)[]): Promise<void> {
	await Promise.all(responses.map((res) => res?.body?.cancel().catch(() => {})));
}

const NULL_BODY_STATUSES = new Set([101, 204, 205, 304]);

/**
 * Read a JSON response off the socket at once and hand back an in-memory copy, so no
 * caller can leave it paused on a closing connection. Streams and files pass through.
 */
export async function bufferJsonResponse(res: Response): Promise<Response> {
	if (!res.body || NULL_BODY_STATUSES.has(res.status)) return res;
	if (!res.headers.get('content-type')?.includes('application/json')) return res;
	const body = await res.arrayBuffer();
	return new Response(body, {
		status: res.status,
		statusText: res.statusText,
		headers: res.headers
	});
}
