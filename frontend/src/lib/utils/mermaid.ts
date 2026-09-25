import { isDarkTheme } from '$lib/utils/echartsTheme';

export const MERMAID_BLOCK_CLASS = 'mermaid-diagram';

const MERMAID_CODE_RE = /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g;
const SVG_CACHE_LIMIT = 50;

const svgCache = new Map<string, string>();
let counter = 0;

/** Wraps sanitized mermaid code blocks so they can be swapped for diagrams after mount. */
export function wrapMermaidBlocks(html: string): string {
	return html.replace(
		MERMAID_CODE_RE,
		(block) => `<div class="${MERMAID_BLOCK_CLASS} not-prose">${block}</div>`
	);
}

function cacheSvg(key: string, svg: string) {
	if (svgCache.size >= SVG_CACHE_LIMIT) svgCache.delete(svgCache.keys().next().value!);
	svgCache.set(key, svg);
}

function currentTheme(): 'dark' | 'default' {
	return isDarkTheme() ? 'dark' : 'default';
}

/** Renders every wrapped mermaid block under `root`; blocks that fail to parse keep their source. */
export async function renderMermaidBlocks(root: HTMLElement): Promise<void> {
	const blocks = [...root.querySelectorAll<HTMLElement>(`.${MERMAID_BLOCK_CLASS}`)];
	if (!blocks.length) return;

	const theme = currentTheme();
	const pending: HTMLElement[] = [];
	for (const block of blocks) {
		block.dataset.source ??= block.textContent ?? '';
		const cached = svgCache.get(`${theme}:${block.dataset.source}`);
		if (cached) block.innerHTML = cached;
		else pending.push(block);
	}
	if (!pending.length) return;

	const { default: mermaid } = await import('mermaid');
	mermaid.initialize({
		startOnLoad: false,
		securityLevel: 'strict',
		suppressErrorRendering: true,
		theme
	});

	for (const block of pending) {
		const source = block.dataset.source!;
		try {
			if (currentTheme() !== theme) return;
			const { svg } = await mermaid.render(`mermaid-${++counter}`, source);
			// A theme flip mid-render re-initialises mermaid for the newer pass; drop this one.
			if (currentTheme() !== theme) return;
			cacheSvg(`${theme}:${source}`, svg);
			if (block.isConnected) block.innerHTML = svg;
		} catch {
			block.dataset.error = 'true';
		}
	}
}

/** Renders mermaid blocks under `root` and re-renders them when the dark theme flips. */
export function mountMermaidBlocks(root: HTMLElement): () => void {
	if (!root.querySelector(`.${MERMAID_BLOCK_CLASS}`)) return () => {};
	renderMermaidBlocks(root);
	let dark = isDarkTheme();
	const observer = new MutationObserver(() => {
		if (isDarkTheme() === dark) return;
		dark = !dark;
		renderMermaidBlocks(root);
	});
	observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
	return () => observer.disconnect();
}
