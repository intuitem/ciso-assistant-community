import { marked } from 'marked';
import posixPath from 'node:path/posix';

export interface ParsedHelpDoc {
	description?: string;
	html: string;
}

function extractFrontMatter(raw: string): { description?: string; body: string } {
	const match = raw.match(/^---\n([\s\S]*?)\n---\n?/);
	if (!match) return { body: raw };

	const frontMatter = match[1];
	const body = raw.slice(match[0].length);

	const singleLine = frontMatter.match(/^description:\s*(.+)$/m);
	if (singleLine && !/^[>|]/.test(singleLine[1].trim())) {
		return { description: singleLine[1].trim(), body };
	}

	const folded = frontMatter.match(/^description:\s*[>|]-?\s*\n((?:[ \t]+.+\n?)+)/m);
	if (folded) {
		const description = folded[1]
			.split('\n')
			.map((line) => line.trim())
			.filter(Boolean)
			.join(' ');
		return { description, body };
	}

	return { body };
}

function convertHints(text: string, blocks: string[]): string {
	return text.replace(
		/\{%\s*hint\s+style="([a-z]+)"\s*%\}([\s\S]*?)\{%\s*endhint\s*%\}/g,
		(_match, style: string, inner: string) => {
			const innerHtml = marked(inner.trim()) as string;
			const token = `@@HELP_BLOCK_${blocks.length}@@`;
			blocks.push(`<div class="help-hint help-hint-${style}">${innerHtml}</div>`);
			return token;
		}
	);
}

function convertEmbeds(text: string): string {
	const withBody = text.replace(
		/\{%\s*embed\s+url="([^"]+)"\s*%\}([\s\S]*?)\{%\s*endembed\s*%\}/g,
		(_match, url: string, label: string) => {
			const trimmedLabel = label.trim();
			return `[▶ ${trimmedLabel || 'Watch video'}](${url})`;
		}
	);
	return withBody.replace(
		/\{%\s*embed\s+url="([^"]+)"\s*%\}/g,
		(_match, url: string) => `[▶ Watch video](${url})`
	);
}

function stripRemainingGitbookTags(text: string): string {
	return text.replace(/\{%[^%]*%\}/g, '');
}

function rewriteAssetPaths(text: string): string {
	return text.replace(
		/(!\[[^\]]*\]\()(?:\.\.\/)*\.gitbook\/assets\/([^)]+)(\))/g,
		(_match, prefix: string, file: string, suffix: string) =>
			`${prefix}/help-assets/${file}${suffix}`
	);
}

function rewriteInternalLinks(text: string, currentDir: string): string {
	return text.replace(/\]\(([^)]+)\)/g, (match, target: string) => {
		if (/^(https?:)?\/\//.test(target) || target.startsWith('/help-assets/')) return match;
		if (target.startsWith('#')) return match;
		const [pathPart, fragment] = target.split('#');
		if (!pathPart.endsWith('.md')) return match;

		const resolved = posixPath.normalize(posixPath.join(currentDir, pathPart));
		const slug = resolved.replace(/\.md$/i, '').replace(/(^|\/)README$/i, '$1');
		const href = `/help/${slug}${fragment ? `#${fragment}` : ''}`;
		return `](${href})`;
	});
}

function reinsertBlocks(html: string, blocks: string[]): string {
	return html.replace(
		/<p>@@HELP_BLOCK_(\d+)@@<\/p>|@@HELP_BLOCK_(\d+)@@/g,
		(_match, wrapped: string | undefined, bare: string | undefined) => {
			const index = Number(wrapped ?? bare);
			return blocks[index] ?? '';
		}
	);
}

/**
 * Renders a GitBook-flavoured markdown document (from product-docs/) into
 * sanitizer-free HTML. Content is trusted/build-time bundled, not user input,
 * so this intentionally skips sanitize-html (unlike MarkdownRenderer.svelte,
 * which handles untrusted user-entered descriptions).
 */
export function renderHelpDoc(raw: string, slug: string): ParsedHelpDoc {
	const { description, body } = extractFrontMatter(raw);
	const currentDir = posixPath.dirname(slug === '' ? '.' : slug);

	const blocks: string[] = [];
	let text = convertHints(body, blocks);
	text = convertEmbeds(text);
	text = stripRemainingGitbookTags(text);
	text = rewriteAssetPaths(text);
	text = rewriteInternalLinks(text, currentDir);

	const html = reinsertBlocks(marked(text) as string, blocks);
	return { description, html };
}
