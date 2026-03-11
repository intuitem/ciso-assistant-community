import type { FrameLocator } from '@playwright/test';
import { type Locator, type Page } from './test-utils.js';

export class MailContent {
	readonly content: FrameLocator;
	readonly setPasswordButton: Locator;
	readonly resetPasswordButton: Locator;

	constructor(public readonly page: Page) {
		this.content = this.page.frameLocator('#preview-html');
		this.setPasswordButton = this.content.getByRole('link', { name: 'Set my password' });
		this.resetPasswordButton = this.content.getByRole('link', { name: 'Reset my password' });
	}
}
