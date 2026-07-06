// Renders the features bento to a PNG by injecting tools/readme/features.json
// into tools/readme/features.html (template) and screenshotting the .bento
// element with headless Chromium. Reuses the Playwright dependency already
// present in the repo (frontend/node_modules, or a root install in CI).
//
// Usage:  node frontend/scripts/render-readme-features.mjs [outPath]
//   default outPath = <repo>/features.png
//
// Resolution note: `@playwright/test` is resolved by walking up from this
// file's directory, so it works both locally (frontend/node_modules) and in CI.

import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const templatePath = path.join(repoRoot, 'tools', 'readme', 'features.html');
const dataPath = path.join(repoRoot, 'tools', 'readme', 'features.json');
const outPath = process.argv[2]
	? path.resolve(process.argv[2])
	: path.join(repoRoot, 'features.png');

const template = fs.readFileSync(templatePath, 'utf8');
const data = fs.readFileSync(dataPath, 'utf8');
const html = template.replace('__FEATURES_JSON__', () => data);

const browser = await chromium.launch();
try {
	const page = await browser.newPage({ deviceScaleFactor: 2 });
	await page.setContent(html, { waitUntil: 'networkidle' });
	await page.waitForSelector('html[data-ready="1"] .bento .card');
	const bento = await page.$('.bento');
	await bento.screenshot({ path: outPath });
	console.log(`Wrote ${outPath}`);
} finally {
	await browser.close();
}
