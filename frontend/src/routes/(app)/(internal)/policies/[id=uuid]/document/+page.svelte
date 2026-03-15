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

	const statusColors: Record<string, string> = {
		draft: 'bg-yellow-100 text-yellow-800',
		in_review: 'bg-blue-100 text-blue-800',
		change_requested: 'bg-red-100 text-red-800',
		published: 'bg-green-100 text-green-800',
		deprecated: 'bg-gray-100 text-gray-500'
	};

	const statusLabels: Record<string, string> = {
		draft: 'Draft',
		in_review: 'In review',
		change_requested: 'Change requested',
		published: 'Published',
		deprecated: 'Deprecated'
	};

	function getStatusBadge(revisionStatus: string) {
		return statusColors[revisionStatus] || 'bg-gray-100 text-gray-600';
	}

	// All API calls go through the +server.ts proxy
	const proxyUrl = `/policies/${policy.id}/document`;

	async function proxyPost(body: Record<string, any>) {
		const res = await fetch(proxyUrl, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		return res;
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

<div class="flex flex-col space-y-4 p-4">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center space-x-4">
			<a href="/policies/{policy.id}" class="text-gray-500 hover:text-gray-700">
				<i class="fa-solid fa-arrow-left"></i>
			</a>
			<h1 class="text-2xl font-bold">{policy.name}</h1>
			{#if currentRevision}
				<span
					class="px-3 py-1 rounded-full text-sm font-medium {getStatusBadge(
						currentRevision.status
					)}"
				>
					{statusLabels[currentRevision.status] || currentRevision.status}
				</span>
				<span class="text-sm text-gray-500">v{currentRevision.version_number}</span>
			{/if}
		</div>

		<div class="flex items-center space-x-2">
			{#if currentRevision}
				<button class="btn bg-gray-200 text-gray-700 hover:bg-gray-300" onclick={() => exportPdf()}>
					<i class="fa-solid fa-file-pdf mr-1"></i>
					{m.exportPdf()}
				</button>
			{/if}

			{#if isDraft}
				<button
					class="btn {saved
						? 'bg-green-500'
						: 'bg-blue-500'} text-white hover:bg-blue-600 disabled:opacity-60"
					onclick={() => saveContent()}
					disabled={saving}
				>
					{#if saving}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
						Saving...
					{:else if saved}
						<i class="fa-solid fa-check mr-1"></i>
						Saved
					{:else}
						<i class="fa-solid fa-save mr-1"></i>
						Save
					{/if}
				</button>
				<button
					class="btn bg-orange-500 text-white hover:bg-orange-600"
					onclick={() => submitForReview()}
				>
					<i class="fa-solid fa-paper-plane mr-1"></i>
					{m.submitForReview()}
				</button>
			{/if}

			{#if isInReview}
				<button class="btn bg-green-500 text-white hover:bg-green-600" onclick={() => approve()}>
					<i class="fa-solid fa-check mr-1"></i>
					Approve
				</button>
				<button class="btn bg-red-400 text-white hover:bg-red-500" onclick={() => requestChanges()}>
					<i class="fa-solid fa-rotate-left mr-1"></i>
					{m.requestChanges()}
				</button>
			{/if}

			{#if !hasDraft && document}
				<button
					class="btn bg-indigo-500 text-white hover:bg-indigo-600"
					onclick={() => createNewDraft()}
				>
					<i class="fa-solid fa-plus mr-1"></i>
					{m.createNewDraft()}
				</button>
			{/if}

			{#if document}
				<button
					class="btn bg-red-100 text-red-600 hover:bg-red-200"
					onclick={() => deleteDocument()}
					title="Delete document and all revisions"
				>
					<i class="fa-solid fa-trash"></i>
				</button>
			{/if}
		</div>
	</div>

	<!-- Template selector (shown when no document exists) -->
	{#if showTemplateSelector}
		<div class="bg-white shadow rounded-lg p-6 border">
			<h2 class="text-lg font-semibold mb-4">{m.documentEditor()}</h2>
			<p class="text-gray-600 mb-6">Choose how to start your policy document:</p>

			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				<button
					class="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors text-left"
					onclick={() => createDocument(null)}
				>
					<i class="fa-solid fa-file-pen text-2xl text-gray-400 mb-2"></i>
					<h3 class="font-medium">{m.startFromScratch()}</h3>
					<p class="text-sm text-gray-500">Start with a blank document</p>
				</button>

				{#each templates as template}
					<button
						class="p-4 border-2 border-gray-200 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors text-left"
						onclick={() => createDocument(template.id)}
					>
						<i class="fa-solid fa-file-lines text-2xl text-blue-400 mb-2"></i>
						<h3 class="font-medium">{template.title}</h3>
						{#if template.description}
							<p class="text-sm text-gray-500">{template.description}</p>
						{/if}
					</button>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Main editor area -->
	{#if document && currentRevision}
		<!-- Reviewer comments (if change requested) -->
		{#if currentRevision.status === 'change_requested' && currentRevision.reviewer_comments}
			<div class="bg-red-50 border border-red-200 rounded-lg p-4">
				<div class="flex items-center space-x-2 mb-2">
					<i class="fa-solid fa-comment-dots text-red-500"></i>
					<span class="font-medium text-red-700">{m.reviewerComments()}</span>
				</div>
				<p class="text-red-600">{currentRevision.reviewer_comments}</p>
			</div>
		{/if}

		<!-- Review comments input (when in review) -->
		{#if isInReview}
			<div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
				<label for="reviewer-comments" class="block text-sm font-medium text-blue-700 mb-2">
					{m.reviewerComments()} (for requesting changes)
				</label>
				<textarea
					id="reviewer-comments"
					bind:value={reviewerComments}
					class="w-full border border-blue-300 rounded p-2 text-sm"
					rows="2"
					placeholder="Add comments explaining what changes are needed..."
				></textarea>
			</div>
		{/if}

		<div class="flex gap-4 flex-1">
			<!-- Editor / Preview -->
			<div class="flex-1 flex flex-col">
				<div class="flex items-center space-x-2 mb-2">
					<button
						class="px-3 py-1 text-sm rounded {!showPreview
							? 'bg-blue-500 text-white'
							: 'bg-gray-200 text-gray-700'}"
						onclick={() => {
							showPreview = false;
							showDiff = false;
						}}
					>
						<i class="fa-solid fa-pen mr-1"></i> Edit
					</button>
					<button
						class="px-3 py-1 text-sm rounded {showPreview && !showDiff
							? 'bg-blue-500 text-white'
							: 'bg-gray-200 text-gray-700'}"
						onclick={() => {
							showPreview = true;
							showDiff = false;
						}}
					>
						<i class="fa-solid fa-eye mr-1"></i>
						{m.contentPreview()}
					</button>
					{#if isDraft}
						<div class="flex-1"></div>
						<label for="change-summary" class="text-sm text-gray-500">{m.changeSummary()}:</label>
						<input
							id="change-summary"
							type="text"
							bind:value={changeSummary}
							class="border rounded px-2 py-1 text-sm w-64"
							placeholder="Describe your changes..."
						/>
					{/if}
				</div>

				{#if showDiff}
					<DiffViewer diff={diffResult} />
				{:else if showPreview}
					<div class="border rounded-lg p-6 bg-white overflow-auto flex-1 min-h-[500px]">
						<MarkdownRenderer {content} />
					</div>
				{:else}
					<textarea
						bind:value={content}
						class="w-full border rounded-lg p-4 font-mono text-sm flex-1 min-h-[500px] resize-y {!isDraft
							? 'bg-gray-50'
							: ''}"
						disabled={!isDraft}
						placeholder="Write your policy document in Markdown..."
					></textarea>
				{/if}
			</div>

			<!-- Sidebar: Version history -->
			<div class="w-80 flex-shrink-0">
				<div class="bg-white shadow rounded-lg border">
					<div class="p-4 border-b">
						<h3 class="font-semibold">{m.versionHistory()}</h3>
					</div>
					<div class="p-2 max-h-[400px] overflow-auto">
						{#each revisions as revision}
							<button
								class="w-full text-left p-3 rounded hover:bg-gray-50 transition-colors {currentRevision?.id ===
								revision.id
									? 'bg-blue-50 border border-blue-200'
									: ''}"
								onclick={() => loadRevision(revision.id)}
							>
								<div class="flex items-center justify-between">
									<span class="font-medium">v{revision.version_number}</span>
									<span
										class="px-2 py-0.5 rounded text-xs font-medium {getStatusBadge(
											revision.status
										)}"
									>
										{statusLabels[revision.status] || revision.status_display || revision.status}
									</span>
								</div>
								{#if revision.author}
									<p class="text-xs text-gray-500 mt-1">
										{revision.author.str || revision.author.email || ''}
									</p>
								{/if}
								{#if revision.change_summary}
									<p class="text-xs text-gray-400 mt-1 truncate">
										{revision.change_summary}
									</p>
								{/if}
								<div class="flex items-center justify-between mt-1">
									<p class="text-xs text-gray-400">
										{new Date(revision.created_at).toLocaleDateString()}
									</p>
									{#if revision.status === 'draft' || revision.status === 'deprecated'}
										<button
											class="text-xs text-red-400 hover:text-red-600"
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
					</div>

					<!-- Diff comparison -->
					{#if revisions.length >= 2}
						<div class="p-4 border-t">
							<h4 class="text-sm font-medium mb-2">{m.compareDiff()}</h4>
							<div class="flex flex-col space-y-2">
								<select bind:value={diffRevisionA} class="text-sm border rounded p-1">
									<option value="">From...</option>
									{#each revisions as rev}
										<option value={rev.id}>v{rev.version_number}</option>
									{/each}
								</select>
								<select bind:value={diffRevisionB} class="text-sm border rounded p-1">
									<option value="">To...</option>
									{#each revisions as rev}
										<option value={rev.id}>v{rev.version_number}</option>
									{/each}
								</select>
								<button
									class="btn text-sm bg-gray-200 hover:bg-gray-300"
									onclick={() => loadDiff()}
									disabled={!diffRevisionA || !diffRevisionB}
								>
									<i class="fa-solid fa-code-compare mr-1"></i>
									{m.compareDiff()}
								</button>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
