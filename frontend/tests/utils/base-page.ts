import { expect, type Locator, type Page } from './test-utils';

export abstract class BasePage {
	readonly url: string;
	readonly name: string | RegExp;

	constructor(public readonly page: Page, url: string, name: string | RegExp) {
		this.url = url;
		this.name = name;
	}

	async goto() {
		await this.page.goto(this.url);
	}

	async hasUrl() {
		await expect(this.page).toHaveURL(this.url);
	}
}
