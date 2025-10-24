import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/accounts/saml/0/download-cert`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the cert');
	}

	const cert = await res.text();

	return new Response(cert, {
		headers: {
			'Content-Type': 'application/x-pem-file',
			'Content-Disposition': 'attachment; filename="saml-public-cert.pem"'
		}
	});
};
