import { isHttpError } from '@sveltejs/kit';
import { describe, expect, it } from 'vitest';
import { errorFromBody, getErrorReason } from './errors';

const thrown = (body: unknown) => {
	try {
		errorFromBody(400, body);
	} catch (e) {
		if (isHttpError(e)) return { status: e.status, body: e.body };
		throw e;
	}
	throw new Error('errorFromBody did not throw');
};

describe('errorFromBody', () => {
	it('keeps backend fields next to the message', () => {
		expect(thrown({ detail: 'nope', field: ['x'] })).toEqual({
			status: 400,
			body: { status: 400, message: 'Error: 400', detail: 'nope', field: ['x'] }
		});
	});

	it('uses a string message from the body', () => {
		expect(thrown({ message: 'bad', error: 'e' }).body).toEqual({
			status: 400,
			message: 'bad',
			error: 'e'
		});
	});

	it('uses a string body as the message', () => {
		expect(thrown('plain text').body).toEqual({ status: 400, message: 'plain text' });
	});

	it('falls back to the default message for empty or odd bodies', () => {
		expect(thrown(null).body.message).toBe('Error: 400');
		expect(thrown(undefined).body.message).toBe('Error: 400');
		expect(thrown({ message: 42 }).body).toEqual({ status: 400, message: 'Error: 400' });
	});
});

describe('getErrorReason', () => {
	it('prefers the field error over the default message', () => {
		const { body } = thrown({ commitment_state: ['onlyTheReviewerCanDoThis'] });
		expect(getErrorReason(body)).toBe('onlyTheReviewerCanDoThis');
	});

	it('falls back to the message without a field error', () => {
		expect(getErrorReason(thrown({ message: 'bad' }).body)).toBe('bad');
	});

	it('finds nothing in an unreadable body', () => {
		expect(getErrorReason(null)).toBeUndefined();
		expect(getErrorReason({ commitment_state: [] })).toBeUndefined();
	});
});
