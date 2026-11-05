import { marked } from 'marked';
import sanitizeHtml from 'sanitize-html';

export const sanitizeConfig: sanitizeHtml.IOptions = {
	allowedTags: [
		'p',
		'blockquote',
		'h1',
		'h2',
		'h3',
		'h4',
		'h5',
		'h6',
		'ul',
		'ol',
		'li',
		'strong',
		'em',
		'a',
		'code',
		'pre',
		'table',
		'thead',
		'tbody',
		'tr',
		'th',
		'td',
		'img',
		'hr',
		'br',
		'input',
		'abbr',
		'sup'
	],
	allowedAttributes: {
		a: ['href', 'name', 'target', 'rel'],
		img: ['src', 'alt', 'title', 'width', 'height', 'loading'],
		code: ['class'],
		input: ['type', 'checked', 'disabled'],
		li: ['class'],
		ul: ['class'],
		abbr: ['title']
	},
	allowedSchemes: ['http', 'https'],
	transformTags: {
		a: sanitizeHtml.simpleTransform('a', { rel: 'noopener noreferrer', target: '_blank' }, true)
	}
};

// Untrusted markdown: sanitized, then stripped of links and remote images since the
// caller renders it inside a script-less frame with no network access.
export function markdownToIsolatedHtml(source: string): string {
	return sanitizeHtml(marked(source) as string, {
		...sanitizeConfig,
		allowedTags: sanitizeConfig.allowedTags!.filter((tag: string) => tag !== 'img'),
		allowedAttributes: { ...sanitizeConfig.allowedAttributes, a: [] },
		transformTags: {}
	});
}
