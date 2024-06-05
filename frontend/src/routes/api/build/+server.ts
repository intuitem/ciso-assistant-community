import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch }) => {
	interface BuildInfo {
		version: string;
		build: string;
	}

	const endpoint = `${BASE_API_URL}/build/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching buld info');
	}

	const build: BuildInfo = await res.json();

	return new Response(JSON.stringify(build), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
