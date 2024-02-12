import { BASE_API_URL } from '$lib/utils/constants';

async function getCsrfToken() {
	try {
		const response = await fetch(`${BASE_API_URL}/csrf/`, {
			credentials: 'include'
		}).then((res) => res.json());
		return response.csrfToken;
	} catch (error) {
		console.error(error);
	}
}

export const csrfToken = await getCsrfToken();
