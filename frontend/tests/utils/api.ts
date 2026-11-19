import type { BrowserContext } from '@playwright/test';

export const BACKEND_API_URL = process.env.PUBLIC_BACKEND_API_URL ?? 'http://localhost:8000/api';

/** Returns the auth token the frontend stored after login, for direct backend API calls. */
export async function getAuthToken(context: BrowserContext): Promise<string> {
	const cookies = await context.cookies();
	const token = cookies.find((c) => c.name === 'token')?.value;
	if (!token) throw new Error('No `token` cookie found: is the user logged in?');
	return token;
}
