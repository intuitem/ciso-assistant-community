import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async (event) => {
	const requestInitOptions: RequestInit = {
		method: 'POST'
	};
	const form = await event.request.formData();
	const raw = form.get('__superform_json') as string;

	let parsed = JSON.parse(raw);

	let email: string | undefined;

	if (Array.isArray(parsed)) {
		const mapping = parsed[0];
		if (mapping && typeof mapping === 'object' && typeof mapping.email === 'number') {
			const emailIndex = mapping.email;
			email = parsed[emailIndex];
		} else {
			email = parsed.find((v: any) => typeof v === 'string' && v.includes('@'));
		}
	} else if (parsed && typeof parsed === 'object') {
		email = parsed.email ?? parsed['__email'] ?? undefined;
	}

	const res = await fetch(`${BASE_API_URL}/iam/send-invitation/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email: email })
	});
	return new Response(null, {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
