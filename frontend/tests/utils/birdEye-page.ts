import { expect, type Page } from './test-utils.js';
import { BasePage } from './base-page.js';

export class BirdEyePage extends BasePage {
	constructor(public readonly page: Page) {
		super(page, '/bird-eye', 'Bird Eye');
		// this.page.goto('/analytics');
	}
}
