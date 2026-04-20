import path from 'path';
import fs from 'fs';

import { describe, it, assert, beforeAll, afterAll } from 'vitest';

import { match as urlModelMatch } from '../../params/urlmodel';
import { match as thirdPartyUrlModelMatch } from '../../params/thirdparty_urlmodels';

const TEMP_FILENAME_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';

/** Generate a unique library filename which won't conflict with any of our currently existing libraries. */
function getTempFilename(): string {
	const randomStringLength = 10;
	let randomString = '';

	for (let i = 0; i < randomStringLength; i++) {
		randomString += TEMP_FILENAME_CHARS.charAt(
			Math.floor(Math.random() * TEMP_FILENAME_CHARS.length)
		);
	}

	const tempFilename = `tmp.${randomString}.ts`;
	return tempFilename;
}

/** Match `import SomeComponents from './SomeComponent.svelte';` */
const SVELTE_IMPORT_REGEX = /^import\s+([a-zA-Z0-9_]+)\s+from\s+('.*\.svelte'|".*\.svelte")[\s;]*$/;
/** Match `import { getModelInfo } from './crud';` */
const STANDARD_IMPORT_REGEX =
	/^import\s+{\s*(([a-zA-Z0-9_]+\s+,\s+)*[a-zA-Z0-9_]+)\s*}\s+from\s+('.*?'|".*?")[\s;]*$/;

/** The goal of this function is to patch the content of a typescript library to replace its Svelte component imports by dummy variable definitions.
 *
 * We need this as Vitest fails to compile the codebase svelte components.
 */
function getPatchedLibContent(libContent: string): string {
	// We also replace the following import paths as they also import svelte components.
	// (e.g. we remove `./crud` as `crud.ts` imports `EvidenceFilePreview.svelte`).
	// Note that the import path is relative so it might break sometime in the future.
	const IMPORT_PATH_TO_REPLACE = new Set(['./crud']);

	const lines = libContent.split('\n');

	for (let idx = 0; idx < lines.length; idx++) {
		const line = lines[idx];
		const svelteMatch = line.match(SVELTE_IMPORT_REGEX);

		// Replace every svelte component imports by a fake dummy component definition.
		if (svelteMatch) {
			const importedComponentName = svelteMatch[1];
			const newLine = `const ${importedComponentName} = () => {return { default: {} }};`;

			lines[idx] = newLine;
			continue;
		}

		const match = line.match(STANDARD_IMPORT_REGEX);
		if (match) {
			const importedNamesString = match[1];
			const importedNames = importedNamesString.split(/\s+,\s+/);

			const importedLibExpression = match[3];
			const importedLib = importedLibExpression.slice(1, -1); // Strip quotes.

			if (IMPORT_PATH_TO_REPLACE.has(importedLib)) {
				const dummyObjMembers = importedNames
					.map((importedName) => `${importedName}: null`)
					.join(', ');
				const newLine = `const { ${importedNamesString} } = { ${dummyObjMembers} };`;

				lines[idx] = newLine;
				continue;
			}
		}
	}

	const patchedLibContent = lines.join('\n');
	return patchedLibContent;
}

interface Globals {
	/** File path of the temporary library file (which is a patched version of `$lib/utils/table.ts`). */
	patchedLibPath: string;
	/** Copy of the `filterKeys` variable from `$lib/utils/table.ts`. */
	filterKeys: Set<string>;
	/** Copy of the `fieldSet` variable from `$lib/utils/table.ts`. */
	fieldSet: Set<string>;
}

/** Global variables (initialized by `beforeAll`). */
let globals: Globals;

/** Copy of the `./src/params/filters.ts` `match` function . */
function filtersMatch(param: string): boolean {
	const normalizedParam = param.toLowerCase().replace(/-/g, '_');
	return globals.filterKeys.has(normalizedParam);
}

/** Copy of the `./src/params/fields.ts` `match` function . */
function fieldsMatch(param: string): boolean {
	const normalizedParam = param.toLowerCase().replace(/-/g, '_');
	return globals.fieldSet.has(normalizedParam);
}

function _filterSpecialRoutes(route: string): boolean {
	const firstRouteChar = route[0];
	if (firstRouteChar == '[' || firstRouteChar == '(') {
		return false;
	}
	return true;
}

/** Return `true` if the `param` is valid, or `false` otherwise.
 *
 * This type is meant to be passed as an argument to an `Array.prototype.filter` method.
 */
type ParamFilter = (param: string) => boolean;

/** Ignore special route syntaxes: like `[mode=urlmodel]`, `(internal)`, `[year]` etc... */
function filterSpecialRoutes(verifier: ParamFilter): ParamFilter {
	return (route: string) => _filterSpecialRoutes(route) && verifier(route);
}

/** Return the Set of directory names AND the Set of file names under the `path` path. */
function getDirAndFileNames(path: string): [Set<string>, Set<string>] {
	const dirEntries = fs.readdirSync(path, { withFileTypes: true });

	const directoryNames = dirEntries
		.filter((dirEntry) => dirEntry.isDirectory())
		.map((dirEntry) => dirEntry.name);

	const fileNames = dirEntries
		.filter((dirEntry) => dirEntry.isFile())
		.map((dirEntry) => dirEntry.name);

	return [new Set(directoryNames), new Set(fileNames)];
}

beforeAll(async () => {
	const libPath = path.join(__dirname, 'table.ts');
	const libDir = path.dirname(libPath);

	const patchedLibPath = path.join(libDir, getTempFilename());

	const libContent = fs.readFileSync(libPath, { encoding: 'utf-8' });
	const patchedLibContent = getPatchedLibContent(libContent);

	fs.writeFileSync(patchedLibPath, patchedLibContent, { encoding: 'utf-8' });

	const lib = await import(patchedLibPath);
	const filterKeys = lib.filterKeys;
	const fieldSet = lib.fieldSet;

	globals = { patchedLibPath, filterKeys, fieldSet };
});

afterAll(() => {
	fs.rmSync(globals.patchedLibPath);
});

const BASE_ROUTE_PATH = path.join(__dirname, '../../routes');
const INTERNAL_ROUTE_PATH = path.join(BASE_ROUTE_PATH, '(app)/(internal)');
const THIRD_PARTY_ROUTE_PATH = path.join(BASE_ROUTE_PATH, '(app)/(third-party)');

function getRelativePath(absolutePath: string): string {
	return path.relative(BASE_ROUTE_PATH, absolutePath);
}

/** Check if the route path `routePath` conflicts with the generic route path `conflictRoutePath`.
 *
 * The `fileNameSet` is the of present files under the route path `routePath`, it's used for conflict checking.
 *
 * Example of `routePath`: `${INTERNAL_ROUTE_PATH}/assets`.
 *
 * Example of `conflictRoutePath`: `${INTERNAL_ROUTE_PATH}/[model=urlmodel]`
 */
function checkRouteConflict(
	fileNameSet: Set<string>,
	routePath: string,
	conflictRoutePath: string
) {
	const relativeRoutePath = getRelativePath(routePath);
	const relativeConflictRoutePath = getRelativePath(conflictRoutePath);

	const errorMessage = `File '${relativeRoutePath}/+page.svelte' conflicts with file '${relativeConflictRoutePath}/+server.ts'.
This MUST be fixed by creating a new file '${relativeRoutePath}/+server.ts' which reimplments the request handlers of the +server.ts file the +page.svelte file conflicts with.
This new +server.ts SHALL implement request handlers using "generic*" request handler functions provided by src/lib/utils/api-routes.ts.`;

	const isRouteConflicting = fileNameSet.has('+page.svelte') && !fileNameSet.has('+server.ts');
	assert.equal(!isRouteConflicting, true, errorMessage);
}

/**
 **WARNING:** This test does NOT check for `enterprise/frontend/**` route conflicts yet.

  This test handle route conflicts related to either one of those:

  - `(app)/(internal)/[model=urlmodel]/+server.ts`
  - `(app)/(internal)/[model=urlmodel]/[id=uuid]/+server.ts`
  - `(app)/(internal)/[model=urlmodel]/[id=uuid]/[field=fields]/+server.ts`
  - `(app)/(internal)/[model=urlmodel]/[filter=filters]/+server.ts`
  - `(app)/(third-party)/[model=thirdparty_urlmodels]/+server.ts`
  - `(app)/(third-party)/[model=thirdparty_urlmodels]/[id=uuid]/+server.ts`

  A route conflict occurs when a generic route with a `+server.ts` match another route with a `+page.svelte` but no `+server.ts`.

  Example: If:

  - `(app)/(internal)/assets/+page.svelte` exists.
  - `(app)/(internal)/assets/+server.ts` doesn't exist OR don't contain a `GET` handler then.
  - `(app)/(internal)/[model=urlmodel]/+server.ts` exists WHERE `urlmodel` matches `assets`.

  Then a `GET` request to `/assets` will always get a HTML response from `assets/+page.svelte` instead of a JSON response from `(app)/(internal)/[model=urlmodel]/+server.ts`.

  (This test only checks for missing `+server.ts`, but doesn't check for missing `GET` function inside them.)
*/
describe('checkSveltekitRouteConflicts', () => {
	it('checks route conflicts', () => {
		const [internalRouteSet] = getDirAndFileNames(INTERNAL_ROUTE_PATH);
		const internalRouteList = [...internalRouteSet];

		/** List of routes matching `(app)/(internal)/[model=urlmodel]` */
		const urlmodelRoutes = internalRouteList.filter(filterSpecialRoutes(urlModelMatch));

		for (const route of urlmodelRoutes) {
			const routePath = path.join(INTERNAL_ROUTE_PATH, route);

			const [dirNameSet, fileNameSet] = getDirAndFileNames(routePath);
			const dirNameList = [...dirNameSet];

			// Check conflicts with: (app)/(internal)/[model=urlmodel]/+server.ts
			const conflictRoute = path.join(INTERNAL_ROUTE_PATH, '[model=urlmodel]');
			checkRouteConflict(fileNameSet, routePath, conflictRoute);

			const filterRoutes = dirNameList.filter(filtersMatch);
			for (const filterRoute of filterRoutes) {
				const filterRoutePath = path.join(routePath, filterRoute);

				const [_, fileNameSet] = getDirAndFileNames(filterRoutePath);

				// Check conflicts with: (app)/(internal)/[model=urlmodel]/[filter=filters]/+server.ts
				const conflictRoute = path.join(INTERNAL_ROUTE_PATH, '[model=urlmodel]/[filter=filters]');
				checkRouteConflict(fileNameSet, filterRoutePath, conflictRoute);
			}

			if (dirNameSet.has('[id=uuid]')) {
				const detailedRoutePath = path.join(routePath, '[id=uuid]');

				const [dirNameSet, fileNameSet] = getDirAndFileNames(detailedRoutePath);
				const dirNameList = [...dirNameSet];

				// Check conflicts with: (app)/(internal)/[model=urlmodel]/[id=uuid]/+server.ts
				const conflictRoute = path.join(INTERNAL_ROUTE_PATH, '[model=urlmodel]/[id=uuid]');
				checkRouteConflict(fileNameSet, detailedRoutePath, conflictRoute);

				const fieldRoutes = dirNameList.filter(fieldsMatch);
				for (const fieldRoute of fieldRoutes) {
					const fieldRoutePath = path.join(detailedRoutePath, fieldRoute);

					const [_, fileNameSet] = getDirAndFileNames(fieldRoutePath);

					// Check conflicts with: (app)/(internal)/[model=urlmodel]/[id=uuid]/[field=fields]/+server.ts
					const conflictRoute = path.join(
						INTERNAL_ROUTE_PATH,
						'[model=urlmodel]/[id=uuid]/[field=fields]'
					);
					checkRouteConflict(fileNameSet, fieldRoutePath, conflictRoute);
				}
			}
		}

		const [thirdPartyRouteSet] = getDirAndFileNames(THIRD_PARTY_ROUTE_PATH);
		const thirdPartyRouteList = [...thirdPartyRouteSet];

		/** List of routes matching `(app)/(third-party)/[model=thirdparty_urlmodels]` */
		const thirdPartyUrlmodelRoutes = thirdPartyRouteList.filter(
			filterSpecialRoutes(thirdPartyUrlModelMatch)
		);

		for (const route of thirdPartyUrlmodelRoutes) {
			const routePath = path.join(THIRD_PARTY_ROUTE_PATH, route);

			const [dirNameSet, fileNameSet] = getDirAndFileNames(routePath);

			// Check conflicts with: (app)/(third-party)/[model=thirdparty_urlmodels]/+server.ts
			const conflictRoute = path.join(THIRD_PARTY_ROUTE_PATH, '[model=thirdparty_urlmodels]');
			checkRouteConflict(fileNameSet, routePath, conflictRoute);

			if (dirNameSet.has('[id=uuid]')) {
				const detailedRoutePath = path.join(routePath, '[id=uuid]');

				const [_, fileNameSet] = getDirAndFileNames(detailedRoutePath);

				// Check conflicts with: (app)/(third-party)/[model=thirdparty_urlmodels]/[id=uuid]/+server.ts
				const conflictRoute = path.join(
					THIRD_PARTY_ROUTE_PATH,
					'[model=thirdparty_urlmodels]/[id=uuid]'
				);
				checkRouteConflict(fileNameSet, detailedRoutePath, conflictRoute);
			}
		}
	});
});
