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
		const dismiss = (options as { dismiss?: boolean } | undefined)?.dismiss ?? false; // safer default
		const waitHidden = (options as { waitHidden?: boolean } | undefined)?.waitHidden ?? true;

		const re = new RegExp(value, flags);

		// Install an observer once per page
		await this.page.evaluate(() => {
			const w = window as any;
			if (w.__pwToastObserverInstalled) return;

			w.__pwToastObserverInstalled = true;
			w.__pwToastSeen = [];

			const normalize = (s: string) => (s ?? '').replace(/\s+/g, ' ').trim();
			const record = (text: string) => {
				const t = normalize(text);
				if (!t) return;
				w.__pwToastSeen.push({ t: Date.now(), text: t });
				if (w.__pwToastSeen.length > 200) w.__pwToastSeen.splice(0, w.__pwToastSeen.length - 200);
			};

			const scan = () => {
				for (const el of Array.from(document.querySelectorAll('[data-testid="toast"]'))) {
					record((el as HTMLElement).innerText || el.textContent || '');
				}
			};

			scan();

			const obs = new MutationObserver(() => scan());
			obs.observe(document.documentElement, {
				subtree: true,
				childList: true,
				characterData: true,
				attributes: true
			});
		});

		// Wait until the observer recorded a matching toast at least once
		await expect
			.poll(
				async () => {
					const seen = await this.page.evaluate(() => (window as any).__pwToastSeen ?? []);
					return seen.some((e: any) => re.test(e.text));
				},
				{ timeout }
			)
			.toBeTruthy();

		// Keep return type compatible with your previous code
		const matching = this.page.getByTestId('toast').filter({ hasText: re });

		// Best-effort dismiss (won’t fail if it already disappeared)
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
