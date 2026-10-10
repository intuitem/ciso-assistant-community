import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';

export const POST: RequestHandler = async ({ params, request, fetch, locals }) => {
	const { id } = params;

	// Parse the incoming RPC payload
	let body;
	try {
		body = await request.json();
	} catch (e) {
		return error(400, 'Invalid JSON body');
	}

	const { action, params: rpcParams } = body;

	if (!action) {
		return error(400, 'RPC "action" is required');
	}

	// 2. Construct the Django Backend URL
	const backendUrl = `${BASE_API_URL}/integrations/configs/${id}/rpc/`;

	try {
		// Forward request to Django
		const response = await fetch(backendUrl, {
			method: 'POST',
			body: JSON.stringify({
				action,
				params: rpcParams || {}
			})
		});

		const data = await response.json();

		if (!response.ok) {
			console.error(`RPC Proxy Error [${action}]:`, data);
			// Forward the specific error message from the orchestrator if available
			return error(response.status, data.error || 'Upstream RPC failure');
		}

		return json(data);
	} catch (err) {
		console.error('RPC Network Error:', err);
		return error(502, 'Failed to reach integration backend');
	}
};
