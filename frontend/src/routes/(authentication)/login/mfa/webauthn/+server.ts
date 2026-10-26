import { ALLAUTH_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${ALLAUTH_API_URL}/auth/webauthn/authenticate`;

	let response;
	try {
		response = await fetch(endpoint);
	} catch {
		return Response.json({ error: 'Could not reach authentication server' }, { status: 502 });
	}

	if (!response.ok) {
		return Response.json(
			{ error: 'Could not get WebAuthn challenge' },
			{ status: response.status }
		);
	}

	let data;
	try {
		data = await response.json();
	} catch {
		return Response.json({ error: 'Invalid response from authentication server' }, { status: 502 });
	}

	return Response.json(data);
};
