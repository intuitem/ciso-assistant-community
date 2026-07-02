<script lang="ts">
	import { m } from '$paraglide/messages';
	import { invalidateAll, goto } from '$app/navigation';

	interface Props {
		parent: { id: string; name: string };
		data: any;
		proxyBase: string;
		backHref: string;
	}

	let { parent, data, proxyBase, backHref }: Props = $props();

	let document = $derived(data.document);
	let currentRevision = $derived(data.currentRevision);
	let revisions = $derived((data.revisions ?? []) as any[]);
	let busy = $state(false);
	let fileInput: HTMLInputElement;

	const statusStyles: Record<string, string> = {
		draft: 'preset-tonal-warning',
		in_review: 'preset-tonal-primary',
		change_requested: 'preset-tonal-error',
		validated: 'preset-tonal-tertiary',
		published: 'preset-tonal-success',
		deprecated: 'preset-tonal-surface'
	};

	let status = $derived(currentRevision?.status as string | undefined);
	let isDraft = $derived(status === 'draft' || status === 'change_requested');
	let isInReview = $derived(status === 'in_review');
	let isValidated = $derived(status === 'validated');
	let isPublished = $derived(status === 'published');

	function fileUrl(rev: any): string {
		return rev?.id ? `${proxyBase}/file?rev=${rev.id}` : '';
	}
	let currentFileUrl = $derived(fileUrl(currentRevision));
	let isPdf = $derived((currentRevision?.file ?? '').toLowerCase().endsWith('.pdf'));

	async function proxyPost(body: Record<string, any>) {
		busy = true;
		try {
			const res = await fetch(proxyBase, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			if (res.ok) await invalidateAll();
			return res;
		} finally {
			busy = false;
		}
	}

	async function onFilePicked(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		busy = true;
		try {
			const fd = new FormData();
			fd.append('file', file);
			await fetch(`${proxyBase}?_action=upload-revision&document_id=${document.id}`, {
				method: 'POST',
				body: fd
			});
			await invalidateAll();
		} finally {
			busy = false;
			if (fileInput) fileInput.value = '';
		}
	}

	const submitForReview = () =>
		proxyPost({ _action: 'submit-for-review', revision_id: currentRevision.id });
	const approve = () => proxyPost({ _action: 'approve', revision_id: currentRevision.id });
	const publish = () => proxyPost({ _action: 'publish', revision_id: currentRevision.id });
	function requestChanges() {
		const comments = window.prompt(m.requestChanges());
		if (comments === null) return;
		proxyPost({
			_action: 'request-changes',
			revision_id: currentRevision.id,
			reviewer_comments: comments
		});
	}

	async function deleteDocument() {
		if (!window.confirm(m.deleteConfirm())) return;
		busy = true;
		try {
			await fetch(`${proxyBase}?_type=document&id=${document.id}`, { method: 'DELETE' });
			await goto(backHref);
		} finally {
			busy = false;
		}
	}
</script>

<div class="mx-auto max-w-4xl space-y-6 p-4">
	<header class="space-y-3 border-b border-surface-200-800 pb-4">
		<a href={backHref} class="text-sm text-primary-500 hover:underline">
			<i class="fa-solid fa-arrow-left mr-1"></i>{m.documents()}
		</a>
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h1 class="text-2xl font-bold">{parent?.name || m.untitled()}</h1>
			{#if currentRevision}
				<span class="badge {statusStyles[status ?? 'draft']} text-xs">
					{status} · v{currentRevision.version_number}
				</span>
			{/if}
		</div>
	</header>

	<!-- File -->
	{#if currentFileUrl}
		<div class="space-y-3">
			<a href={currentFileUrl} target="_blank" rel="noopener" class="btn variant-filled-primary">
				<i class="fa-solid fa-download mr-2"></i>{m.download()}
			</a>
			{#if isPdf}
				<iframe
					src={currentFileUrl}
					title={parent?.name}
					class="h-[70vh] w-full rounded border border-surface-200-800"
				></iframe>
			{/if}
		</div>
	{:else}
		<p class="text-surface-500">{m.noFileUploaded()}</p>
	{/if}

	<!-- Lifecycle actions -->
	<div class="flex flex-wrap items-center gap-2 border-t border-surface-200-800 pt-4">
		<input type="file" class="hidden" bind:this={fileInput} onchange={onFilePicked} />
		{#if isDraft}
			<button class="btn btn-sm variant-soft" disabled={busy} onclick={() => fileInput?.click()}>
				<i class="fa-solid fa-file-arrow-up mr-2"></i>{m.replaceFile()}
			</button>
			<button class="btn btn-sm variant-filled-primary" disabled={busy} onclick={submitForReview}>
				{m.submitForReview()}
			</button>
		{:else if isInReview}
			<button class="btn btn-sm variant-filled-success" disabled={busy} onclick={approve}>
				{m.approve()}
			</button>
			<button class="btn btn-sm variant-soft-error" disabled={busy} onclick={requestChanges}>
				{m.requestChanges()}
			</button>
		{:else if isValidated}
			<button class="btn btn-sm variant-filled-success" disabled={busy} onclick={publish}>
				{m.publish()}
			</button>
		{:else if isPublished}
			<button
				class="btn btn-sm variant-filled-primary"
				disabled={busy}
				onclick={() => fileInput?.click()}
			>
				<i class="fa-solid fa-file-arrow-up mr-2"></i>{m.uploadNewVersion()}
			</button>
		{/if}
		<button class="btn btn-sm variant-soft-error ml-auto" disabled={busy} onclick={deleteDocument}>
			<i class="fa-solid fa-trash mr-2"></i>{m.delete()}
		</button>
	</div>

	<!-- Version history -->
	{#if revisions.length}
		<section class="space-y-2">
			<h2 class="text-sm font-semibold text-surface-700-300">{m.versionHistory()}</h2>
			<ul class="divide-y divide-surface-200-800 rounded border border-surface-200-800">
				{#each revisions as rev (rev.id)}
					<li class="flex items-center justify-between gap-2 px-3 py-2 text-sm">
						<span>v{rev.version_number} · {rev.status_display ?? rev.status}</span>
						{#if rev.file || rev.source === 'uploaded'}
							<a
								href={fileUrl(rev)}
								target="_blank"
								rel="noopener"
								class="text-primary-500 hover:underline"
							>
								<i class="fa-solid fa-download mr-1"></i>{m.download()}
							</a>
						{/if}
					</li>
				{/each}
			</ul>
		</section>
	{/if}
</div>
