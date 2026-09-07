import { BASE_API_URL } from '$lib/utils/constants';
import type { Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'quick-form-responses';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const [response, content] = await Promise.all([
		fetch(endpoint).then((res) => res.json()),
		fetch(`${endpoint}content/`).then((res) => res.json())
	]);
	return { URLModel, response, content, title: response.name };
}) satisfies PageServerLoad;

export const actions: Actions = {
	updateAnswers: async (event) => {
		const { id, answers } = await event.request.json();
		const res = await event.fetch(`${BASE_API_URL}/quick-form-responses/${id}/`, {
			method: 'PATCH',
			body: JSON.stringify({ answers })
		});
		return { status: res.status, body: await res.json() };
	},
	setStatus: async (event) => {
		const { id, status, observation } = await event.request.json();
		const res = await event.fetch(`${BASE_API_URL}/quick-form-responses/${id}/set-status/`, {
			method: 'POST',
			body: JSON.stringify({ status, observation })
		});
		return { status: res.status, body: await res.json() };
	},
	start: async (event) => {
		const { id } = await event.request.json();
		const res = await event.fetch(`${BASE_API_URL}/quick-form-responses/${id}/start/`, {
			method: 'POST',
			body: JSON.stringify({})
		});
		return { status: res.status, body: await res.json() };
	}
};
