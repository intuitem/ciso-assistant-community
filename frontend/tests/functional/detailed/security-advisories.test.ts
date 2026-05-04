import { test, expect } from '../../utils/test-utils.js';

test.describe('Security Advisories', () => {
	test('sync KEV catalog and enrich advisory from NVD', async ({ logedPage, page }) => {
		test.setTimeout(120_000);

		await test.step('navigate to security advisories', async () => {
			await page.goto('/security-advisories');
			await expect(page).toHaveURL(/.*security-advisories.*/);
			await page.waitForLoadState('networkidle');
		});

		await test.step('pull CISA KEV catalog', async () => {
			const syncBtn = page.getByTestId('sync-kev-button');
			await expect(syncBtn).toBeVisible();
			await syncBtn.click();
		});

		await test.step('confirm pull in modal', async () => {
			const modal = page.getByTestId('modal');
			await expect(modal).toBeVisible({ timeout: 10_000 });
			await expect(modal.getByText('Pull external catalog')).toBeVisible();

			await modal.getByRole('button', { name: /confirm/i }).click();
			await expect(modal).not.toBeVisible({ timeout: 30_000 });

			await page.waitForLoadState('networkidle');
		});

		await test.step('verify at least one advisory is present in the table', async () => {
			await page.waitForTimeout(3_000);
			await page.reload();
			await page.waitForLoadState('networkidle');

			const rowCount = await page.getByTestId('tablerow-detail-button').count();
			console.log('tablerow-detail-button count:', rowCount);

			await expect(page.getByTestId('tablerow-detail-button').first()).toBeVisible({
				timeout: 30_000
			});
		});

		await test.step('click on first advisory to view detail', async () => {
			const detailBtn = page.getByTestId('tablerow-detail-button').first();
			await expect(detailBtn).toBeVisible();

			const href = await detailBtn.getAttribute('href');
			console.log('detail href:', href);
			if (href) {
				await page.goto(href);
			} else {
				await detailBtn.click();
			}
			await page.waitForLoadState('networkidle');
			await expect(page).toHaveURL(/.*security-advisories\/.+/);
		});

		await test.step('note existing field values before enrichment', async () => {
			const cvssField = page.getByTestId('cvss-base_score-field-value');
			const cvssText = await cvssField.textContent().catch(() => '--');
			console.log('CVSS before enrich:', cvssText?.trim());
		});

		await test.step('click Enrich from NVD', async () => {
			const enrichBtn = page.getByRole('button', { name: /enrich from nvd/i });
			await expect(enrichBtn).toBeVisible();
			await enrichBtn.click();

			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(2_000);
		});

		await test.step('verify fields have been updated after enrichment', async () => {
			const cvssScore = page.getByTestId('cvss-base_score-field-value');
			const cvssVector = page.getByTestId('cvss-vector-field-value');

			await expect(cvssScore).not.toHaveText('--');
			await expect(cvssVector).not.toHaveText('--');

			const scoreText = await cvssScore.textContent();
			const vectorText = await cvssVector.textContent();
			console.log('CVSS score after enrich:', scoreText?.trim());
			console.log('CVSS vector after enrich:', vectorText?.trim());
		});
	});

	test('sync MITRE CWE catalog and view first CWE', async ({ logedPage, page }) => {
		test.setTimeout(120_000);

		await test.step('navigate to CWEs via sidebar', async () => {
			await page.goto('/analytics');
			await page.waitForLoadState('networkidle');
			await page.getByTestId('accordion-item-catalog').click();
			await page.waitForTimeout(300);
			await page.getByTestId('accordion-item-cwes').click();
			await expect(page).toHaveURL(/.*cwes.*/);
			await page.waitForLoadState('networkidle');
		});

		await test.step('pull MITRE CWE catalog', async () => {
			const syncBtn = page.getByTestId('sync-cwe-button');
			await expect(syncBtn).toBeVisible();
			await syncBtn.click();
		});

		await test.step('wait for CWE sync to complete and verify rows', async () => {
			await page.waitForTimeout(5_000);
			await page.reload();
			await page.waitForLoadState('networkidle');

			const rowCount = await page.getByTestId('tablerow-detail-button').count();
			console.log('CWE tablerow-detail-button count:', rowCount);

			await expect(page.getByTestId('tablerow-detail-button').first()).toBeVisible({
				timeout: 30_000
			});
		});

		await test.step('click on first CWE to view detail', async () => {
			const detailBtn = page.getByTestId('tablerow-detail-button').first();
			const href = await detailBtn.getAttribute('href');
			console.log('CWE detail href:', href);
			if (href) {
				await page.goto(href);
			} else {
				await detailBtn.click();
			}
			await page.waitForLoadState('networkidle');
			await expect(page).toHaveURL(/.*cwes\/.+/);
		});

		await test.step('verify CWE detail page loaded', async () => {
			await expect(page.getByTestId('ref-id-field-value')).toBeVisible();
			await expect(page.getByTestId('name-field-value')).toBeVisible();

			const refId = await page.getByTestId('ref-id-field-value').textContent();
			const name = await page.getByTestId('name-field-value').textContent();
			console.log('CWE ref_id:', refId?.trim());
			console.log('CWE name:', name?.trim());
		});
	});

	test('vulnerability SLA settings - set values, save, reset to defaults', async ({
		logedPage,
		page
	}) => {
		test.setTimeout(60_000);

		const fields = ['critical', 'high', 'medium', 'low', 'info'] as const;
		const initialValues: Record<string, string> = {};
		let initialAnchor = '';

		const gotoSlaTab = async () => {
			await page.goto('/settings');
			await page.waitForLoadState('networkidle');
			await page.locator('[data-value="vulnerabilitySla"]').click();
			await page.waitForTimeout(300);
			await expect(page.getByTestId('form-input-critical')).toBeVisible();
		};

		const saveSlaForm = async () => {
			await page.locator('form[action*="vulnerabilitySla"] [data-testid="save-button"]').click();
			await expect(page.getByTestId('toast')).toBeVisible({ timeout: 10_000 });
			await page.waitForLoadState('networkidle');
		};

		await test.step('navigate to settings Vulnerability SLA tab', gotoSlaTab);

		await test.step('snapshot initial SLA settings', async () => {
			initialAnchor = await page.getByTestId('form-input-sla-anchor').inputValue();
			for (const field of fields) {
				initialValues[field] = await page.getByTestId(`form-input-${field}`).inputValue();
			}
			console.log('Initial SLA anchor:', initialAnchor, 'values:', initialValues);
		});

		try {
			await test.step('set SLA anchor to Published date and all severities to 20', async () => {
				await page.getByTestId('form-input-sla-anchor').selectOption('published_date');
				for (const field of fields) {
					await page.getByTestId(`form-input-${field}`).fill('20');
				}
			});

			await test.step('save and verify toast', saveSlaForm);

			await test.step('verify values persisted', async () => {
				await page.reload();
				await page.waitForLoadState('networkidle');
				await page.locator('[data-value="vulnerabilitySla"]').click();
				await page.waitForTimeout(300);
				for (const field of fields) {
					await expect(page.getByTestId(`form-input-${field}`)).toHaveValue('20');
				}
			});

			await test.step('click Reset to defaults and verify default values (15/30/90/180/365)', async () => {
				await page.getByRole('button', { name: /reset to defaults/i }).click();
				await page.waitForTimeout(300);
				const defaults: Record<string, string> = {
					critical: '15',
					high: '30',
					medium: '90',
					low: '180',
					info: '365'
				};
				for (const [field, value] of Object.entries(defaults)) {
					await expect(page.getByTestId(`form-input-${field}`)).toHaveValue(value);
				}
			});
		} finally {
			await test.step('restore original SLA settings', async () => {
				await gotoSlaTab();
				if (initialAnchor) {
					await page.getByTestId('form-input-sla-anchor').selectOption(initialAnchor);
				}
				for (const field of fields) {
					await page.getByTestId(`form-input-${field}`).fill(initialValues[field] ?? '');
				}
				await saveSlaForm();
			});
		}
	});

	test('vulnerability feeds settings - enable all, save, disable all, save', async ({
		logedPage,
		page
	}) => {
		test.setTimeout(60_000);

		const FEEDS = [
			'form-input-kev-feed-enabled',
			'form-input-epss-feed-enabled',
			'form-input-nvd-enrich-enabled'
		];

		const initialState: Record<string, boolean> = {};

		const gotoFeedsTab = async () => {
			await page.goto('/settings');
			await page.waitForLoadState('networkidle');
			await page.locator('[data-value="secIntelFeeds"]').click();
			await page.waitForTimeout(300);
			await expect(page.getByTestId('form-input-kev-feed-enabled')).toBeVisible();
		};

		const saveFeedsForm = async () => {
			await page.locator('form[action*="secIntelFeeds"] [data-testid="save-button"]').click();
			await expect(page.getByTestId('toast')).toBeVisible({ timeout: 10_000 });
			await page.waitForLoadState('networkidle');
		};

		await test.step('navigate to Vulnerability Feeds tab', gotoFeedsTab);

		await test.step('snapshot initial feed states', async () => {
			for (const testid of FEEDS) {
				initialState[testid] = await page.getByTestId(testid).isChecked();
			}
			console.log('Initial feed states:', initialState);
		});

		await test.step('enable all feeds', async () => {
			for (const testid of FEEDS) {
				const checkbox = page.getByTestId(testid);
				if (!(await checkbox.isChecked())) {
					await checkbox.click();
				}
			}
		});

		await test.step('save with all feeds enabled', saveFeedsForm);

		await test.step('verify all feeds checked after reload', async () => {
			await gotoFeedsTab();
			for (const testid of FEEDS) {
				await expect(page.getByTestId(testid)).toBeChecked();
			}
		});

		await test.step('disable all feeds', async () => {
			for (const testid of FEEDS) {
				const checkbox = page.getByTestId(testid);
				if (await checkbox.isChecked()) {
					await checkbox.click();
				}
			}
		});

		await test.step('save with all feeds disabled', saveFeedsForm);

		await test.step('verify all feeds unchecked after reload', async () => {
			await gotoFeedsTab();
			for (const testid of FEEDS) {
				await expect(page.getByTestId(testid)).not.toBeChecked();
			}
		});

		await test.step('restore initial feed states', async () => {
			await gotoFeedsTab();
			for (const testid of FEEDS) {
				const checkbox = page.getByTestId(testid);
				const current = await checkbox.isChecked();
				if (current !== initialState[testid]) {
					await checkbox.click();
				}
			}
			await saveFeedsForm();
		});
	});
});
