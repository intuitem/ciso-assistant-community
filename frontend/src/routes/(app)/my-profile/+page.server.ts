import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import { redirect } from '@sveltejs/kit';

export const load = async ({ fetch, locals, url }) => {
	// Layout and page loads run concurrently, so the layout's redirect does not
	// stop this one from starting.
	const user = await locals.getUser();
	if (!user) redirect(302, `/login?next=${url.pathname}`);

	const res = await fetch(`${BASE_API_URL}/users/${user.id}/`, { credentials: 'include' })
		.then((r) => r.json())
		.catch((e) => {
			console.error('Error fetching user data:', e);
			return null;
		});

	// Teams are their own endpoint rather than a field on the user: membership is three
	// relations, and putting them on UserReadSerializer would N+1 the users list.
	const teams = await fetch(`${BASE_API_URL}/users/${user.id}/teams/`, {
		credentials: 'include'
	})
		.then((r) => (r.ok ? r.json() : []))
		.catch((e) => {
			console.error('Error fetching user teams:', e);
			return [];
		});

	return {
		currentUser: res,
		teams,
		title: m.myProfile()
	};
};
