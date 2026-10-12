import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

// Vitest resolves `svelte` with server export conditions, whose `mount` throws.
// The client entry is what jsdom needs; child imports of `svelte/internal/*` stay put.
vi.mock('svelte', () => import('../../../../node_modules/svelte/src/index-client.js'));

import DocumentCreate from './DocumentCreate.svelte';

function requestUrl(input: RequestInfo | URL): string {
	if (typeof input === 'string') return input;
	if (input instanceof URL) return input.href;
	return input.url;
}

/** Every URL, including FolderTreeSelect's org tree, gets the same stub. */
function stubFetch(ok: boolean) {
	const urls: string[] = [];
	vi.stubGlobal(
		'fetch',
		vi.fn(async (input: RequestInfo | URL) => {
			urls.push(requestUrl(input));
			return {
				ok,
				status: ok ? 200 : 500,
				statusText: ok ? 'OK' : 'Error',
				json: async () => []
			};
		})
	);
	return urls;
}

function classificationUrls(urls: string[]) {
	return urls.filter((url) => url.includes('classification-levels'));
}

/**
 * Both filters are required: `is_visible` drops a hidden level on a visible scheme,
 * and `object_classification__is_visible` drops levels of a hidden scheme (TLP).
 * Either missing fails, including a bare `/classification-levels` URL.
 */
function expectFilteredClassificationRequests(urls: string[]) {
	const hits = classificationUrls(urls);
	expect(hits.length).toBeGreaterThan(0);
	for (const url of hits) {
		const params = new URL(url, 'http://localhost').searchParams;
		expect(params.get('is_visible')).toBe('true');
		expect(params.get('object_classification__is_visible')).toBe('true');
	}
}

afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
	vi.restoreAllMocks();
});

describe('DocumentCreate classification options', () => {
	it('requests only visible levels and keeps the field optional when the list is empty', async () => {
		const urls = stubFetch(true);
		render(DocumentCreate);

		await waitFor(() => {
			expect(classificationUrls(urls).length).toBeGreaterThan(0);
		});
		await new Promise((resolve) => setTimeout(resolve, 0));

		expectFilteredClassificationRequests(urls);
		const classification = screen.getByRole('combobox', { name: 'Classification' });
		expect(classification).toBeInTheDocument();
		expect(classification).not.toBeRequired();
	});

	it('does not retry classification-levels without the visibility filters when the request fails', async () => {
		const urls = stubFetch(false);
		render(DocumentCreate);

		await waitFor(() => {
			expect(classificationUrls(urls).length).toBeGreaterThan(0);
		});
		await new Promise((resolve) => setTimeout(resolve, 0));

		expectFilteredClassificationRequests(urls);
	});
});
