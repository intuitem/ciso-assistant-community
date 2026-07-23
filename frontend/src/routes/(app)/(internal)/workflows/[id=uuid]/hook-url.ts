import { env } from '$env/dynamic/public';

// Public URL of a webhook trigger (spec D23). Hooks are served through the
// frontend origin (passthrough at /api/workflows/hooks/, short-circuited by
// proxies that route /api/* straight to the backend), so the browser's own
// origin is correct with zero configuration. PUBLIC_HOOKS_URL overrides it
// for split-horizon deployments where admins browse an internal URL but
// senders must hit a public one.
export function publicHookUrl(workflowId: string, nodeRef: string, secret: string): string {
	const base = env.PUBLIC_HOOKS_URL?.replace(/\/$/, '') || location.origin;
	return `${base}/api/workflows/hooks/${workflowId}/${nodeRef}/${secret}/`;
}
