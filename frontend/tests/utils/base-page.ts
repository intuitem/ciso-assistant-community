import { expect, type Locator, type Page } from './test-utils.js';

export abstract class BasePage {
	readonly url: string;
	readonly name: string | RegExp;
	readonly pageTitle: Locator;
	readonly modalTitle: Locator;
	readonly breadcrumbs: Locator;

	constructor(public readonly page: Page, url: string, name: string | RegExp) {
		this.url = url;
		this.name = name;
		this.pageTitle = this.page.locator('#page-title');
		this.modalTitle = this.page.getByTestId('modal-title');
		this.breadcrumbs = this.page.getByTestId('crumb-item');
	}

	async goto() {
		await this.page.goto(this.url);
		await this.page.waitForURL(this.url);
	}

	async hasTitle(title: string | RegExp = this.name) {
		await expect.soft(this.pageTitle).toHaveText(title);
	}

	async hasUrl() {
		await expect(this.page).toHaveURL(this.url);
	}

	async hasBreadcrumbPath(
		paths: (string | RegExp)[],
		fullPath: boolean = true,
		origin: string = 'Home'
	) {
		paths.unshift(new RegExp('.+' + origin));
		if (fullPath) {
			await expect.soft(this.breadcrumbs).toHaveText(paths);
		} else {
			await expect.soft(this.breadcrumbs.last()).toHaveText(paths[paths.length - 1]);
		}
	}

	async checkForUndefinedText() {
		await expect
			.soft(this.page.getByText('undefined'), 'An undefined text is visible on the page')
			.toHaveCount(0);
	}

	async waitUntilLoaded() {
		const loadingFields = this.page.getByTestId('loading-field');
		if ((await loadingFields.count()) > 0) {
			await Promise.all(
				(await loadingFields.all()).map(async (field) => await expect(field).toBeHidden())
			);
		}
	}

	async isToastVisible(value: string, flags?: string | undefined, options?: {} | undefined) {
		const toast = this.page.getByTestId('toast').filter({ hasText: new RegExp(value, flags) });
		//await expect(toast).toBeVisible(options);
		await toast.getByLabel('Dismiss toast').click();
		//await expect(toast).toBeHidden();
		return toast;
	}
}
