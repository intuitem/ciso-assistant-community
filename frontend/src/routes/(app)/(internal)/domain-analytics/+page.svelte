<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import TreeView from './TreeView.svelte';
</script>

<main class="bg-white card p-4">
	<TreeView tree={data.data} />
</main>
