<script lang="ts">
	import FlippableCard from './FlippableCard.svelte';
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

{#if data.data && data.data.length > 0}
	<div
		class="p-6 bg-white bg-opacity-95 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
		role="list"
		data-testid="cards-list"
	>
		{#each data.data as entity_assessment}
			<FlippableCard {entity_assessment} />
		{/each}
	</div>
{:else}
	<div class="p-4" data-testid="no-data-available">{m.noDataAvailable()}</div>
{/if}
