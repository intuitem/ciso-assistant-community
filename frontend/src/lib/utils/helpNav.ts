export interface HelpNavItem {
	title: string;
	slug: string | null;
	children: HelpNavItem[];
}

/**
 * Converts a GitBook-relative markdown path (e.g. "guides/initial-setup.md",
 * "installation/README.md") into a /help route slug ("guides/initial-setup",
 * "installation"). A bare "README.md" maps to the empty slug (the /help index).
 */
export function mdPathToSlug(path: string): string {
	const noExt = path.replace(/\.md$/i, '');
	return noExt.replace(/(^|\/)README$/i, '$1').replace(/\/$/, '');
}

/**
 * Parses product-docs/SUMMARY.md's nested GitBook link list into a nav tree.
 * "## Section" headings become top-level groups; "* [Title](path.md)" bullets
 * become linked entries; plain "* Text" bullets become unlinked group labels.
 * Nesting depth is derived from 2-space indentation, matching GitBook's format.
 */
export function parseHelpSummary(raw: string): HelpNavItem[] {
	const root: HelpNavItem[] = [];
	let currentSection: HelpNavItem | null = null;
	const stack: { depth: number; node: HelpNavItem }[] = [];

	for (const line of raw.split('\n')) {
		const sectionMatch = line.match(/^##\s+(.+)$/);
		if (sectionMatch) {
			currentSection = { title: sectionMatch[1].trim(), slug: null, children: [] };
			root.push(currentSection);
			stack.length = 0;
			continue;
		}

		const bulletMatch = line.match(/^(\s*)\*\s+(.+)$/);
		if (!bulletMatch) continue;

		const depth = Math.floor(bulletMatch[1].length / 2);
		const text = bulletMatch[2].trim();
		const linkMatch = text.match(/^\[(.+?)\]\(([^)]+)\)$/);
		const node: HelpNavItem = linkMatch
			? { title: linkMatch[1], slug: mdPathToSlug(linkMatch[2]), children: [] }
			: { title: text, slug: null, children: [] };

		while (stack.length && stack[stack.length - 1].depth >= depth) {
			stack.pop();
		}

		const parent = stack.length ? stack[stack.length - 1].node : currentSection;
		if (parent) {
			parent.children.push(node);
		} else {
			root.push(node);
		}

		stack.push({ depth, node });
	}

	return root;
}
