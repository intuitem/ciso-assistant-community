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

	return {
		currentUser: res,
		title: m.myProfile()
	};
};
