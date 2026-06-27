<script lang="ts">
	import { goto } from '$app/navigation';
	import PortalGrid from '$lib/components/PortalGrid/PortalGrid.svelte';
	import { isSafeExternalUrl } from '$lib/utils/external-links';
	import { m } from '$paraglide/messages';

	let { portal }: { portal: { name: string; branding?: any; sections?: any[] } } = $props();
	const accent = $derived(portal.branding?.accent_color || '#7c3aed');

	function trigger(item: {
		kind: string;
		target?: { url?: string; token?: string; dest?: string };
		snapshot?: { token?: string };
	}) {
		if (item.kind === 'external' && isSafeExternalUrl(item.target?.url))
			window.open(item.target!.url, '_blank', 'noopener,noreferrer');
		else if (item.kind === 'certificationDocument') {
			if (item.target?.dest === 'document' && item.target?.token)
				window.open(`/trust/documents/${item.target.token}`, '_blank', 'noopener,noreferrer');
			else if (isSafeExternalUrl(item.target?.url))
				window.open(item.target!.url, '_blank', 'noopener,noreferrer');
		} else if (item.kind === 'framework' && item.snapshot?.token)
			goto(`/trust/snapshot/${item.snapshot.token}`);
	}
</script>

<svelte:head>
	<title>{portal.name}</title>
</svelte:head>

<div class="min-h-screen bg-linear-to-br from-surface-100-900 to-surface-200-800">
	<header
		class="border-b border-surface-200-800 bg-surface-50-950/80 backdrop-blur"
		style="border-top: 4px solid {accent}"
	>
		<div class="mx-auto flex max-w-5xl items-center gap-4 px-6 py-6">
			{#if portal.branding?.logo_url}
				<img src={portal.branding.logo_url} alt={portal.name} class="h-10 object-contain" />
			{/if}
			<div>
				<h1 class="text-2xl font-bold text-surface-900-100">{portal.name}</h1>
				{#if portal.branding?.tagline}
					<p class="text-sm text-surface-600-400">{portal.branding.tagline}</p>
				{/if}
			</div>
		</div>
	</header>

	<main class="mx-auto max-w-5xl px-6 py-10">
		{#if (portal.sections ?? []).length}
			<PortalGrid sections={portal.sections} onTrigger={trigger} />
		{:else}
			<p class="text-center text-surface-500">{m.noPortalsAvailable()}</p>
		{/if}
	</main>

	<footer class="mx-auto max-w-5xl px-6 py-8 text-center text-xs text-surface-500">
		{m.poweredByCISOAssistant()}
	</footer>
</div>
