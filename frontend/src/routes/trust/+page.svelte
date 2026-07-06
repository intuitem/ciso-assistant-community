<script lang="ts">
	import TrustPortal from '$lib/components/TrustPortal/TrustPortal.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

{#if data.portal}
	<TrustPortal portal={data.portal} />
{:else}
	<div
		class="flex min-h-screen items-center justify-center bg-linear-to-br from-surface-100-900 to-surface-200-800"
	>
		<p class="text-surface-500">{m.noPrimaryPortal()}</p>
	</div>
{/if}
