<script lang="ts">
	interface Props {
		body: string;
		css?: string;
		title: string;
		class?: string;
	}

	let { body, css = '', title, class: className = 'w-full h-[70vh]' }: Props = $props();

	const srcdoc = $derived(
		`<!doctype html><html><head><meta charset="utf-8">` +
			`<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'">` +
			`<style>${css}</style></head><body>${body}</body></html>`
	);
</script>

<iframe
	{srcdoc}
	{title}
	sandbox=""
	class="{className} bg-white rounded border border-surface-200-800"
></iframe>
