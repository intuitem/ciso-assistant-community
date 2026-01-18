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

	async isToastVisible(value: string, flags?: string | undefined, options?: {} | undefined) {
		const timeout = (options as { timeout?: number } | undefined)?.timeout ?? 5000;

		// Keep backward-compat behavior: you used to dismiss by default.
		// But dismissing makes blink-toasts even flakier; so default to false.
		const dismiss = (options as { dismiss?: boolean } | undefined)?.dismiss ?? false;
		const waitHidden = (options as { waitHidden?: boolean } | undefined)?.waitHidden ?? true;
		const optional = (options as { optional?: boolean } | undefined)?.optional ?? false;

		// Normalize whitespace so we don't lose on line breaks / multiple spaces
		const normalize = (s: string) => (s ?? '').replace(/\s+/g, ' ').trim();

		const expected = normalize(value);

		// If flags provided, treat as regex flags, but still be whitespace-tolerant.
		// Otherwise use a simple "includes" on normalized text.
		const re =
			flags !== undefined
				? new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s+'), flags)
				: null;

		// Search text anywhere in the DOM, including shadow roots
		const scanFrameForText = async (frame: import('@playwright/test').Frame) => {
			return await frame.evaluate(
				({ expected, useRegex, regexSource, regexFlags }) => {
					const normalize = (s: string) => (s ?? '').replace(/\s+/g, ' ').trim();
					const re = useRegex ? new RegExp(regexSource, regexFlags) : null;

					const matches = (t: string) => {
						const n = normalize(t);
						if (!n) return false;
						return re ? re.test(n) : n.includes(expected);
					};

					// Walk DOM + shadow DOM
					const stack: (Document | ShadowRoot)[] = [document];
					while (stack.length) {
						const root = stack.pop()!;
						// Fast check: if body text already contains, return early
						if (
							root instanceof Document &&
							matches(root.body?.innerText || root.body?.textContent || '')
						) {
							return true;
						}

						const tree = root.querySelectorAll ? root.querySelectorAll('*') : [];
						for (const el of Array.from(tree)) {
							const anyEl = el as any;

							// Check common announcement nodes quickly
							const role = el.getAttribute?.('role');
							const ariaLive = el.getAttribute?.('aria-live');
							const testid = el.getAttribute?.('data-testid');

							if (
								testid === 'toast' ||
								role === 'alert' ||
								ariaLive === 'polite' ||
								ariaLive === 'assertive'
							) {
								const txt = (el as HTMLElement).innerText || el.textContent || '';
								if (matches(txt)) return true;
							}

							// Dive into shadow root
							if (anyEl.shadowRoot) stack.push(anyEl.shadowRoot);
						}
					}

					// Last resort: whole document text
					return matches(
						document.documentElement?.innerText || document.documentElement?.textContent || ''
					);
				},
				{
					expected,
					useRegex: Boolean(re),
					regexSource: re?.source ?? '',
					regexFlags: re?.flags ?? ''
				}
			);
		};

		let toastFound = false;
		try {
			// 1) Wait until the text appears in ANY frame (main frame or iframes)
			await expect
				.poll(
					async () => {
						const frames = this.page.frames();
						for (const f of frames) {
							try {
								if (await scanFrameForText(f)) return true;
							} catch {
								// Ignore cross-origin / detached frame errors
							}
						}
						return false;
					},
					{ timeout }
				)
				.toBeTruthy();
			toastFound = true;
		} catch (error) {
			if (!optional) throw error;
			console.warn(`[toast] Optional toast not found: "${expected}" (flags: ${flags ?? 'none'})`);
		}

		// 2) Return compatible locator (as before)
		const matching = this.page.getByTestId('toast').filter({ hasText: re ?? expected });

		if (!toastFound) {
			return matching;
		}

		// 3) Best-effort dismiss if requested (won't fail if it vanished)
		if (dismiss) {
			const toast = matching.first();
			if (await toast.isVisible().catch(() => false)) {
				const btn = toast.getByLabel('Dismiss toast');
				if (await btn.isVisible().catch(() => false)) {
					await btn.click();
					if (waitHidden) {
						await Promise.race([
							expect(toast)
								.toBeHidden({ timeout: 5000 })
								.catch(() => {}),
							expect(toast)
								.toBeDetached({ timeout: 5000 })
								.catch(() => {})
						]);
					}
				}
			}
		}

		return matching;
	}
}
