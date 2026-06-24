// Generates a single publish-ready accessibility page by merging the
// hand-written statement (docs/accessibility-statement.md) with the latest
// automated test results (tests/reports/accessibility/axe-report.json).
// Run after an audit:  pnpm run a11y:page
import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url)); // frontend/scripts
const repoRoot = join(here, '..', '..');
const accessibilityDir = join(here, '..', 'tests', 'reports', 'accessibility');
const statementPath = join(repoRoot, 'docs', 'accessibility-statement.md');
const reportPath = join(accessibilityDir, 'axe-report.json');
const lighthouseDir = join(accessibilityDir, 'lighthouse');
const outPath = join(repoRoot, 'docs', 'accessibility.md');

const statement = readFileSync(statementPath, 'utf8').trim();
const reports = JSON.parse(readFileSync(reportPath, 'utf8'));

const passes = (r) => !r.violations.some((v) => v.impact === 'critical' || v.impact === 'serious');
const passed = reports.filter(passes).length;
const axePassed = reports.reduce((n, r) => n + (r.passes ?? 0), 0);
const axeIncomplete = reports.reduce((n, r) => n + (r.incomplete ?? 0), 0);
const axeFailed = reports.reduce((n, r) => n + r.violations.length, 0);
const date = new Date().toISOString().slice(0, 10);

// Only trust Lighthouse scores that didn't redirect to /login (authenticated
// Lighthouse is flaky in batch; we publish only verified, non-redirected runs).
let lighthouse = [];
if (existsSync(lighthouseDir)) {
	lighthouse = readdirSync(lighthouseDir)
		.filter((f) => f.endsWith('.json'))
		.map((f) => JSON.parse(readFileSync(join(lighthouseDir, f), 'utf8')))
		.filter((x) =>
			x.path === '/login'
				? String(x.finalUrl).includes('/login')
				: !String(x.finalUrl).includes('/login')
		)
		.sort((a, b) => a.name.localeCompare(b.name));
}
const lighthouseRows = lighthouse
	.map((x) => `| ${x.name} | \`${x.path}\` | ${x.score}/100 |`)
	.join('\n');

const rows = reports
	.slice()
	.sort((a, b) => a.name.localeCompare(b.name))
	.map((r) => `| ${r.name} | \`${r.path}\` | ${passes(r) ? '✅ Pass' : '❌ Fail'} |`)
	.join('\n');

const lighthouseSection = lighthouse.length
	? `
### Lighthouse Accessibility score

_Google Lighthouse provides a 0–100 score. Per Google, it is a health indicator, **not** a measure of WCAG/RGAA conformance._

| Screen | Path | Score |
| --- | --- | --- |
${lighthouseRows}
`
	: '';

const evidence = `
---

## Automated test evidence

_Snapshot: ${date}. Tools: axe-core (WCAG 2.1 A & AA), light and dark themes; Google Lighthouse. Horizontal overflow checked at the 1024px minimum supported width._

**Result: ${passed}/${reports.length} screens passed automated checks with no critical or serious violations.**

axe-core, cumulative across screens: **${axePassed} checks passed**, ${axeFailed} failed, ${axeIncomplete} flagged for manual review.

### axe-core results by screen

| Screen | Path | Status |
| --- | --- | --- |
${rows}
${lighthouseSection}`;

writeFileSync(outPath, `${statement}\n${evidence}`);
console.log(`Wrote ${outPath} — ${passed}/${reports.length} screens passed`);
