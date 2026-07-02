<script lang="ts">
	import DocumentEditor from '$lib/components/DocumentEditor/DocumentEditor.svelte';
	import UploadedDocumentView from '$lib/components/DocumentEditor/UploadedDocumentView.svelte';
	let { data } = $props();

	let isUploaded = $derived(data.currentRevision?.source === 'uploaded');
	const proxyBase = `/document-containers/${data.container.id}/document`;
</script>

{#if isUploaded}
	<UploadedDocumentView parent={data.container} {data} {proxyBase} backHref="/documents" />
{:else}
	<DocumentEditor
		parent={data.container}
		{data}
		{proxyBase}
		backHref="/documents"
		createParentField="container"
	/>
{/if}
