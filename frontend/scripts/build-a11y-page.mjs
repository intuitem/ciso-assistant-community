// Merges docs/accessibility-statement.md with the latest axe-report.json into a
// publishable docs/accessibility.md. Run after an audit: pnpm run a11y:page
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url)); // frontend/scripts
const repoRoot = join(here, '..', '..');
const accessibilityDir = join(here, '..', 'tests', 'reports', 'accessibility');
const statementPath = join(repoRoot, 'docs', 'accessibility-statement.md');
const reportPath = join(accessibilityDir, 'axe-report.json');
const outPath = join(repoRoot, 'docs', 'accessibility.md');

const statement = readFileSync(statementPath, 'utf8').trim();
const reports = JSON.parse(readFileSync(reportPath, 'utf8'));

const passes = (r) => !r.violations.some((v) => v.impact === 'critical' || v.impact === 'serious');
const passed = reports.filter(passes).length;
const axePassed = reports.reduce((n, r) => n + (r.passes ?? 0), 0);
const axeIncomplete = reports.reduce((n, r) => n + (r.incomplete ?? 0), 0);
const axeFailed = reports.reduce((n, r) => n + r.violations.length, 0);
const date = new Date().toISOString().slice(0, 10);

const rows = reports
	.slice()
	.sort((a, b) => a.name.localeCompare(b.name))
	.map((r) => `| ${r.name} | \`${r.path}\` | ${passes(r) ? '✅ Pass' : '❌ Fail'} |`)
	.join('\n');

const evidence = `
---

## Automated test evidence

_Snapshot: ${date}. Tool: axe-core (WCAG 2.1 A & AA), light and dark themes. Horizontal overflow checked at the 1024px minimum supported width._

**Result: ${passed}/${reports.length} screens passed automated checks with no critical or serious violations.**

axe-core, cumulative across screens: **${axePassed} checks passed**, ${axeFailed} failed, ${axeIncomplete} flagged for manual review.

### Results by screen

| Screen | Path | Status |
| --- | --- | --- |
${rows}
`;

writeFileSync(outPath, `${statement}\n${evidence}`);
console.log(`Wrote ${outPath} — ${passed}/${reports.length} screens passed`);
