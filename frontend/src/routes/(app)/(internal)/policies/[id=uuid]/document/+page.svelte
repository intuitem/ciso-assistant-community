<script lang="ts">
	import DocumentEditor from '$lib/components/DocumentEditor/DocumentEditor.svelte';
	let { data } = $props();
</script>

<DocumentEditor
	parent={data.policy}
	{data}
	proxyBase={`/policies/${data.policy.id}/document`}
	backHref={`/policies/${data.policy.id}`}
	createParentField="policy"
/>
