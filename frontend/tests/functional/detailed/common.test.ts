import {
	test,
	expect,
	setHttpResponsesListener,
	TestContent,
	replaceValues
} from '../../utils/test-utils.js';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { dirname } from 'path';

let items: { [k: string]: any } = TestContent.itemBuilder();
let history: any = {};

function setFilePath(projectName: string, retry: number) {
	file_path = `./tests/utils/.testhistory/${projectName}/hist${retry}.json`;
	mkdirSync(dirname(file_path), { recursive: true });
	return file_path;
}

let file_path = '';
const testPages = Object.keys(items);

test.describe.configure({ mode: 'serial' });
for (const key of testPages) {
	test.describe(`Tests on ${items[key].displayName.toLowerCase()} item`, () => {
		test.beforeAll(async ({}, testInfo) => {
			setFilePath(testInfo.project.name, testInfo.retry);
			existsSync(file_path)
				? (history = JSON.parse(readFileSync(file_path, 'utf8')))
				: writeFileSync(file_path, JSON.stringify(history));
		});

		test.describe(`Tests on ${items[key].displayName.toLowerCase()} item details`, () => {
			test.beforeEach(async ({ logedPage, pages, page }, testInfo) => {
				await pages[key].goto();
				await expect(page).toHaveURL(pages[key].url);

				if (testInfo.line in history) {
					items = history[testInfo.line];
				} else {
					items = TestContent.itemBuilder();
					history[testInfo.line] = items;
				}

				setHttpResponsesListener(page);

				await pages[key].waitUntilLoaded();
				await pages[key].createItem(
					items[key].build,
					'dependency' in items[key] ? items[key].dependency : null
				);

				if (await pages[key].getRow(items[key].build.name || items[key].build.email).isHidden()) {
					await pages[key].searchInput.fill(items[key].build.name || items[key].build.email);
				}

				await pages[key].waitUntilLoaded();
				await pages[key].viewItemDetail(items[key].build.name || items[key].build.email);
				await pages[key].itemDetail.hasTitle(items[key].build.name || items[key].build.email);
				await pages[key].itemDetail.hasBreadcrumbPath([
					items[key].displayName,
					items[key].build.name || items[key].build.email
				]);
				//wait fore the file to load to prevent crashing
				page.url().includes('evidences')
					? await pages[key].page.getByTestId('attachment-name-title').waitFor({ state: 'visible' })
					: null;
			});

			test(`${items[key].displayName} item details are showing properly`, async ({
				pages,
				page
			}) => {
				await pages[key].itemDetail.verifyItem(items[key].build);
				await pages[key].checkForUndefinedText();
				page.url().includes('evidences') ? await pages[key].page.waitForTimeout(1000) : null; // prevent crashing
			});

			test(`user can edit ${items[key].displayName.toLowerCase()} item`, async ({
				pages,
				page
			}, testInfo) => {
				const editedValues = await pages[key].itemDetail.editItem(
					items[key].build,
					items[key].editParams
				);
				for (const editedKey of Object.keys(editedValues)) {
					replaceValues(
						history[testInfo.line],
						items[key].build[editedKey],
						editedKey === 'name'
							? items[key].build.name + ' edited'
							: items[key].build.email
								? '_' + items[key].build.email
								: editedValues[editedKey]
					);
				}
				//wait fore the file to load to prevent crashing
				page.url().includes('evidences')
					? await pages[key].page.getByTestId('attachment-name-title').waitFor({ state: 'visible' })
					: null;

				await pages[key].itemDetail.verifyItem(editedValues);
			});
		});

		test.afterAll(async () => {
			writeFileSync(file_path, JSON.stringify(history));
		});
	});
}
