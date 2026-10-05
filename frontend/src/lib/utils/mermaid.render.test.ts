import { beforeEach, describe, expect, it, vi } from 'vitest';

const state = vi.hoisted(() => ({
	dark: false,
	pending: [] as { theme: string; resolve: (svg: string) => void }[],
	theme: 'default'
}));

vi.mock('$lib/utils/echartsTheme', () => ({ isDarkTheme: () => state.dark }));

vi.mock('mermaid', () => ({
	default: {
		initialize: (config: { theme: string }) => {
			state.theme = config.theme;
		},
		render: () => {
			const theme = state.theme;
			return new Promise<{ svg: string }>((resolve) =>
				state.pending.push({ theme, resolve: (svg) => resolve({ svg }) })
			);
		}
	}
}));

const { MERMAID_BLOCK_CLASS, renderMermaidBlocks } = await import('./mermaid');

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

function mountBlock(source: string): HTMLElement {
	const root = document.createElement('div');
	root.innerHTML = `<div class="${MERMAID_BLOCK_CLASS}"><pre><code>${source}</code></pre></div>`;
	document.body.appendChild(root);
	return root;
}

describe('renderMermaidBlocks', () => {
	beforeEach(() => {
		state.dark = false;
		state.pending = [];
		document.body.innerHTML = '';
	});

	it('keeps the newest theme when an older render finishes last', async () => {
		const root = mountBlock('graph TD\n  A-->B');
		const block = root.querySelector<HTMLElement>(`.${MERMAID_BLOCK_CLASS}`)!;

		const light = renderMermaidBlocks(root);
		await settle();
		state.dark = true;
		const dark = renderMermaidBlocks(root);
		await settle();

		const [lightRender, darkRender] = state.pending;
		darkRender.resolve('<svg id="dark"></svg>');
		await dark;
		lightRender.resolve('<svg id="light"></svg>');
		await light;

		expect(block.querySelector('svg')?.id).toBe('dark');
	});

	it('does not cache a stale render under the old theme', async () => {
		const root = mountBlock('graph TD\n  C-->D');

		const light = renderMermaidBlocks(root);
		await settle();
		state.dark = true;
		state.pending[0].resolve('<svg id="stale"></svg>');
		await light;

		state.dark = false;
		const again = renderMermaidBlocks(root);
		await settle();
		expect(state.pending).toHaveLength(2);
		state.pending[1].resolve('<svg id="fresh"></svg>');
		await again;

		expect(root.querySelector('svg')?.id).toBe('fresh');
	});
});
