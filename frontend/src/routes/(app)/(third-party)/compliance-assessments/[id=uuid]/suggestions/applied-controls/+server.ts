import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

async function proxyRequest(event: Parameters<RequestHandler>[0], init: RequestInit, query = '') {
	const endpoint = `${BASE_API_URL}/compliance-assessments/${event.params.id}/suggestions/applied-controls/${query}`;
	const res = await event.fetch(endpoint, init);

	if (!res.ok) {
		const response = await res.json();
		console.error(response);
		return new Response(JSON.stringify(response), {
			status: res.status,
			headers: {
				'Content-Type': 'application/json'
			}
		});
	}

	return new Response(await res.text(), {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
}

export const GET: RequestHandler = async (event) => {
	return proxyRequest(event, { method: 'GET' }, '?dry_run=true');
};

export const POST: RequestHandler = async (event) => {
	return proxyRequest(event, { method: 'POST' });
};
