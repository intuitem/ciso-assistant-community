<script lang="ts">
	import TrustPortal from '$lib/components/TrustPortal/TrustPortal.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<TrustPortal portal={data.portal} />
