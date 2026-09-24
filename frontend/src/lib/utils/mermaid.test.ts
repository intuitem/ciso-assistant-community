import { describe, expect, it } from 'vitest';
import { marked } from 'marked';
import sanitizeHtml from 'sanitize-html';
import { sanitizeConfig } from './markdown';
import { MERMAID_BLOCK_CLASS, wrapMermaidBlocks } from './mermaid';

const render = (md: string) => wrapMermaidBlocks(sanitizeHtml(marked(md) as string, sanitizeConfig));

describe('wrapMermaidBlocks', () => {
	it('wraps mermaid fenced blocks', () => {
		const html = render('```mermaid\ngraph TD\n  A-->B\n```');
		expect(html).toContain(`<div class="${MERMAID_BLOCK_CLASS} not-prose">`);
		expect(html).toContain('A--&gt;B');
	});

	it('leaves other code blocks alone', () => {
		const html = render('```python\nprint(1)\n```\n\n```\nplain\n```');
		expect(html).not.toContain(MERMAID_BLOCK_CLASS);
	});

	it('keeps markup inside the source escaped', () => {
		const html = render('```mermaid\ngraph TD\n  A["<img src=x onerror=alert(1)>"]\n```');
		expect(html).toContain(MERMAID_BLOCK_CLASS);
		expect(html).not.toContain('<img');
	});

	it('wraps every block independently', () => {
		const html = render('```mermaid\ngraph TD\nA-->B\n```\n\ntext\n\n```mermaid\npie\n"a": 1\n```');
		expect(html.match(new RegExp(MERMAID_BLOCK_CLASS, 'g'))).toHaveLength(2);
		expect(html).toContain('<p>text</p>');
	});
});
