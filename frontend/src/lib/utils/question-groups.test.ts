import { describe, expect, it } from 'vitest';
import { hasQuestionAnswer, normalizeQuestionGroups } from './question-groups';

describe('normalizeQuestionGroups', () => {
	it('uses the requirement order and groups questions by their group reference', () => {
		expect(
			normalizeQuestionGroups(
				['not_achieved', 'achieved'],
				[
					{
						ref_id: 'not_achieved',
						name: 'Not Achieved',
						description: 'One statement is true.',
						annotation: 'A failed state.',
						typical_evidence: 'A risk record.'
					},
					{ ref_id: 'achieved', name: 'Achieved' }
				],
				{
					'q:1': { question_group: 'not_achieved' },
					'q:2': { question_group: 'not_achieved' },
					'q:3': { question_group: 'achieved' }
				}
			)
		).toEqual([
			{
				refId: 'not_achieved',
				name: 'Not Achieved',
				description: 'One statement is true.',
				annotation: 'A failed state.',
				typicalEvidence: 'A risk record.',
				order: ['q:1', 'q:2']
			},
			{
				refId: 'achieved',
				name: 'Achieved',
				description: '',
				annotation: '',
				typicalEvidence: '',
				order: ['q:3']
			}
		]);
	});

	it('falls back when a question references a group outside the local order', () => {
		expect(
			normalizeQuestionGroups(
				['not_achieved'],
				[{ ref_id: 'not_achieved', name: 'Not Achieved' }],
				{
					'q:1': { question_group: 'not_achieved' },
					'q:2': { question_group: 'not_achieved' },
					'q:3': { question_group: 'achieved' }
				}
			)
		).toEqual([]);
	});

	it('falls back for an unknown definition or a group without questions', () => {
		expect(
			normalizeQuestionGroups(
				['not_achieved', 'achieved'],
				[{ ref_id: 'not_achieved', name: 'Not Achieved' }],
				{
					'q:1': { question_group: 'not_achieved' },
					'q:2': { question_group: 'not_achieved' },
					'q:3': { question_group: 'not_achieved' }
				}
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
