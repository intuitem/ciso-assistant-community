import { expect, type Locator, type Page } from './test-utils';

export class Layout {
	readonly pageTitle: Locator;
	readonly modalTitle: Locator;

	constructor(public readonly page: Page) {
		this.pageTitle = this.page.locator('#page-title');
		this.modalTitle = this.page.getByTestId('modal-title');
	}
}
