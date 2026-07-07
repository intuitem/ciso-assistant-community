// Generates the collapsible, keyword-searchable feature list in README.md from
// tools/readme/features.json. Pure Node (no browser) so it is deterministic and
// cheap enough to run in a read-only CI verify step.
//
// It replaces the content between these markers in README.md:
//   <!-- FEATURES:START ... -->  ...generated...  <!-- FEATURES:END -->
//
// Usage:  node frontend/scripts/generate-readme-list.mjs
// CI verify pattern: run it, then `git diff --exit-code README.md`.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const dataPath = path.join(repoRoot, 'tools', 'readme', 'features.json');
const readmePath = path.join(repoRoot, 'README.md');

const START = '<!-- FEATURES:START -->';
const END = '<!-- FEATURES:END -->';

const { groups, features } = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

// Group features, preserving the order declared in `groups` and, within a
// group, the order they appear in the array. Any feature whose group is not in
// `groups` is collected under an "Other" heading so nothing is silently dropped.
const byGroup = new Map(groups.map((g) => [g, []]));
for (const f of features) {
	if (!byGroup.has(f.group)) byGroup.set(f.group, []);
	byGroup.get(f.group).push(f.name);
}

const sections = [];
for (const [group, names] of byGroup) {
	if (names.length === 0) continue;
	sections.push(`**${group}**`);
	sections.push(...names.map((n) => `- ${n}`));
	sections.push('');
}

const block = [
	START,
	'<details>',
	`<summary><strong>📋 Full feature list</strong> — click to expand (searchable, ${features.length} features)</summary>`,
	'',
	...sections,
	'</details>',
	END
].join('\n');

const readme = fs.readFileSync(readmePath, 'utf8');
const pattern = new RegExp(
	`${START.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[\\s\\S]*?${END.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`
);

if (!pattern.test(readme)) {
	console.error(
		`Markers not found in README.md. Add this where the list should go:\n\n${START}\n${END}\n`
	);
	process.exit(1);
}

const updated = readme.replace(pattern, block);
if (updated === readme) {
	console.log('README.md feature list already up to date.');
} else {
	fs.writeFileSync(readmePath, updated);
	console.log(`Updated README.md feature list (${features.length} features).`);
}
