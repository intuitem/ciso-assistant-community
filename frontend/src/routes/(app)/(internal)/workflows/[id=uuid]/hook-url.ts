import { env } from '$env/dynamic/public';

// Public URL of a webhook trigger. Hooks are served through the
// frontend origin (passthrough at /api/workflows/hooks/, short-circuited by
// proxies that route /api/* straight to the backend), so the browser's own
// origin is correct with zero configuration. PUBLIC_HOOKS_URL overrides it
// for split-horizon deployments where admins browse an internal URL but
// senders must hit a public one.
export function publicHookUrl(workflowId: string, nodeRef: string, secret: string): string {
	// `location` only exists in the browser; SSR gets a relative URL instead
	// of a crash (registrations load client-side, so this never renders there).
	const base =
		env.PUBLIC_HOOKS_URL?.replace(/\/$/, '') ||
		(typeof location === 'undefined' ? '' : location.origin);
	return `${base}/api/workflows/hooks/${workflowId}/${nodeRef}/${secret}/`;
}

// The URL credential is change-gated server-side (it authorizes inbound
// deliveries), so it never rides on the trigger read serializer. Returns
// null when the caller may not see it — hide the URL then.
export async function fetchHookSecret(
	workflowId: string,
	triggerId: string
): Promise<string | null> {
	const res = await fetch(`/workflows/${workflowId}/ops?action=trigger-hook-secret`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ id: triggerId })
	});
	if (!res.ok) return null;
	const body = await res.json().catch(() => ({}));
	return typeof body.secret === 'string' ? body.secret : null;
}
