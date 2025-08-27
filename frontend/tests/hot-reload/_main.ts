// We can import types for the IDE even if the import path is not a relative path (like '@playwright/test').
// This is fine since the hot reloader compiler will strip any type-only import declarations.
import type { Page as _Page } from '@playwright/test';
import type { EntryPoint } from '../utilsv2/core/hot-reloader';

// This works as $lib is kind of an indirect relative path.
import { safeTranslate } from '$lib/utils/i18n';

import { LoginPage } from './derived/login-page';
import { LibraryListViewPage } from './derived/list-view';
import { ADMIN_EMAIL, ADMIN_PASSWORD } from './core/test-data';

/**
 * Hot-reloader main function (indirect entry point).
 *
 * @param {Object} context - Context object injected by Playwright.
 * @param {Function} context.test - The Playwright test function used to define tests.
 * @param {Function} context.expect - The assertion utility provided by Playwright.
 * @param {Object} context.allFixtures - The allFixtures fixture which is an object containing all fixtures.
 * @param {number} context.counter - A counter starting from 0 incremented each time the hot reloader loops.
 * @param {HotReload} context.HotReload - This class can be used to directly control the hot reloader from within the hot-reloaded code itself.
 */
const main = (async ({ test, expect, allFixtures, counter, HotReload }) => {
	// We can get access to all the fixtures by destructuring allFixtures.
	const { page } = allFixtures;

	let ACTION: number;
	await (
		[
			async () => {
				// ACTION = 0 (Stop the test loop)
				HotReload.doStop(Math.random());
				HotReload.doStopTest();
			},
			async () => {
				// ACTION = 1 (Restart the test)
				// Restarts the test and the browser with it (only works if the value returned by EX() is changed
				// The EX() value exists so that the current test is only stopped once (for a simple restart)
				HotReload.doStop(EX());
			},
			async () => {
				// ACTION = 2 (Log in to the application)
				const loginPage = new LoginPage(page);
				await loginPage.gotoSelf();
				const analyticsPage = await loginPage.doLoginP(ADMIN_EMAIL, ADMIN_PASSWORD);
				await analyticsPage.doCloseModal();
			},
			async () => {
				// ACTION = 3 (Navigates to the library list view)
				const listView = new LibraryListViewPage(page);
				await listView.gotoSelf();
				// m.firstTimeLoginModalTitle() can't be used directly in the hot reloader so we use safeTranslate instead.
				// As you can see the console.log output can be seen in the console each time it's being executed which is nice for debugging.
				console.log('Output:', safeTranslate('firstTimeLoginModalTitle'));
			}
			// ACTION = 2 selects the action at index 2 which is the login action.
		][(ACTION = 2)] ?? (() => {})
	)();
	// Each action is an async function defined in an array.
	// [(ACTION = {IDX})] selects the action at index {IDX} as the function to be executed.
	// Every time a hot-reloaded module is modified (either main.ts or something directly/indirectly imported by main.ts) the main.ts file (and therefore the {IDX} action) will be re-executed.
	// So to re-execute an action you just have to modify any hot-reloaded code, and if you change the {IDX} value it will directly executes the newly selected action as {IDX} is a part of the main.ts code.
	function EX() {
		// Modify this value if you want [ACTION = 1] (The test restart action) to work.
		// This value is stored in the EX() function to make it convenient to modify it quickly.
		// Modifying this value also serves as a quick way to re-execute the current action.
		return '1111111111111111111111111111111111111111111111111111';
	}
}) satisfies EntryPoint;

//// Commands to pass the hot reloaded code to the real utilsv2 codebase/the other way around:
// Overwrite the hot-reload content with the utilsv2 content
// rm -rf hot-reload/core hot-reload/base hot-reload/derived && cp -r utilsv2/* hot-reload

// Overwrite the utilsv2 content  with hot-reload content
// rm -rf utilsv2/* && cp -r hot-reload/core hot-reload/base hot-reload/derived utilsv2

const _start = (async (args) => {
	console.log(`[${new Date().toLocaleTimeString('fr-FR')}] hot reload update.`);
	// Used to avoid blocking the event loop with the main function execution.
	// Change the timeout as you wish.
	const MAIN_FUNCTION_TIMEOUT = 60_000;
	await Promise.race([main(args), new Promise((res) => setTimeout(res, MAIN_FUNCTION_TIMEOUT))]);
}) satisfies EntryPoint;
