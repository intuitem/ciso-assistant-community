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
			'br'
		],
		allowedAttributes: {
			a: ['href', 'name', 'target', 'rel'],
			img: ['src', 'alt', 'title', 'width', 'height', 'loading'],
			code: ['class']
		},
		allowedSchemes: ['http', 'https', 'mailto'],
		transformTags: {
			a: sanitizeHtml.simpleTransform('a', { rel: 'noopener noreferrer', target: '_blank' }, true)
		}
	};

	let renderedContent = $derived(() => {
		if (!content || content.trim() === '') return '';
		const html = marked(content) as string;
		return sanitizeHtml(html, sanitizeConfig);
	});
</script>

{#if renderedContent}
	<div class="prose prose-sm max-w-none {className}">
		{@html renderedContent}
	</div>
{:else}
	<span class="text-gray-500 italic">--</span>
{/if}
