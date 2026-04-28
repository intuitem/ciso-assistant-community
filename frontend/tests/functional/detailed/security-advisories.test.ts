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
});
