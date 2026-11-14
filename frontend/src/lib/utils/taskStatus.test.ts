import { describe, it, expect } from 'vitest';
import { aggregateStatus, countOccurrenceStates } from '#lib/utils/taskStatus.js';

// Same cases as the control plan's rule, TaskTemplateViewSet._aggregate_status.
describe('aggregateStatus', () => {
	it('has no status without an occurrence', () => {
		expect(aggregateStatus([])).toBeNull();
	});

	it('is the status of a single occurrence', () => {
		for (const status of ['pending', 'in_progress', 'completed', 'cancelled']) {
			expect(aggregateStatus([status])).toBe(status);
		}
	});

	it('is completed only when every occurrence is', () => {
		expect(aggregateStatus(['completed', 'completed'])).toBe('completed');
		expect(aggregateStatus(['completed', 'pending'])).toBe('in_progress');
	});

	it('is in progress as soon as one occurrence is', () => {
		expect(aggregateStatus(['pending', 'in_progress', 'pending'])).toBe('in_progress');
	});

	it('is pending when nothing has started', () => {
		expect(aggregateStatus(['pending', 'pending'])).toBe('pending');
	});

	it('sets cancelled occurrences aside unless all are', () => {
		expect(aggregateStatus(['cancelled', 'completed'])).toBe('completed');
		expect(aggregateStatus(['cancelled', 'pending'])).toBe('pending');
		expect(aggregateStatus(['cancelled', 'cancelled'])).toBe('cancelled');
	});
});

describe('countOccurrenceStates', () => {
	// Far enough from today to stay due before it, or after it.
	const past = '2000-01-01';
	const future = '2999-01-01';

	it('counts occurrences as they are drawn, late ones apart from their status', () => {
		const counts = countOccurrenceStates([
			{ status: 'completed', due_date: past },
			{ status: 'pending', due_date: past },
			{ status: 'in_progress', due_date: past },
			{ status: 'completed', due_date: future },
			{ status: 'pending', due_date: future }
		]);
		expect(counts).toEqual([
			['overdue', 2],
			['completed', 2],
			['planned', 1]
		]);
	});

	it('leaves out the states the period has none of', () => {
		expect(countOccurrenceStates([{ status: 'cancelled', due_date: past }])).toEqual([
			['cancelled', 1]
		]);
		expect(countOccurrenceStates([])).toEqual([]);
	});
});
