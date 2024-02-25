import { expect, type Locator, type Page } from './test-utils.js';

export abstract class BasePage {
	readonly url: string;
	readonly name: string | RegExp;
	readonly pageTitle: Locator;
	readonly modalTitle: Locator;

	constructor(public readonly page: Page, url: string, name: string | RegExp) {
		this.url = url;
		this.name = name;
		this.pageTitle = this.page.locator('#page-title');
		this.modalTitle = this.page.getByTestId('modal-title');
	}

	async goto() {
		await this.page.goto(this.url);
		await this.page.waitForURL(this.url);
	}

	async hasUrl() {
		await expect(this.page).toHaveURL(this.url);
	}

	//TODO function to assert breadcrumb path is accurate

	async isToastVisible(value: string, flags?: string | undefined, options?: {} | undefined) {
		const toast = this.page.getByTestId('toast').filter({ hasText: new RegExp(value, flags) });
		await expect(toast).toBeVisible(options);
		await toast.getByLabel('Dismiss toast').click();
		await expect(toast).toBeHidden();
		return toast;
	}
}
