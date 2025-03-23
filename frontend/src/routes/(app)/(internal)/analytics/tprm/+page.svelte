<script lang="ts">
	import FlippableCard from './FlippableCard.svelte';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

{#if data.data && data.data.length > 0}
	<div class="card bg-white bg-stripes-pink">
		<div class="p-6 bg-white bg-opacity-85">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
				{#each data.data as entity_assessment}
					<FlippableCard {entity_assessment} />
				{/each}
			</div>
		</div>
	</div>
{:else}
	<div class="p-4">No data available for now.</div>
{/if}

<style>
	.bg-stripes-pink {
		background-image: linear-gradient(
			135deg,
			#07275e 10%,
			transparent 0,
			transparent 50%,
			#07275e 0,
			#07275e 60%,
			transparent 0,
			transparent
		);
		background-size: 7.07px 7.07px;
	}
</style>
