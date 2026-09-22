import { describe, expect, it } from 'vitest';
import { hasQuestionAnswer, normalizeQuestionGroups } from './question-groups';

const questions = {
	'q:1': {},
	'q:2': {},
	'q:3': {}
};

describe('normalizeQuestionGroups', () => {
	it('sorts numeric group keys and preserves the declared question order', () => {
		expect(
			normalizeQuestionGroups(
				{
					2: { description: 'Achieved', order: ['q:3'] },
					1: { description: 'Not Achieved', order: ['q:2', 'q:1'] }
				},
				questions
			)
		).toEqual([
			{ description: 'Not Achieved', order: ['q:2', 'q:1'] },
			{ description: 'Achieved', order: ['q:3'] }
		]);
	});

	it('falls back when a question is omitted', () => {
		expect(
			normalizeQuestionGroups(
				{ 1: { description: 'Not Achieved', order: ['q:1', 'q:2'] } },
				questions
			)
		).toEqual([]);
	});

	it('falls back when a question is repeated or unknown', () => {
		expect(
			normalizeQuestionGroups(
				{
					1: { description: 'First', order: ['q:1', 'q:2'] },
					2: { description: 'Second', order: ['q:2', 'q:4'] }
				},
				questions
			)
		).toEqual([]);
	});
});

describe('hasQuestionAnswer', () => {
	it('treats false and zero as answers while rejecting empty values', () => {
		expect(hasQuestionAnswer(false)).toBe(true);
		expect(hasQuestionAnswer(0)).toBe(true);
		expect(hasQuestionAnswer('answer')).toBe(true);
		expect(hasQuestionAnswer(['choice'])).toBe(true);
		expect(hasQuestionAnswer(null)).toBe(false);
		expect(hasQuestionAnswer(undefined)).toBe(false);
		expect(hasQuestionAnswer('   ')).toBe(false);
		expect(hasQuestionAnswer([])).toBe(false);
	});

	it('counts an uploaded attachment as an answer', () => {
		expect(hasQuestionAnswer(undefined, 1)).toBe(true);
	});
});
