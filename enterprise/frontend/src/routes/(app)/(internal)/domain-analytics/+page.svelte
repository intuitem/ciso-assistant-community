<script lang="ts">
	import type { PageData } from './$types';
	import TreeView from './TreeView.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<main class="bg-white card p-4">
	<TreeView tree={data.data} />
</main>
