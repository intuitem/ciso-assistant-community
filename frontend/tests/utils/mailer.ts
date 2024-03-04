import { expect, type Locator, type Page } from './test-utils.js';

export class Mailer {
	readonly url: string;
    readonly emails: Locator;

	constructor(public readonly page: Page) {
		this.url = "http://localhost:8025";
        this.emails = this.page.locator('.msglist-message');

        this.goto();
	}

	async goto() {
		await this.page.goto(this.url);
		await this.page.waitForURL(this.url);
	}

	async hasUrl() {
		await expect(this.page).toHaveURL(this.url);
	}

    async lastEmail() {
        return this.emails.first();
    }
}
