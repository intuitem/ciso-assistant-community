import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

export const REPORT_DIR = join(__dirname, '..', 'reports', 'accessibility');
export const PAGES_DIR = join(REPORT_DIR, 'pages');

export type Severity = 'critical' | 'serious' | 'moderate' | 'minor';

export interface PageReport {
	name: string;
	path: string;
	violations: {
		id: string;
		impact: Severity | null;
		help: string;
		helpUrl: string;
		wcagTags: string[];
		nodes: number;
		sample: { target: string; html: string }[];
	}[];
}

/** Written once per audited page, immediately — survives Playwright worker restarts on failure. */
export function writePageReport(report: PageReport): void {
	if (!existsSync(PAGES_DIR)) mkdirSync(PAGES_DIR, { recursive: true });
	writeFileSync(join(PAGES_DIR, `${report.name}.json`), JSON.stringify(report, null, 2));
}

/** Global setup: wipe previous run's per-page files so stale pages don't linger. */
export function cleanReports(): void {
	rmSync(PAGES_DIR, { recursive: true, force: true });
}

/** Global teardown: fold per-page files into a combined json + markdown report. */
export function aggregateReports(): void {
	if (!existsSync(PAGES_DIR)) return;
	const reports: PageReport[] = readdirSync(PAGES_DIR)
		.filter((f) => f.endsWith('.json'))
		.map((f) => JSON.parse(readFileSync(join(PAGES_DIR, f), 'utf-8')) as PageReport)
		.sort((a, b) => a.name.localeCompare(b.name));
	if (!reports.length) return;

	writeFileSync(join(REPORT_DIR, 'axe-report.json'), JSON.stringify(reports, null, 2));

	const order: Severity[] = ['critical', 'serious', 'moderate', 'minor'];
	const total = reports.reduce((n, r) => n + r.violations.length, 0);

	const lines: string[] = [
		'# Accessibility audit (axe-core / WCAG 2.1 AA)',
		'',
		'> Automated scan only. Covers ~30% of WCAG SC fully and ~62% of RGAA criteria partially.',
		'> Keyboard, screen-reader, multimedia and content criteria still need a manual RGAA audit.',
		'',
		`**Pages scanned:** ${reports.length} — **violation types:** ${total}`,
		'',
		'## Per-page summary',
		'',
		'| Page | Path | Critical | Serious | Moderate | Minor |',
		'| --- | --- | --- | --- | --- | --- |'
	];
	for (const r of reports) {
		const c = (s: Severity) => r.violations.filter((v) => v.impact === s).length;
		lines.push(
			`| ${r.name} | \`${r.path}\` | ${c('critical')} | ${c('serious')} | ${c('moderate')} | ${c('minor')} |`
		);
	}

	lines.push('', '## Violations by rule', '');
	for (const r of reports) {
		if (!r.violations.length) continue;
		lines.push(`### ${r.name} (\`${r.path}\`)`, '');
		const sorted = [...r.violations].sort(
			(a, b) => order.indexOf(a.impact ?? 'minor') - order.indexOf(b.impact ?? 'minor')
		);
		for (const v of sorted) {
			lines.push(
				`- **[${v.impact}] ${v.id}** (${v.nodes} element(s)) — ${v.help}  ` +
					`\n  WCAG: ${v.wcagTags.join(', ') || 'n/a'} · [details](${v.helpUrl})`
			);
		}
		lines.push('');
	}

	writeFileSync(join(REPORT_DIR, 'axe-report.md'), lines.join('\n'));
	console.log(`\n♿ Accessibility report written to ${REPORT_DIR}/axe-report.md`);
}
