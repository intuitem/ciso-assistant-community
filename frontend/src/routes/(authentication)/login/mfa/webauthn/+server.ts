import { ALLAUTH_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${ALLAUTH_API_URL}/auth/webauthn/authenticate`;
	const response = await fetch(endpoint);
	const data = await response.json();

	if (data.status !== 200) {
		return json({ error: 'Could not get WebAuthn challenge' }, { status: data.status });
	}

	return json(data);
};
