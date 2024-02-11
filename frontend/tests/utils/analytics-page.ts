import { expect, type Page } from './test-utils';
import { PageContent } from './page-content';
import { BasePage } from './base-page';

export class AnalyticsPage extends BasePage {
	constructor(public readonly page: Page) {
		super(page, '/analytics', 'Analytics');
		// this.page.goto('/analytics');
	}

	async hasTitle() {
		await expect.soft(this.page.locator('#page-title')).toHaveText('Analytics');
	}
}
