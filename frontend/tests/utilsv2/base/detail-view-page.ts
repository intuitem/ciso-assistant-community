import { Page } from '../core/page';
import type { Page as _Page, Locator } from '@playwright/test';
import type { Expect } from '@playwright/test';
import { safeTranslate } from '$lib/utils/i18n';

// Make this type globally available in the utilsv2 codebase ?
// Should i put it in utils.ts or create a types.ts file for this ?
// type JSONObject = {[key: string]: JSONObject} | JSONObject[] | string | number | boolean | null;
// type JSONDict = {[key: string]: JSONObject};

export class DetailViewPage extends Page {
	protected _descriptionList: Locator;

	constructor(page: _Page, endpoint: string) {
		super(page, endpoint);
		this._descriptionList = this._self.getByTestId('description-list');
	}

	async checkValues(expect: Expect, values: { [key: string]: string }): Promise<void> {
		const rows = await this._descriptionList.getByTestId('description-list-row-elem').all();
		const descriptionListEntries = await Promise.all(
			rows.map(async (row) => {
				const key = await row.locator('dt').first().innerText();
				const value = await row.locator('dd').first().innerText();
				return [key, value];
			})
		);
		const currentValues = Object.fromEntries(descriptionListEntries);

		for (const [key, value] of Object.entries(values)) {
			const translatedKey = safeTranslate(key);
			expect(
				Object.hasOwn(currentValues, translatedKey),
				`The key '${translatedKey}' (translated from '${key}') wasn't found among the description list keys: ${JSON.stringify(Object.keys(currentValues))}`
			).toBeTruthy();
			expect(currentValues[translatedKey]).toBe(value);
		}

		// await expect(this._self).toBeVisible();
	}
}
/* export namespace DetailViewPage {
  export type Derived = new(page: _Page) => DetailViewPage;
} */
