// import { ModelForm } from './model-form';
import { Element } from '../core/element';
import type { Expect, Locator } from '@playwright/test';

/** Represents the `<AutoCompleteSelect/>` component.
 * The dataTestId filter must be used to access it with the _getSubElement method as its ID is dynamic. */
export class AutoCompleteSelect extends Element {
	static DATA_TESTID = undefined; // Dynamic data-testid.

	/* getForm<T = ModelForm>(formClass: Element.Class<T>): T {
    return this._getSubElement(formClass);
  } */

	async select(expect: Expect, value: string) {
		const inputSearch = this._self.locator('ul.selected input');
		const activeOption = this._self.locator('[role="option"].active');
		const searchBox = this._self.getByRole('searchbox');

		let optionCount = 0;
		await expect
			.poll(
				async () => {
					const classes = await searchBox.getAttribute('class');
					if (classes && classes.indexOf('disabled') >= 0) {
						return 1;
					}
					optionCount = await this._self.locator('[role="option"]').count();
					return optionCount; // document.querySelectorAll(`[role="option"]`);
				},
				{ timeout: 20_000 }
			)
			.toBeGreaterThan(0);

		if (optionCount <= 1) {
			return;
		}

		await inputSearch.fill(value);
		const lastOption = this._self.locator('[role="option"]').last();

		const start = Date.now();
		while (true) {
			const html = await lastOption.innerHTML();
			if (html !== 'No matching options<!---->') break;
			if (Date.now() - start > 10_000) {
				expect(false, 'Expected condition was not met').toBeTruthy();
			}
		}
		await lastOption.evaluate((node) => node.classList.add('active'));
		await activeOption.click({ force: true });
	}
}
