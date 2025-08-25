<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<main class="bg-white card p-4">
	<ModelTable
		source={{ ...data.table }}
		URLModel="audit-log"
		baseEndpoint="/audit-log"
		fields={['actor', 'action', 'content_type', 'timestamp', 'folder']}
	/>
</main>
