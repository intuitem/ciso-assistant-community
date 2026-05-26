import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/**
 * Lightweight POST proxy for AgentAction approve/reject/bulk-approve,
 * plus run-level controls (cancel, start-wave2). Routes the call into the
 * chat API so the page can call this same path for any op without needing
 * per-action routes.
 *
 * Body shapes:
 *   { op: 'approve', actionId, payload? }
 *   { op: 'reject',  actionId }
 *   { op: 'bulk-approve', minConfidence, kinds? }
 *   { op: 'bulk-reject', kinds? }
 *   { op: 'start-wave2' }
 *   { op: 'cancel' }
 */
export const POST: RequestHandler = async ({ request, params, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const op = body?.op;

	const post = (url: string, payload: any) =>
		fetch(`${BASE_API_URL}${url}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

	let response: Response;
	if (op === 'approve') {
		if (!body.actionId) {
			return json({ detail: 'actionId is required.' }, { status: 400 });
		}
		response = await post(`/chat/agent-actions/${body.actionId}/approve/`, {
			payload: body.payload ?? null
		});
	} else if (op === 'reject') {
		if (!body.actionId) {
			return json({ detail: 'actionId is required.' }, { status: 400 });
		}
		response = await post(`/chat/agent-actions/${body.actionId}/reject/`, {});
	} else if (op === 'bulk-approve') {
		response = await post(`/chat/agent-actions/bulk-approve/`, {
			agent_run: params.id,
			min_confidence: body.minConfidence ?? 0.7,
			kinds: body.kinds ?? undefined
		});
	} else if (op === 'bulk-reject') {
		response = await post(`/chat/agent-actions/bulk-reject/`, {
			agent_run: params.id,
			kinds: body.kinds ?? undefined
		});
	} else if (op === 'start-wave2') {
		response = await post(`/chat/agent-runs/${params.id}/start-audit-prefill-wave2/`, {
			skip_not_applicable: body.skip_not_applicable ?? true
		});
	} else if (op === 'cancel') {
		response = await post(`/chat/agent-runs/${params.id}/cancel/`, {});
	} else {
		return json({ detail: `Unknown op: ${op}` }, { status: 400 });
	}

	const data = await response.json().catch(() => ({}));
	return json(data, { status: response.status });
};

export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/chat/agent-runs/${params.id}/`, {
		method: 'DELETE'
	});
	if (res.status === 204) {
		return new Response(null, { status: 204 });
	}
	const data = await res.json().catch(() => ({}));
	return json(data, { status: res.status });
};
