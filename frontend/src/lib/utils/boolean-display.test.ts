import { describe, expect, it } from 'vitest';
import { booleanDisplay, getBooleanPolarity } from './boolean-display';

const SOLID = 'fa-solid fa-circle';
const HOLLOW = 'fa-regular fa-circle';

describe('booleanDisplay', () => {
	it('defaults to positive for an unlisted field', () => {
		expect(getBooleanPolarity('some_new_flag')).toBe('positive');
		expect(booleanDisplay(true, 'some_new_flag')).toEqual({
			icon: SOLID,
			colorClass: 'text-green-500'
		});
	});

	it('prefers a model-specific entry over the global one', () => {
		expect(getBooleanPolarity('is_read')).toBe('positive');
		expect(getBooleanPolarity('is_read', 'notifications')).toBe('warning_when_false_blank');
	});

	it('draws an unread notification loud and a read one blank', () => {
		expect(booleanDisplay(false, 'is_read', 'notifications')).toEqual({
			icon: SOLID,
			colorClass: 'text-orange-500'
		});
		expect(booleanDisplay(true, 'is_read', 'notifications')).toEqual({
			icon: HOLLOW,
			colorClass: 'text-gray-400'
		});
	});

	it('still affirms the true state for plain warning_when_false fields', () => {
		expect(booleanDisplay(true, 'has_mfa_enabled')).toEqual({
			icon: SOLID,
			colorClass: 'text-green-500'
		});
		expect(booleanDisplay(false, 'has_mfa_enabled')).toEqual({
			icon: SOLID,
			colorClass: 'text-orange-500'
		});
	});
});
