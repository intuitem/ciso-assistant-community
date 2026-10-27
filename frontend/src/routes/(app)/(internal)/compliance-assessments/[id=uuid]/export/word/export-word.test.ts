import { isHttpError } from '@sveltejs/kit';
import { describe, expect, it } from 'vitest';
import { m } from '$paraglide/messages';
import { GET } from './+server';

async function exportError(
	body: unknown,
	status = 400
): Promise<{ status: number; message: string } | undefined> {
	const fetch = async (): Promise<Response> => new Response(JSON.stringify(body), { status });
	try {
		await GET({ fetch, params: { id: 'audit' } } as unknown as Parameters<typeof GET>[0]);
	} catch (e) {
		if (isHttpError(e)) return { status: e.status, message: e.body.message };
	}
	return undefined;
}

describe('Word export route', () => {
	it('names the reason a custom template failed to render', async () => {
		const failure = await exportError({
			error: 'invalidCustomWordTemplate',
			detail: "'x' is undefined"
		});
		expect(failure?.message).toContain("'x' is undefined");
	});

	it('translates a custom template that timed out', async () => {
		const failure = await exportError({ error: 'customWordTemplateTimedOut' });
		expect(failure?.message).toBe(m.customWordTemplateTimedOut());
	});

	it('translates a custom template that crashed', async () => {
		const failure = await exportError({ error: 'customWordTemplateCrashed' });
		expect(failure?.message).toBe(m.customWordTemplateCrashed());
	});

	it('translates a custom template that failed for another reason', async () => {
		const failure = await exportError({ error: 'customWordTemplateFailed' });
		expect(failure?.message).toBe(m.customWordTemplateFailed());
	});

	it('keeps the backend status and the generic message for other failures', async () => {
		expect(await exportError({ detail: 'Forbidden.' }, 403)).toEqual({
			status: 403,
			message: 'Error fetching the Word file'
		});
	});
});
