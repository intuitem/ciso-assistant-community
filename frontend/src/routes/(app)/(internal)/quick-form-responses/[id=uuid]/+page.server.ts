import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// A requester who filed through a publication holds no role on the domain their
// response landed in, so the reviewer endpoints 403 them out of their own request.
// Every call falls back to the audience-scoped surface, which authorises on
// respondent membership. One page, two backends, the choice made in one place.
const withFallback = async (
	fetch: typeof globalThis.fetch,
	primary: string,
	fallback: string,
	init?: RequestInit
) => {
	const res = await fetch(primary, init);
	if (res.status !== 403 && res.status !== 404) return { res, ownSurface: false };
	return { res: await fetch(fallback, init), ownSurface: true };
};

export const load = (async ({ fetch, params }) => {
	const own = `${BASE_API_URL}/my-requests/${params.id}/`;
	const reviewer = `${BASE_API_URL}/quick-form-responses/${params.id}/`;
	const [responseRes, contentRes] = await Promise.all([
		withFallback(fetch, reviewer, own),
		withFallback(fetch, `${reviewer}content/`, `${own}content/`)
	]);
	if (!responseRes.res.ok) error(responseRes.res.status === 404 ? 404 : 403, 'Request not found');
	const response = await responseRes.res.json();
	// Supervised actions are a reviewer's affordance; a requester's call 403s and the
	// list is simply empty for them.
	const actionsRes = await fetch(`${reviewer}suggested-actions/`);
	return {
		suggestedActions: actionsRes.ok ? await actionsRes.json() : [],
		URLModel: 'quick-form-responses',
		response,
		content: await contentRes.res.json(),
		// True when the reviewer surface refused and the requester's own served it:
		// the viewer is here as the person who filed this, not as its reviewer.
		viewerIsRequester: responseRes.ownSurface,
		title: response.name
	};
}) satisfies PageServerLoad;

const json = (body: unknown) => ({
	method: 'POST',
	headers: { 'Content-Type': 'application/json' },
	body: JSON.stringify(body)
});

export const actions: Actions = {
	updateAnswers: async (event) => {
		const { id, answers } = await event.request.json();
		const { res } = await withFallback(
			event.fetch,
			`${BASE_API_URL}/quick-form-responses/${id}/`,
			`${BASE_API_URL}/my-requests/${id}/answers/`,
			{
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ answers })
			}
		);
		return { status: res.status, body: await res.json() };
	},
	setStatus: async (event) => {
		const { id, status, observation, resolution } = await event.request.json();
		// The requester's only transition is submit; every other one is the reviewer's.
		const fallback =
			status === 'submitted'
				? `${BASE_API_URL}/my-requests/${id}/submit/`
				: `${BASE_API_URL}/quick-form-responses/${id}/set-status/`;
		const { res } = await withFallback(
			event.fetch,
			`${BASE_API_URL}/quick-form-responses/${id}/set-status/`,
			fallback,
			json({ status, observation, resolution })
		);
		return { status: res.status, body: await res.json() };
	},
	drop: async (event) => {
		const { id, observation } = await event.request.json();
		const res = await event.fetch(`${BASE_API_URL}/my-requests/${id}/drop/`, json({ observation }));
		return { status: res.status, body: await res.json() };
	},
	clone: async (event) => {
		const { id } = await event.request.json();
		const res = await event.fetch(`${BASE_API_URL}/my-requests/${id}/clone/`, json({}));
		return { status: res.status, body: await res.json() };
	},
	// Multipart has to be consumed and rebuilt: forwarding the raw stream loses the
	// boundary. handleFetch already exempts multipart from its JSON Content-Type.
	uploadAttachment: async (event) => {
		const incoming = await event.request.formData();
		const body = new FormData();
		body.append('question', String(incoming.get('question') ?? ''));
		body.append('file', incoming.get('file') as File);
		const id = String(incoming.get('id') ?? '');
		const { res } = await withFallback(
			event.fetch,
			`${BASE_API_URL}/quick-form-responses/${id}/attachments/`,
			`${BASE_API_URL}/my-requests/${id}/attachments/`,
			{ method: 'POST', body }
		);
		return { status: res.status, body: await res.json() };
	},
	removeAttachment: async (event) => {
		const { id, attachmentId } = await event.request.json();
		const { res } = await withFallback(
			event.fetch,
			`${BASE_API_URL}/quick-form-responses/${id}/attachments/${attachmentId}/`,
			`${BASE_API_URL}/my-requests/${id}/attachments/${attachmentId}/`,
			{ method: 'DELETE' }
		);
		return { status: res.status, body: res.status === 204 ? null : await res.json() };
	},
	runAction: async (event) => {
		const { id, version } = await event.request.json();
		const res = await event.fetch(
			`${BASE_API_URL}/quick-form-responses/${id}/run-action/`,
			json({ version })
		);
		return { status: res.status, body: await res.json() };
	}
};
