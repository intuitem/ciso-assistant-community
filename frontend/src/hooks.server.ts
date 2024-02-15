import { BASE_API_URL } from '$lib/utils/constants';
import type { User } from '$lib/utils/types';
import { redirect, type Handle, type HandleFetch } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
	const session = event.cookies.get('sessionid');

	let csrfToken = event.cookies.get('csrftoken');
	if (!csrfToken) {
		csrfToken = await fetch(`${BASE_API_URL}/csrf/`, {
			credentials: 'include',
			headers: {
				'content-type': 'application/json'
			}
		})
			.then((res) => res.json())
			.then((res) => res.csrfToken);
	}
	event.cookies.set('csrftoken', csrfToken!, {
		httpOnly: false,
		sameSite: 'lax',
		path: '/',
		secure: true
	});

	if (event.locals.user) {
		// There is already a logged-in user. Load page as normal.
		return await resolve(event);
	}

	if (!session) {
		// There is no session, so no logged-in user. Load page as normal.
		return await resolve(event);
	}

	// Fetch the user corresponding to the session.
	const res = await fetch(`${BASE_API_URL}/iam/current-user/`, {
		credentials: 'include',
		headers: {
			'content-type': 'application/json',
			Cookie: `sessionid=${session}`
		}
	});

	if (!res.ok) {
		// The session is invalid. Delete the session cookie and redirect to the login page.
		event.cookies.delete('sessionid', {
			path: '/',
			secure: true,
			sameSite: 'lax'
		});
		redirect(302, `/login?next=${event.url.pathname}`);
	}

	// User exists, set `events.locals.user` and load page.
	const response: User = (await res.json()) as User;
	event.locals.user = response;

	return await resolve(event);
};

export const handleFetch: HandleFetch = async ({ request, fetch, event: { cookies } }) => {
	const unsafeMethods = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

	if (request.url.startsWith(BASE_API_URL)) {
		request.headers.set('Content-Type', 'application/json');

		const sessionid = cookies.get('sessionid');
		const csrfToken = cookies.get('csrftoken');

		if (sessionid) {
			request.headers.append('Cookie', `sessionid=${sessionid}`);
		}

		if (unsafeMethods.has(request.method) && csrfToken) {
			request.headers.append('X-CSRFToken', csrfToken);
			request.headers.append('Cookie', `csrftoken=${csrfToken}`);
		}
	}

	return fetch(request);
};
