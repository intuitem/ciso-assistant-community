import { Element } from '../core/element';
import type { Expect } from '@playwright/test';

export class Toast extends Element {
	static DATA_TESTID = 'toast';

	async checkContainText(expect: Expect, text: string) {
		expect(this._self).toContainText(text);
	}
}

/* async isToastVisible(value: string, flags?: string | undefined, options?: {} | undefined) {
  const toast = this.page.getByTestId('toast').filter({ hasText: new RegExp(value, flags) });
  await expect(toast).toBeVisible(options);
  await toast.getByLabel('Dismiss toast').click();
  // await expect(toast).toBeHidden();
  return toast;
} */
