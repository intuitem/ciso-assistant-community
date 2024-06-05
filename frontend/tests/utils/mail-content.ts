import type { FrameLocator } from '@playwright/test';
import { type Locator, type Page } from './test-utils.js';

export class MailContent {
	readonly content: FrameLocator;
	readonly setPasswordButton: Locator;
	readonly resetPasswordButton: Locator;

	constructor(public readonly page: Page) {
		this.content = this.page.frameLocator('#preview-html');
		this.setPasswordButton = this.content.getByTestId('set-password-btn');
		this.resetPasswordButton = this.content.getByTestId('reset-password-btn');
	}
}
