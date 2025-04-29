<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<DetailView {data} displayModelTable={data.data.is_recurrent} exclude={data.data.is_recurrent ? ['observation', 'evidences'] : [] } />
