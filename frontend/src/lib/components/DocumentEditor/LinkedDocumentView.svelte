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
	let currentUrl = $derived(currentRevision?.url as string | undefined);

	async function proxyPost(body: Record<string, any>) {
		busy = true;
		try {
			const res = await fetch(proxyBase, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			if (res.ok) await invalidateAll();
			else {
				const err = await res.json().catch(() => null);
				window.alert(err?.url || err?.detail || err?.error || m.error());
			}
			return res;
		} finally {
			busy = false;
		}
	}

	function updateLink() {
		const url = window.prompt(m.updateLink(), currentUrl || 'https://');
		if (!url) return;
		proxyPost({ _action: 'link-revision', document_id: document.id, url: url.trim() });
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
			const res = await fetch(`${proxyBase}?_type=document&id=${document.id}`, {
				method: 'DELETE'
			});
			if (res.ok) await goto(backHref);
			else window.alert(m.deleteFailed());
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

	<!-- External link -->
	{#if currentUrl}
		<div class="space-y-2">
			<a
				href={currentUrl}
				target="_blank"
				rel="noopener noreferrer"
				class="btn variant-filled-primary"
			>
				<i class="fa-solid fa-arrow-up-right-from-square mr-2"></i>{m.openLink()}
			</a>
			<p class="break-all text-sm text-surface-500">
				<i class="fa-solid fa-link mr-1"></i>{currentUrl}
			</p>
		</div>
	{:else}
		<p class="text-surface-500">{m.noLinkSet()}</p>
	{/if}

	<!-- Lifecycle actions -->
	<div class="flex flex-wrap items-center gap-2 border-t border-surface-200-800 pt-4">
		{#if isDraft}
			<button class="btn btn-sm variant-soft" disabled={busy} onclick={updateLink}>
				<i class="fa-solid fa-pen mr-2"></i>{m.updateLink()}
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
			<button class="btn btn-sm variant-filled-primary" disabled={busy} onclick={updateLink}>
				<i class="fa-solid fa-pen mr-2"></i>{m.updateLink()}
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
						{#if rev.url}
							<a
								href={rev.url}
								target="_blank"
								rel="noopener noreferrer"
								class="max-w-[55%] truncate text-primary-500 hover:underline"
							>
								<i class="fa-solid fa-arrow-up-right-from-square mr-1"></i>{rev.url}
							</a>
						{/if}
					</li>
				{/each}
			</ul>
		</section>
	{/if}
</div>
