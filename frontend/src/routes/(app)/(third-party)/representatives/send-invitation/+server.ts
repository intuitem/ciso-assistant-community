import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';


export const POST: RequestHandler = async (event) => {
	const form = await event.request.formData();
	const raw = form.get('__superform_json');
	if (typeof raw !== 'string') {
		return new Response(JSON.stringify({ error: 'invalidFormPayload' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	let parsed: unknown;
	try {
		parsed = JSON.parse(raw);
	} catch {
		return new Response(JSON.stringify({ error: 'invalidJsonPayload' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

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

	if (!email) {
		return new Response(JSON.stringify({ error: 'emailRequired' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const res = await fetch(`${BASE_API_URL}/iam/send-invitation/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email: email })
	});

	const text = await res.text();
	return new Response(text || null, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
};
