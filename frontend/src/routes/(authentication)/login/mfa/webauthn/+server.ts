import { ALLAUTH_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${ALLAUTH_API_URL}/auth/webauthn/authenticate`;

	let response;
	try {
		response = await fetch(endpoint);
	} catch {
		return json({ error: 'Could not reach authentication server' }, { status: 502 });
	}

	if (!response.ok) {
		return json({ error: 'Could not get WebAuthn challenge' }, { status: response.status });
	}

	let data;
	try {
		data = await response.json();
	} catch {
		return json({ error: 'Invalid response from authentication server' }, { status: 502 });
	}

	return json(data);
};
