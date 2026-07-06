<script lang="ts">
	import DocumentEditor from '$lib/components/DocumentEditor/DocumentEditor.svelte';
	import UploadedDocumentView from '$lib/components/DocumentEditor/UploadedDocumentView.svelte';
	import LinkedDocumentView from '$lib/components/DocumentEditor/LinkedDocumentView.svelte';
	let { data } = $props();

	let isUploaded = $derived(data.currentRevision?.source === 'uploaded');
	let isLinked = $derived(data.currentRevision?.source === 'link');
	const proxyBase = `/document-containers/${data.container.id}/document`;
</script>

{#if isUploaded}
	<UploadedDocumentView parent={data.container} {data} {proxyBase} backHref="/documents" />
{:else if isLinked}
	<LinkedDocumentView parent={data.container} {data} {proxyBase} backHref="/documents" />
{:else}
	<DocumentEditor
		parent={data.container}
		{data}
		{proxyBase}
		backHref="/documents"
		createParentField="container"
	/>
{/if}
