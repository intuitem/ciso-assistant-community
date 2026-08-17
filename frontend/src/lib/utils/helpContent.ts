import { mdPathToSlug, parseHelpSummary, type HelpNavItem } from './helpNav';
import summaryRaw from '../help-nav-summary.md?raw';

const modules = import.meta.glob('/src/lib/help-content/**/*.md', {
	eager: true,
	query: '?raw',
	import: 'default'
}) as Record<string, string>;

const CONTENT_PREFIX = '/src/lib/help-content/';

const contentBySlug: Record<string, string> = {};
for (const [path, raw] of Object.entries(modules)) {
	const relative = path.slice(CONTENT_PREFIX.length);
	contentBySlug[mdPathToSlug(relative)] = raw;
}

export function getHelpDocRaw(slug: string): string | undefined {
	return contentBySlug[slug];
}

export function getHelpNavTree(): HelpNavItem[] {
	return parseHelpSummary(summaryRaw);
}

function flattenTitles(nodes: HelpNavItem[], map: Record<string, string>): void {
	for (const node of nodes) {
		if (node.slug !== null) map[node.slug] = node.title;
		flattenTitles(node.children, map);
	}
}

export function getHelpTitleBySlug(): Record<string, string> {
	const map: Record<string, string> = {};
	flattenTitles(getHelpNavTree(), map);
	return map;
}
