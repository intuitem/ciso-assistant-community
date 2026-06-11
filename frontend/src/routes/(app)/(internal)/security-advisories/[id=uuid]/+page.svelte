<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const toastStore = getToastStore();
	let enriching = $state(false);

	async function enrich() {
		enriching = true;
		try {
			const res = await fetch(`/security-advisories/${data.data.id}/enrich`, {
				method: 'POST'
			});
			const result = await res.json();
			toastStore.trigger({
				message:
					result.detail || result.error || (res.ok ? m.enrichmentComplete() : m.enrichmentFailed()),
				preset: res.ok ? 'success' : 'error'
			});
			if (res.ok) await invalidateAll();
		} catch {
			toastStore.trigger({ message: m.enrichmentFailed(), preset: 'error' });
		}
		enriching = false;
	}
</script>

<DetailView {data}>
	{#snippet actions()}
		<button
			class="btn text-gray-100 bg-linear-to-r from-sky-500 to-cyan-500 h-fit"
			onclick={enrich}
			disabled={enriching}
		>
			{#if enriching}
				<i class="fa-solid fa-spinner fa-spin mr-2"></i>
			{:else}
				<i class="fa-solid fa-cloud-arrow-down mr-2"></i>
			{/if}
			{#if data.data.source === 'EUVD'}
				{m.enrichFromEUVD()}
			{:else}
				{m.enrichFromNVD()}
			{/if}
		</button>
	{/snippet}
</DetailView>
