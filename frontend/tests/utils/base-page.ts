import { expect, type Locator, type Page } from './test-utils.js';

/**
 * Escape the characters of `string` to safely insert it in a regex.
 *
 * @param {string} string - The string to escape.
 * @returns {string} The escaped string.
 */
function escapeRegex(string: string): string {
	return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export abstract class BasePage {
	readonly url: string;
	readonly name: string | RegExp;
	readonly pageTitle: Locator;
	readonly modalTitle: Locator;
	readonly breadcrumbs: Locator;

	constructor(
		public readonly page: Page,
		url: string,
		name: string | RegExp
	) {
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

	/**
	 * Check whether the browser's URL match the `this.url` value.
	 *
	 * @param {boolean} [strict=true] - Determines the URL matching mode.
	 * If `strict` is `true`, the function checks if `this.url` is strictly equal to the browser's URL.
	 * Otherwise, it checks if the browser's URL starts with `this.url`.
	 * @returns {void}
	 */
	async hasUrl(strict: boolean = false, url: string = this.url) {
		const URLPattern = strict ? url : new RegExp(escapeRegex(url) + '.*');
		await expect(this.page).toHaveURL(URLPattern);
	}

	async hasBreadcrumbPath(paths: (string | RegExp)[], fullPath = true, origin = 'Home') {
		paths.unshift(new RegExp('.+' + origin));
		if (fullPath) {
			await expect.soft(this.breadcrumbs).toHaveText(paths, { ignoreCase: true });
		} else {
			await expect
				.soft(this.breadcrumbs.last())
				.toHaveText(paths[paths.length - 1], { ignoreCase: true });
		}
	}

	async waitUntilLoaded() {
		const loadingFields = this.page.getByTestId('loading-field');
		if ((await loadingFields.count()) > 0) {
			await Promise.all(
				(await loadingFields.all()).map(async (field) => await expect(field).toBeHidden())
			);
		}
	}

	async isToastVisible(
		value: string,
		flags?: string,
		options?: {
			timeout?: number;
			dismiss?: boolean;
			waitHidden?: boolean;
			mode?: 'visible' | 'attached'; // NEW (default: 'attached' for blink toasts)
		}
	) {
		const {
			timeout = 5000,
			dismiss = false, // safer default
			waitHidden = true,
			mode = 'attached'
		} = options ?? {};
		const regex = new RegExp(value, flags);
		const toasts = this.page.getByTestId('toast').filter({ hasText: regex });
		const toast = toasts.first();
		if (mode === 'visible') {
			await expect(toast).toBeVisible({ timeout });
		} else {
			// catches ultra-brief toasts
			await expect(toast).toBeAttached({ timeout });
		}
		// If you still want to dismiss (only works if it stays long enough)
		if (dismiss) {
			const dismissBtn = toast.getByLabel('Dismiss toast');
			await expect(dismissBtn).toBeVisible({ timeout: Math.min(2000, timeout) });
			await dismissBtn.click();
			if (waitHidden) await expect(toast).toBeHidden({ timeout: 5000 });
		}
		return toasts;
	}
}
