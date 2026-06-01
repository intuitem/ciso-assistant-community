// Inline-editor proxy for the matrix detail page.
//
// Most CRUD in this codebase goes through SvelteKit form actions plus
// `nestedWriteFormAction` (see e.g. `risk-assessments/[id]/+page.server.ts`).
// We bypass that here because the matrix-editor UX is built around fast JSON
// mutations (cell-cycle, drag-reorder, inline add) that don't fit the form
// submission round-trip. Each action proxies straight to the backend.

import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function requireUuid(value: unknown, field: string): string {
	if (typeof value !== 'string' || !UUID_RE.test(value)) {
		error(400, { detail: `Invalid UUID for "${field}"` });
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
	if (!res.ok) error(res.status as NumericRange<400, 599>, data);
	return json(data, { status: res.status });
}

export const POST: RequestHandler = async ({ fetch, params, request, url }) => {
	const action = url.searchParams.get('action');
	const matrixId = params.id;
	const body = await request.json().catch(() => ({}));

	switch (action) {
		case 'create-activity':
			return proxy(fetch, `${BASE_API_URL}/pmbok/responsibility-matrix-activities/`, 'POST', {
				matrix: matrixId,
				name: body.name,
				order: body.order ?? 0
			});

		case 'update-activity': {
			const activityId = requireUuid(body.id, 'id');
			// Forward only fields that were explicitly provided so we don't accidentally
			// clear M2Ms that weren't touched.
			const patch: Record<string, unknown> = {};
			for (const k of [
				'name',
				'description',
				'assets',
				'applied_controls',
				'task_templates',
				'risk_assessments',
				'compliance_assessments',
				'findings_assessments',
				'business_impact_analyses'
			]) {
				if (k in body) patch[k] = body[k];
			}
			return proxy(
				fetch,
				`${BASE_API_URL}/pmbok/responsibility-matrix-activities/${activityId}/`,
				'PATCH',
				patch
			);
		}

		case 'delete-activity': {
			const activityId = requireUuid(body.id, 'id');
			return proxy(
				fetch,
				`${BASE_API_URL}/pmbok/responsibility-matrix-activities/${activityId}/`,
				'DELETE'
			);
		}

		case 'create-actor': {
			const actorId = requireUuid(body.actor, 'actor');
			return proxy(fetch, `${BASE_API_URL}/pmbok/responsibility-matrix-actors/`, 'POST', {
				matrix: matrixId,
				actor: actorId,
				order: body.order ?? 0
			});
		}

		case 'delete-actor': {
			const membershipId = requireUuid(body.id, 'id');
			return proxy(
				fetch,
				`${BASE_API_URL}/pmbok/responsibility-matrix-actors/${membershipId}/`,
				'DELETE'
			);
		}

		case 'cycle-cell': {
			const activityId = requireUuid(body.activity, 'activity');
			const actorId = requireUuid(body.actor, 'actor');
			return proxy(
				fetch,
				`${BASE_API_URL}/pmbok/responsibility-matrices/${matrixId}/cycle-cell/`,
				'POST',
				{ activity: activityId, actor: actorId, direction: body.direction }
			);
		}

		case 'reorder-activities':
			return proxy(
				fetch,
				`${BASE_API_URL}/pmbok/responsibility-matrices/${matrixId}/reorder-activities/`,
				'POST',
				{ ids: body.ids }
			);

		case 'reorder-actors':
			return proxy(
				fetch,
				`${BASE_API_URL}/pmbok/responsibility-matrices/${matrixId}/reorder-actors/`,
				'POST',
				{ ids: body.ids }
			);

		default:
			error(400, { detail: `unknown action: ${action}` });
	}
};
