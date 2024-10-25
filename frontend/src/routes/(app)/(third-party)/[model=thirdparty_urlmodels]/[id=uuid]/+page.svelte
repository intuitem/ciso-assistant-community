<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<DetailView {data} />
