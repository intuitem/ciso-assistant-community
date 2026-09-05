import { test, expect, TestContent } from '../../utils/test-utils.js';

const vars = TestContent.generateTestVars();

// Regression guard for #4752: the form used to post `value` as a JSON string, which the
// serializer's object schema rejected — the sample was silently never created.
const sampleValue = 42;
const sampleTimestamp = '2024-07-17T16:19';

test('user can add a custom metric sample to a metric instance', async ({
	logedPage,
	foldersPage,
	metricDefinitionsPage,
	metricInstancesPage,
	customMetricSamplesPage,
	page
}) => {
	await test.step('create required folder', async () => {
		await foldersPage.goto();
		await foldersPage.hasUrl();
		await foldersPage.createItem({
			name: vars.folderName,
			description: vars.description
		});
		// NOTE: creating one more folder not to trip up the autocomplete test utils
		await foldersPage.createItem({
			name: vars.folderName + ' foo',
			description: vars.description
		});
	});

	await test.step('create metric definition', async () => {
		await metricDefinitionsPage.goto();
		await metricDefinitionsPage.hasUrl();
		await metricDefinitionsPage.createItem({
			name: vars.metricDefinitionName,
			description: vars.description,
			folder: vars.folderName,
			category: 'quantitative'
		});
	});

	await test.step('create metric instance', async () => {
		await metricInstancesPage.goto();
		await metricInstancesPage.hasUrl();
		await metricInstancesPage.createItem({
			name: vars.metricInstanceName,
			description: vars.description,
			folder: vars.folderName,
			metric_definition: vars.metricDefinitionName
		});
	});

	await test.step('add a custom metric sample', async () => {
		await metricInstancesPage.viewItemDetail(vars.metricInstanceName);
		await customMetricSamplesPage.createItem(
			{
				timestamp: sampleTimestamp,
				value: sampleValue
			},
			undefined,
			page
		);
	});

	await test.step('check that the sample is listed with its value', async () => {
		const row = customMetricSamplesPage.getRow(sampleValue.toString());
		await expect(row).toBeVisible();
		await expect(row).toContainText(sampleValue.toString());
	});
});
