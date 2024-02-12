import { BASE_API_URL } from '$lib/utils/constants';
import type { User } from '$lib/utils/types';
import { redirect, type Handle, type HandleFetch } from '@sveltejs/kit';

const LOGIN_REQUIRED_ROUTING_GROUP = new Set(['app']); // List of route group that require login to be accessed
const ROUTE_GROUP_REGEX = /^\([a-zA-Z0-9_]+\)/;

export const handle: Handle = async ({ event, resolve }) => {
	const route: string | null = event.route.id;
	let group = null;

	const session = event.cookies.get('sessionid');

	if (route) {
		group = route.substring(1).match(ROUTE_GROUP_REGEX)?.[0];
		group = group?.substring(1, group.length - 1);
	}
	if (!session && group && LOGIN_REQUIRED_ROUTING_GROUP.has(group)) {
		redirect(302, `/login?next=${event.url.pathname}`);
	}

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
		console.log('bad response:', await res.text());
		// The session is invalid. Load page as normal.
		return await resolve(event);
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
