<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	{#snippet actions()}
		<form method="POST" action="?/enrich">
			<input type="hidden" name="id" value={data.data.id} />
			<button class="btn text-gray-100 bg-linear-to-r from-sky-500 to-cyan-500 h-fit" type="submit">
				<i class="fa-solid fa-cloud-arrow-down mr-2"></i>
				{m.enrichFromNVD()}
			</button>
		</form>
	{/snippet}
</DetailView>
