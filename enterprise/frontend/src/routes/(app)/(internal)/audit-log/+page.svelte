<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
</script>

<main class="bg-white card p-4">
	<ModelTable
		source={{
			head: {
				actor: 'actor',
				action: 'action',
				content_type: 'content_type',
				timestamp: 'timestamp'
			},
			body: [],
			meta: []
		}}
		URLModel="audit-log"
		baseEndpoint="/audit-log"
		fields={['actor', 'action', 'content_type', 'timestamp']}
	/>
</main>
