<script lang="ts">
	import { marked } from 'marked';
	import sanitizeHtml from 'sanitize-html';

	interface Props {
		content: string | null | undefined;
		class?: string;
	}

	let { content, class: className = '' }: Props = $props();

	const sanitizeConfig: sanitizeHtml.IOptions = {
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
			'input'
		],
		allowedAttributes: {
			a: ['href', 'name', 'target', 'rel'],
			img: ['src', 'alt', 'title', 'width', 'height', 'loading'],
			code: ['class'],
			input: ['type', 'checked', 'disabled'],
			li: ['class'],
			ul: ['class']
		},
		allowedSchemes: ['http', 'https'],
		transformTags: {
			a: sanitizeHtml.simpleTransform('a', { rel: 'noopener noreferrer', target: '_blank' }, true)
		}
	};

	function processContent(content: string | null | undefined): string {
		if (!content || content.trim() === '') return '';

		let html = marked(content) as string;
		html = sanitizeHtml(html, sanitizeConfig);

		// Clean up excessive spacing
		html = html
			.replace(/>\s+</g, '><') // Remove whitespace between tags
			.replace(/\n\s*\n/g, '\n') // Remove double line breaks
			.replace(/<\/p>\s*<ul>/g, '</p><ul>') // Remove space between paragraphs and lists
			.replace(/<\/ul>\s*<p>/g, '</ul><p>') // Remove space between lists and paragraphs
			.replace(/<\/p>\s*<ol>/g, '</p><ol>') // Remove space between paragraphs and ordered lists
			.replace(/<\/ol>\s*<p>/g, '</ol><p>'); // Remove space between ordered lists and paragraphs

		return html;
	}

	let renderedContent = $derived(processContent(content));
</script>

{#if renderedContent}
	<div class="prose prose-sm max-w-none break-all whitespace-pre-line {className}">
		{@html renderedContent}
	</div>
{:else}
	<span class="text-gray-500 italic">--</span>
{/if}
