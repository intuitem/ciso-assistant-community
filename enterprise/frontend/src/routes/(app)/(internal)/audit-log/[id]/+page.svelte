<script lang="ts">
	import RecursiveLogEntryChanges from './components/RecursiveLogEntryChanges.svelte';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';

	let { data } = $props();
	const detailData = { data: data.log, model: { name: 'auditlog', foreignKeyFields: [{field: "actor", urlModel: "users"}]}};
</script>

<main class="flex flex-col space-y-4">
	<DetailView data={detailData} fields={['actor', 'action', 'object_repr', 'timestamp']} />

	<div class="card shadow-lg bg-white p-4">
		<div class="flex w-full">
			<RecursiveLogEntryChanges log={data.log} />
		</div>
	</div>
</main>
