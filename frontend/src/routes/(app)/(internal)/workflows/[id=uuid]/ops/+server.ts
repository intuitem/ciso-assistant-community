// JSON proxy for the workflow builder canvas.
//
// The canvas autosaves the whole graph document and triggers publish /
// new-draft transitions; these are fast JSON mutations that don't fit the
// form-action round-trip (same rationale as the responsibility-matrix editor).

import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function requireUuid(value: unknown, field: string): string {
	if (typeof value !== 'string' || !UUID_RE.test(value)) {
		error(400, `Invalid UUID for "${field}"`);
	}
	return value;
}

async function proxy(
	fetchFn: typeof fetch,
	url: string,
	method: string,
	body?: unknown
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
		// Publish validation failures carry a structured `errors` list the canvas
		// renders in place; pass them through instead of raising.
		if (res.status === 400) return json(data, { status: 400 });
		error(res.status as NumericRange<400, 599>, data);
	}
	return json(data, { status: res.status });
}

export const POST: RequestHandler = async ({ fetch, request, url }) => {
	const action = url.searchParams.get('action');
	const body = await request.json().catch(() => ({}));

	switch (action) {
		case 'save-graph': {
			const versionId = requireUuid(body.version, 'version');
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-versions/${versionId}/graph/`,
				'PUT',
				body.graph
			);
		}

		case 'publish': {
			const versionId = requireUuid(body.version, 'version');
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-versions/${versionId}/publish/`,
				'POST'
			);
		}

		case 'discard-draft': {
			const versionId = requireUuid(body.version, 'version');
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-versions/${versionId}/discard/`,
				'POST'
			);
		}

		case 'new-draft': {
			const versionId = requireUuid(body.version, 'version');
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-versions/${versionId}/new-draft/`,
				'POST'
			);
		}

		case 'get-graph': {
			const versionId = requireUuid(body.version, 'version');
			return proxy(fetch, `${BASE_API_URL}/workflows/workflow-versions/${versionId}/graph/`, 'GET');
		}

		case 'run': {
			const versionId = requireUuid(body.version, 'version');
			const payload: Record<string, unknown> = { version: versionId };
			if (typeof body.entry_node_ref === 'string' && body.entry_node_ref) {
				payload.entry_node_ref = body.entry_node_ref;
			}
			return proxy(fetch, `${BASE_API_URL}/workflows/workflow-instances/`, 'POST', payload);
		}

		case 'list-instances': {
			const workflowId = requireUuid(body.workflow, 'workflow');
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-instances/?workflow=${workflowId}`,
				'GET'
			);
		}

		case 'list-secrets': {
			return proxy(fetch, `${BASE_API_URL}/workflows/workflow-secrets/`, 'GET');
		}

		case 'create-secret': {
			return proxy(fetch, `${BASE_API_URL}/workflows/workflow-secrets/`, 'POST', {
				name: body.name,
				folder: body.folder,
				value: body.value
			});
		}

		case 'delete-secret': {
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-secrets/${requireUuid(body.id, 'id')}/`,
				'DELETE'
			);
		}

		case 'list-triggers': {
			const workflowId = requireUuid(body.workflow, 'workflow');
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-triggers/?workflow=${workflowId}`,
				'GET'
			);
		}

		case 'toggle-trigger': {
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-triggers/${requireUuid(body.id, 'id')}/`,
				'PATCH',
				{ enabled: !!body.enabled }
			);
		}

		case 'set-trigger-hmac': {
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-triggers/${requireUuid(body.id, 'id')}/`,
				'PATCH',
				{ hmac_secret: typeof body.hmac_secret === 'string' ? body.hmac_secret : '' }
			);
		}

		case 'rotate-trigger-secret': {
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-triggers/${requireUuid(body.id, 'id')}/rotate-secret/`,
				'POST'
			);
		}

		case 'event-keys': {
			return proxy(fetch, `${BASE_API_URL}/workflows/workflow-triggers/event-keys/`, 'GET');
		}

		case 'instance-logs': {
			const instanceId = requireUuid(body.instance, 'instance');
			return proxy(
				fetch,
				`${BASE_API_URL}/workflows/workflow-instances/${instanceId}/logs/`,
				'GET'
			);
		}

		default:
			error(400, `unknown action: ${action}`);
	}
};
