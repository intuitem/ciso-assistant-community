import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';
import { readFileSync } from 'fs';
import path from 'path';

const faviconPath = path.resolve(process.cwd(), 'src/lib/assets/favicon.ico');

export const GET: RequestHandler = async ({ fetch }) => {
	try {
		const endpoint = `${BASE_API_URL}/client-settings/favicon/`;
		const res = await fetch(endpoint);

		if (!res.ok) {
			const fileBuffer = readFileSync(faviconPath);

			return new Response(fileBuffer, {
				headers: {
					'Content-Type': 'image/x-icon'
				}
			});
		}

		const response = await res.json();
		const binaryData = Uint8Array.from(atob(response.data), (c) => c.charCodeAt(0));

		return new Response(binaryData, {
			headers: {
				'Content-Type': response.mime_type
			}
		});
	} catch (error) {
		const fileBuffer = readFileSync(faviconPath);

		return new Response(fileBuffer, {
			headers: {
				'Content-Type': 'image/x-icon'
			}
		});
	}
};
