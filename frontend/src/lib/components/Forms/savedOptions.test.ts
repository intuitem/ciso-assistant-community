import { describe, expect, it } from 'vitest';
import { withSavedOptions } from './savedOptions';

const label = (value: string) => `${value} (unverified)`;

describe('withSavedOptions', () => {
	it('adds saved values missing from the options', () => {
		expect(
			withSavedOptions([{ value: 'KAN:10003', label: 'Kanban - Tâche' }], ['KAN:Task'], label)
		).toEqual([
			{ value: 'KAN:10003', label: 'Kanban - Tâche' },
			{ value: 'KAN:Task', label: 'KAN:Task (unverified)' }
		]);
	});

	it('leaves options as is when saved values are listed or empty', () => {
		const options = [{ value: 1, label: 'Highest' }];
		expect(withSavedOptions(options, [1, '', null, undefined], label)).toEqual(options);
	});

	it('adds each missing value once', () => {
		expect(withSavedOptions([], ['Done', 'Done'], label)).toEqual([
			{ value: 'Done', label: 'Done (unverified)' }
		]);
	});
});
