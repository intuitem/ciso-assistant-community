import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';

export const load = async ({ fetch, locals }) => {
	const res = await fetch(`${BASE_API_URL}/users/${locals.user.id}/`, { credentials: 'include' })
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
