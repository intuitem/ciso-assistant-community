<script lang="ts">
	import { m } from '$paraglide/messages';
	import { invalidateAll } from '$app/navigation';
	import DiffViewer from '$lib/components/PolicyEditor/DiffViewer.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	interface Props {
		data: any;
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	let policy = $derived(data.policy);
	let document = $state(data.document);
	let revisions: any[] = $state(data.revisions);
	let currentRevision: any = $state(data.currentRevision);
	let templates = $derived(data.templates);

	let content = $state(currentRevision?.content || '');
	let changeSummary = $state('');
	let reviewerComments = $state('');
	let saving = $state(false);
	let saved = $state(false);
	let saveTimeout: ReturnType<typeof setTimeout> | null = null;
	let showPreview = $state(false);
	let showDiff = $state(false);
	let diffResult = $state('');
	let diffRevisionA = $state('');
	let diffRevisionB = $state('');
	let showTemplateSelector = $state(!document);
	let showVersionHistory = $state(true);

	const statusStyles: Record<string, { bg: string; text: string; icon: string }> = {
		draft: { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-700', icon: 'fa-pen' },
		in_review: {
			bg: 'bg-blue-50 border-blue-200',
			text: 'text-blue-700',
			icon: 'fa-magnifying-glass'
		},
		change_requested: {
			bg: 'bg-red-50 border-red-200',
			text: 'text-red-700',
			icon: 'fa-rotate-left'
		},
		published: {
			bg: 'bg-emerald-50 border-emerald-200',
			text: 'text-emerald-700',
			icon: 'fa-circle-check'
		},
		deprecated: { bg: 'bg-gray-50 border-gray-200', text: 'text-gray-500', icon: 'fa-archive' }
	};

	const statusLabels: Record<string, string> = {
		draft: 'Draft',
		in_review: 'In review',
		change_requested: 'Change requested',
		published: 'Published',
		deprecated: 'Deprecated'
	};

	function getStatusStyle(s: string) {
		return statusStyles[s] || statusStyles.deprecated;
	}

	// All API calls go through the +server.ts proxy
	const proxyUrl = `/policies/${policy.id}/document`;

	async function proxyPost(body: Record<string, any>) {
		return fetch(proxyUrl, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
	}

	async function proxyGet(params: Record<string, string>) {
		const qs = new URLSearchParams(params).toString();
		return fetch(`${proxyUrl}?${qs}`);
	}

	async function createDocument(templateId: string | null) {
		const body: Record<string, any> = {
			_action: 'create-document',
			policy: policy.id,
			folder: policy.folder?.id || policy.folder
		};
		if (templateId) {
			body.template_used = templateId;
		}

		const res = await proxyPost(body);
		if (res.ok) {
			const newDoc = await res.json();
			document = newDoc;
			showTemplateSelector = false;
			await refreshData();
		}
	}

	async function refreshData() {
		if (!document) return;

		const revRes = await proxyGet({ _action: 'revisions', document: document.id });
		const revData = await revRes.json();
		revisions = revData.results || [];

		const draft = revisions.find((r: any) => r.status === 'draft' || r.status === 'Draft');
		if (draft) {
			const fullRes = await proxyGet({ _action: 'revision', revision_id: draft.id });
			currentRevision = await fullRes.json();
			content = currentRevision.content || '';
		} else if (revisions.length > 0) {
			const fullRes = await proxyGet({ _action: 'revision', revision_id: revisions[0].id });
			currentRevision = await fullRes.json();
			content = currentRevision.content || '';
		}
	}

	async function saveContent() {
		if (!currentRevision || currentRevision.status !== 'draft') return;
		saving = true;
		saved = false;
		if (saveTimeout) clearTimeout(saveTimeout);
		try {
			const res = await proxyPost({
				_action: 'save-revision',
				revision_id: currentRevision.id,
				content,
				change_summary: changeSummary
			});
			if (res.ok) {
				currentRevision = await res.json();
				saved = true;
				saveTimeout = setTimeout(() => (saved = false), 3000);
			}
		} finally {
			saving = false;
		}
	}

	async function submitForReview() {
		if (!currentRevision) return;
		await saveContent();
		const res = await proxyPost({
			_action: 'submit-for-review',
			revision_id: currentRevision.id
		});
		if (res.ok) {
			await refreshData();
		}
	}

	async function approve() {
		if (!currentRevision) return;
		const res = await proxyPost({
			_action: 'approve',
			revision_id: currentRevision.id
		});
		if (res.ok) {
			await refreshData();
		}
	}

	async function requestChanges() {
		if (!currentRevision) return;
		const res = await proxyPost({
			_action: 'request-changes',
			revision_id: currentRevision.id,
			reviewer_comments: reviewerComments
		});
		if (res.ok) {
			reviewerComments = '';
			await refreshData();
		}
	}

	async function createNewDraft() {
		if (!document) return;
		const res = await proxyPost({
			_action: 'create-new-draft',
			document_id: document.id
		});
		if (res.ok) {
			await refreshData();
		}
	}

	function confirmAndDelete(title: string, body: string, onConfirm: () => void) {
		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal,
			props: {
				bodyComponent: undefined
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title,
			body,
			response: (confirmed: boolean) => {
				if (confirmed) onConfirm();
			}
		};
		modalStore.trigger(modal);
	}

	function deleteRevision(revisionId: string) {
		confirmAndDelete(
			m.deleteConfirmation ? m.deleteConfirmation() : 'Delete revision',
			'This will permanently delete this revision.',
			async () => {
				const qs = new URLSearchParams({ _type: 'revision', id: revisionId }).toString();
				const res = await fetch(`${proxyUrl}?${qs}`, { method: 'DELETE' });
				if (res.ok) {
					await refreshData();
				}
			}
		);
	}

	function deleteDocument() {
		if (!document) return;
		confirmAndDelete(
			m.deleteConfirmation ? m.deleteConfirmation() : 'Delete document',
			'This will permanently delete this document and all its revisions.',
			async () => {
				const qs = new URLSearchParams({ _type: 'document', id: document.id }).toString();
				const res = await fetch(`${proxyUrl}?${qs}`, { method: 'DELETE' });
				if (res.ok) {
					document = null;
					currentRevision = null;
					revisions = [];
					showTemplateSelector = true;
				}
			}
		);
	}

	async function exportPdf() {
		if (!currentRevision) return;
		const res = await proxyGet({
			_action: 'export-pdf',
			revision_id: currentRevision.id
		});
		if (res.ok) {
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = window.document.createElement('a');
			a.href = url;
			a.download = `${policy.name}_v${currentRevision.version_number}.pdf`;
			a.click();
			URL.revokeObjectURL(url);
		}
	}

	async function loadDiff() {
		if (!diffRevisionA || !diffRevisionB) return;
		const res = await proxyGet({
			_action: 'diff',
			revision_id: diffRevisionB,
			other_id: diffRevisionA
		});
		if (res.ok) {
			const jsonData = await res.json();
			diffResult = jsonData.diff;
			showDiff = true;
		}
	}

	async function loadRevision(revisionId: string) {
		const res = await proxyGet({ _action: 'revision', revision_id: revisionId });
		if (res.ok) {
			currentRevision = await res.json();
			content = currentRevision.content || '';
		}
	}

	let isDraft = $derived(currentRevision?.status === 'draft');
	let isInReview = $derived(currentRevision?.status === 'in_review');
	let hasDraft = $derived(revisions.some((r: any) => r.status === 'draft'));
</script>

<div class="flex flex-col h-full -m-8 bg-white min-h-screen">
	<!-- Sticky header bar -->
	<div
		class="flex items-center justify-between px-6 py-3 border-b border-surface-300 bg-surface-50"
	>
		<div class="flex items-center gap-3">
			<a
				href="/policies/{policy.id}"
				class="btn btn-sm preset-tonal-surface"
				title="Back to policy"
			>
				<i class="fa-solid fa-arrow-left"></i>
			</a>
			<div class="flex items-center gap-2">
				<h1 class="text-lg font-semibold truncate max-w-md">{policy.name}</h1>
				{#if currentRevision}
					{@const style = getStatusStyle(currentRevision.status)}
					<span
						class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border {style.bg} {style.text}"
					>
						<i class="fa-solid {style.icon} text-[10px]"></i>
						{statusLabels[currentRevision.status] || currentRevision.status}
					</span>
					<span class="text-xs text-surface-500 font-mono">
						v{currentRevision.version_number}
					</span>
				{/if}
			</div>
		</div>

		<div class="flex items-center gap-2">
			{#if currentRevision}
				<button
					class="btn btn-sm preset-tonal-surface"
					onclick={() => exportPdf()}
					title={m.exportPdf()}
				>
					<i class="fa-solid fa-file-pdf"></i>
					<span class="hidden lg:inline ml-1">{m.exportPdf()}</span>
				</button>
			{/if}

			{#if isDraft}
				<button
					class="btn btn-sm {saved
						? 'preset-filled-success-500'
						: 'preset-filled-primary-500'} disabled:opacity-50"
					onclick={() => saveContent()}
					disabled={saving}
				>
					{#if saving}
						<i class="fa-solid fa-spinner fa-spin"></i>
						<span class="ml-1">Saving...</span>
					{:else if saved}
						<i class="fa-solid fa-check"></i>
						<span class="ml-1">Saved</span>
					{:else}
						<i class="fa-solid fa-floppy-disk"></i>
						<span class="ml-1">Save</span>
					{/if}
				</button>
				<button class="btn btn-sm preset-filled-warning-500" onclick={() => submitForReview()}>
					<i class="fa-solid fa-paper-plane"></i>
					<span class="ml-1 hidden lg:inline">{m.submitForReview()}</span>
				</button>
			{/if}

			{#if isInReview}
				<button class="btn btn-sm preset-filled-success-500" onclick={() => approve()}>
					<i class="fa-solid fa-check"></i>
					<span class="ml-1">Approve</span>
				</button>
				<button class="btn btn-sm preset-filled-error-500" onclick={() => requestChanges()}>
					<i class="fa-solid fa-rotate-left"></i>
					<span class="ml-1 hidden lg:inline">{m.requestChanges()}</span>
				</button>
			{/if}

			{#if !hasDraft && document}
				<button class="btn btn-sm preset-filled-primary-500" onclick={() => createNewDraft()}>
					<i class="fa-solid fa-plus"></i>
					<span class="ml-1 hidden lg:inline">{m.createNewDraft()}</span>
				</button>
			{/if}

			{#if document}
				<button
					class="btn btn-sm preset-tonal-error"
					onclick={() => deleteDocument()}
					title="Delete document and all revisions"
				>
					<i class="fa-solid fa-trash"></i>
				</button>
			{/if}

			<!-- Toggle version history sidebar -->
			{#if document}
				<button
					class="btn btn-sm preset-tonal-surface"
					onclick={() => (showVersionHistory = !showVersionHistory)}
					title={m.versionHistory()}
				>
					<i class="fa-solid fa-clock-rotate-left"></i>
				</button>
			{/if}
		</div>
	</div>

	<!-- Template selector (shown when no document exists) -->
	{#if showTemplateSelector}
		<div class="flex-1 flex items-center justify-center p-8">
			<div class="max-w-3xl w-full">
				<div class="text-center mb-8">
					<div
						class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-surface-100 mb-4"
					>
						<i class="fa-solid fa-file-pen text-2xl text-surface-500"></i>
					</div>
					<h2 class="text-xl font-semibold mb-2">{m.documentEditor()}</h2>
					<p class="text-surface-500">Choose how to start your policy document</p>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					<button
						class="group card p-5 border-2 border-dashed border-surface-300 hover:border-primary-400 hover:shadow-md transition-all text-left"
						onclick={() => createDocument(null)}
					>
						<div
							class="w-10 h-10 rounded-lg bg-surface-100 group-hover:bg-primary-100 flex items-center justify-center mb-3 transition-colors"
						>
							<i
								class="fa-solid fa-file text-surface-400 group-hover:text-primary-500 transition-colors"
							></i>
						</div>
						<h3 class="font-medium text-sm">{m.startFromScratch()}</h3>
						<p class="text-xs text-surface-400 mt-1">Start with a blank document</p>
					</button>

					{#each templates as template}
						<button
							class="group card p-5 border border-surface-200 hover:border-primary-400 hover:shadow-md transition-all text-left"
							onclick={() => createDocument(template.id)}
						>
							<div
								class="w-10 h-10 rounded-lg bg-primary-50 group-hover:bg-primary-100 flex items-center justify-center mb-3 transition-colors"
							>
								<i class="fa-solid fa-file-lines text-primary-500"></i>
							</div>
							<h3 class="font-medium text-sm">{template.title}</h3>
							{#if template.description}
								<p class="text-xs text-surface-400 mt-1">{template.description}</p>
							{/if}
						</button>
					{/each}
				</div>
			</div>
		</div>
	{/if}

	<!-- Main editor area -->
	{#if document && currentRevision}
		<!-- Status banners -->
		{#if currentRevision.status === 'change_requested' && currentRevision.reviewer_comments}
			<div
				class="mx-6 mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3"
			>
				<i class="fa-solid fa-comment-dots text-red-400 mt-0.5"></i>
				<div class="flex-1 min-w-0">
					<p class="text-sm font-medium text-red-700 mb-1">{m.reviewerComments()}</p>
					<p class="text-sm text-red-600 whitespace-pre-line">
						{currentRevision.reviewer_comments}
					</p>
				</div>
			</div>
		{/if}

		{#if isInReview}
			<div
				class="mx-6 mt-4 flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3"
			>
				<i class="fa-solid fa-pen-to-square text-blue-400 mt-0.5"></i>
				<div class="flex-1 min-w-0">
					<label for="reviewer-comments" class="text-sm font-medium text-blue-700 block mb-1">
						{m.reviewerComments()}
					</label>
					<textarea
						id="reviewer-comments"
						bind:value={reviewerComments}
						class="input w-full text-sm"
						rows="2"
						placeholder="Add comments explaining what changes are needed..."
					></textarea>
				</div>
			</div>
		{/if}

		<div class="flex flex-1 overflow-hidden p-6 gap-4">
			<!-- Editor / Preview column -->
			<div class="flex-1 flex flex-col min-w-0">
				<!-- Tab bar + change summary -->
				<div class="flex items-center gap-1 mb-3">
					<div class="flex rounded-lg border border-surface-300 overflow-hidden">
						<button
							class="px-3 py-1.5 text-sm font-medium transition-colors {!showPreview && !showDiff
								? 'bg-primary-500 text-white'
								: 'bg-surface-50 text-surface-600 hover:bg-surface-100'}"
							onclick={() => {
								showPreview = false;
								showDiff = false;
							}}
						>
							<i class="fa-solid fa-pen mr-1.5 text-xs"></i>Edit
						</button>
						<button
							class="px-3 py-1.5 text-sm font-medium border-l border-surface-300 transition-colors {showPreview &&
							!showDiff
								? 'bg-primary-500 text-white'
								: 'bg-surface-50 text-surface-600 hover:bg-surface-100'}"
							onclick={() => {
								showPreview = true;
								showDiff = false;
							}}
						>
							<i class="fa-solid fa-eye mr-1.5 text-xs"></i>{m.contentPreview()}
						</button>
					</div>

					{#if isDraft}
						<div class="flex-1"></div>
						<div class="flex items-center gap-2">
							<label for="change-summary" class="text-xs text-surface-500 whitespace-nowrap">
								{m.changeSummary()}
							</label>
							<input
								id="change-summary"
								type="text"
								bind:value={changeSummary}
								class="input text-sm w-56"
								placeholder="Describe your changes..."
							/>
						</div>
					{/if}
				</div>

				<!-- Content area -->
				{#if showDiff}
					<DiffViewer diff={diffResult} />
				{:else if showPreview}
					<div class="card border border-surface-200 p-6 overflow-auto flex-1 min-h-[500px]">
						<MarkdownRenderer {content} />
					</div>
				{:else}
					<textarea
						bind:value={content}
						class="input w-full flex-1 min-h-[500px] resize-y font-mono text-sm leading-relaxed p-4 {!isDraft
							? 'bg-surface-50 cursor-not-allowed'
							: ''}"
						disabled={!isDraft}
						placeholder="Write your policy document in Markdown..."
						spellcheck="true"
					></textarea>
				{/if}
			</div>

			<!-- Version history sidebar -->
			{#if showVersionHistory}
				<div class="w-72 flex-shrink-0 flex flex-col">
					<div class="card border border-surface-200 flex flex-col overflow-hidden flex-1">
						<div class="px-4 py-3 border-b border-surface-200 bg-surface-50">
							<h3 class="text-sm font-semibold flex items-center gap-2">
								<i class="fa-solid fa-clock-rotate-left text-surface-400"></i>
								{m.versionHistory()}
							</h3>
						</div>

						<div class="flex-1 overflow-auto p-1.5 space-y-1">
							{#each revisions as revision}
								{@const isActive = currentRevision?.id === revision.id}
								{@const style = getStatusStyle(revision.status)}
								<button
									class="w-full text-left px-3 py-2.5 rounded-lg transition-colors {isActive
										? 'bg-primary-50 ring-1 ring-primary-200'
										: 'hover:bg-surface-50'}"
									onclick={() => loadRevision(revision.id)}
								>
									<div class="flex items-center justify-between mb-1">
										<span class="text-sm font-semibold {isActive ? 'text-primary-700' : ''}">
											v{revision.version_number}
										</span>
										<span
											class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border {style.bg} {style.text}"
										>
											<i class="fa-solid {style.icon} text-[8px]"></i>
											{statusLabels[revision.status] || revision.status_display || revision.status}
										</span>
									</div>
									{#if revision.author}
										<p class="text-xs text-surface-500 truncate">
											{revision.author.str || revision.author.email || ''}
										</p>
									{/if}
									{#if revision.change_summary}
										<p class="text-xs text-surface-400 mt-0.5 truncate italic">
											{revision.change_summary}
										</p>
									{/if}
									<div class="flex items-center justify-between mt-1.5">
										<p class="text-[10px] text-surface-400">
											{new Date(revision.created_at).toLocaleDateString()}
										</p>
										{#if revision.status === 'draft' || revision.status === 'deprecated'}
											<button
												class="text-[10px] text-surface-400 hover:text-red-500 transition-colors p-0.5"
												onclick={(e) => {
													e.stopPropagation();
													deleteRevision(revision.id);
												}}
												title="Delete revision"
											>
												<i class="fa-solid fa-trash"></i>
											</button>
										{/if}
									</div>
								</button>
							{/each}

							{#if revisions.length === 0}
								<div class="text-center py-6 text-surface-400 text-sm">
									<i class="fa-solid fa-inbox text-xl mb-2"></i>
									<p>No revisions yet</p>
								</div>
							{/if}
						</div>

						<!-- Diff comparison -->
						{#if revisions.length >= 2}
							<div class="p-3 border-t border-surface-200 bg-surface-50 space-y-2">
								<h4 class="text-xs font-semibold text-surface-500 uppercase tracking-wide">
									{m.compareDiff()}
								</h4>
								<div class="flex gap-1.5">
									<select bind:value={diffRevisionA} class="select text-xs flex-1 py-1">
										<option value="">From...</option>
										{#each revisions as rev}
											<option value={rev.id}>v{rev.version_number}</option>
										{/each}
									</select>
									<select bind:value={diffRevisionB} class="select text-xs flex-1 py-1">
										<option value="">To...</option>
										{#each revisions as rev}
											<option value={rev.id}>v{rev.version_number}</option>
										{/each}
									</select>
								</div>
								<button
									class="btn btn-sm preset-tonal-primary w-full"
									onclick={() => loadDiff()}
									disabled={!diffRevisionA || !diffRevisionB}
								>
									<i class="fa-solid fa-code-compare mr-1"></i>
									{m.compareDiff()}
								</button>
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>
