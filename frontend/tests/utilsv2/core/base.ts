import { test as base } from '@playwright/test';
import type { Page as _Page } from '@playwright/test';
import { fixtures, type Fixtures } from './fixtures';
import { expect as baseExpect } from '@playwright/test';
import { isEnterpriseMode } from './utils';

export const expect = baseExpect.extend({});
export const test = base.extend<Fixtures>(fixtures);

/** This must be used to construct the enterprise-only tests, this can't replace the real test object (e.g. enterpriseTest.step doesn't exist). */
export const enterpriseTest = (...args: any[]) => {
	if (isEnterpriseMode()) test(...args);
};

/**
 * This function must be called in every abstract methods.
 * It will throw an error indicating that the method can only be called from a derived class.
 */
export function notImplemented(): never {
	throw new Error('This method can only be called from a derived class !');
}
