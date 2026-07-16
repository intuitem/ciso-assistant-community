import { describe, it, expect } from 'vitest';

import {
	isAccessAllowed,
	hasPermissionAnywhere,
	canPerformAction,
	canPerformActionOnObject,
	resolveObjectDomain
} from './access-control';
import type { User } from './types';

const FOLDER_A = '11111111-1111-1111-1111-111111111111';
const FOLDER_B = '22222222-2222-2222-2222-222222222222';
const ROOT = '00000000-0000-0000-0000-000000000000';

const user = {
	root_folder_id: ROOT,
	domain_permissions: {
		[FOLDER_A]: ['view_riskassessment', 'change_riskassessment'],
		[FOLDER_B]: ['view_riskassessment']
	}
} as unknown as User;

describe('isAccessAllowed', () => {
	it('grants a permission held on the folder', () => {
		expect(isAccessAllowed(user, 'change_riskassessment', FOLDER_A)).toBe(true);
	});

	it('denies a permission held only on another folder', () => {
		expect(isAccessAllowed(user, 'change_riskassessment', FOLDER_B)).toBe(false);
	});

	it('denies on an unknown folder and on a missing user', () => {
		expect(isAccessAllowed(user, 'view_riskassessment', ROOT)).toBe(false);
		expect(isAccessAllowed(undefined as unknown as User, 'view_riskassessment', FOLDER_A)).toBe(
			false
		);
	});
});

describe('hasPermissionAnywhere', () => {
	it('is true when the permission exists on at least one folder', () => {
		expect(hasPermissionAnywhere(user, 'change_riskassessment')).toBe(true);
	});

	it('is false when the permission exists on no folder', () => {
		expect(hasPermissionAnywhere(user, 'delete_riskassessment')).toBe(false);
	});

	it('is false without a user or without domain_permissions', () => {
		expect(hasPermissionAnywhere(undefined as unknown as User, 'view_riskassessment')).toBe(false);
		expect(hasPermissionAnywhere({} as User, 'view_riskassessment')).toBe(false);
	});
});

describe('resolveObjectDomain', () => {
	it('uses the object id itself for folders', () => {
		expect(resolveObjectDomain('folder', { id: FOLDER_A })).toBe(FOLDER_A);
	});

	it('reads folder as nested object or bare id', () => {
		expect(resolveObjectDomain('riskassessment', { folder: { id: FOLDER_A } })).toBe(FOLDER_A);
		expect(resolveObjectDomain('riskassessment', { folder: FOLDER_A })).toBe(FOLDER_A);
	});

	it('returns undefined when the payload carries no folder', () => {
		expect(resolveObjectDomain('solution', { id: 'x' })).toBeUndefined();
		expect(resolveObjectDomain('solution', undefined)).toBeUndefined();
	});
});

describe('canPerformActionOnObject', () => {
	it('scopes to the object folder when present', () => {
		const object = { folder: { id: FOLDER_A } };
		expect(
			canPerformActionOnObject({ user, action: 'change', model: 'riskassessment', object })
		).toBe(true);
		// same permission missing in FOLDER_B
		expect(
			canPerformActionOnObject({
				user,
				action: 'change',
				model: 'riskassessment',
				object: { folder: { id: FOLDER_B } }
			})
		).toBe(false);
	});

	it('falls back to the existential check when the payload has no folder', () => {
		expect(
			canPerformActionOnObject({ user, action: 'change', model: 'riskassessment', object: {} })
		).toBe(true);
		expect(
			canPerformActionOnObject({ user, action: 'delete', model: 'riskassessment', object: {} })
		).toBe(false);
	});

	it('matches canPerformAction when the domain is known', () => {
		expect(
			canPerformAction({ user, action: 'view', model: 'riskassessment', domain: FOLDER_B })
		).toBe(
			canPerformActionOnObject({
				user,
				action: 'view',
				model: 'riskassessment',
				object: { folder: FOLDER_B }
			})
		);
	});
});
