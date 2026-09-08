<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import EvidenceAttachments from '$lib/components/AttachmentPreview/EvidenceAttachments.svelte';
	import { page } from '$app/state';
	import { canPerformAction } from '$lib/utils/access-control';
	let { data }: { data: PageData } = $props();
	const canEdit = $derived(
		['evidence', 'evidencerevision'].every((model) =>
			canPerformAction({
				user: page.data.user,
				action: 'change',
				model,
				domain: data.data.folder?.id ?? data.data.folder ?? page.data.user.root_folder_id
			})
		)
	);
</script>

<DetailView {data} />
<EvidenceAttachments attachments={data.data.attachments} {canEdit} />
