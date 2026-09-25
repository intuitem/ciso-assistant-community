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
