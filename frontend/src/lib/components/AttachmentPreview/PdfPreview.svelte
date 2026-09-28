<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		src: string;
		title?: string;
		class?: string;
	}

	let { src, title = '', class: className = 'h-[70vh] w-full' }: Props = $props();

	let status = $state<'loading' | 'ready' | 'failed'>('loading');
	let objectUrl = $state('');

	// The file is fetched into a blob rather than pointed at directly: hosted
	// deployments answer every request with X-Frame-Options: DENY, which blocks
	// embedding even same-origin. A blob: URL carries no response headers.
	$effect(() => {
		const source = src;
		let disposed = false;
		let url = '';
		status = 'loading';
		objectUrl = '';

		(async () => {
			try {
				const res = await fetch(source);
				if (!res.ok) throw new Error(String(res.status));
				const blob = await res.blob();
				if (disposed) return;
				url = URL.createObjectURL(
					blob.type === 'application/pdf' ? blob : new Blob([blob], { type: 'application/pdf' })
				);
				objectUrl = url;
				status = 'ready';
			} catch {
				if (!disposed) status = 'failed';
			}
		})();

		return () => {
			disposed = true;
			if (url) URL.revokeObjectURL(url);
		};
	});
</script>

{#if status === 'loading'}
	<p class="text-sm text-surface-500">{m.loading()}...</p>
{:else if status === 'failed'}
	<p class="text-center text-sm font-bold">{m.NoPreviewMessage()}</p>
{:else}
	<embed
		src={objectUrl}
		type="application/pdf"
		{title}
		class="{className} rounded-xl border border-surface-200-800"
	/>
{/if}
