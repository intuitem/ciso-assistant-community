<script lang="ts">
	import { m } from '$paraglide/messages';
	import { onMount, onDestroy } from 'svelte';
	import DiffViewer from '$lib/components/PolicyEditor/DiffViewer.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { LOCALE_MAP } from '$lib/utils/locales';

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
	let availableLocales: string[] = $state(data.availableLocales || []);
	let currentLocale = $state(data.document?.locale || data.userLocale || 'en');
	let showLocalePicker = $state(false);

	let content = $state(currentRevision?.content || '');
	let changeSummary = $state('');
	let reviewerComments = $state('');
	let saving = $state(false);
	let saved = $state(false);
	let saveTimeout: ReturnType<typeof setTimeout> | null = null;
	let showPreview = $state(false);
	let previewContent = $state('');
	let showDiff = $state(false);
	let diffResult = $state('');
	let diffRevisionA = $state('');
	let diffRevisionB = $state('');
	let showTemplateSelector = $state(!document);
	let showVersionHistory = $state(true);
	let editHistory: any[] = $state([]);
	let showEditHistory = $state(false);
	let loadingEditHistory = $state(false);
	let lockedBy: any = $state(null);
	let hasLock = $state(false);
	let lastLoadedAt = $state(currentRevision?.updated_at || '');

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

	async function createDocument(templateId: string | null, locale?: string) {
		const body: Record<string, any> = {
			_action: 'create-document',
			policy: policy.id,
			folder: policy.folder?.id || policy.folder,
			locale: locale || currentLocale
		};
		if (templateId) {
			body.template_used = templateId;
		}

		const res = await proxyPost(body);
		if (res.ok) {
			const newDoc = await res.json();
			document = newDoc;
			currentLocale = newDoc.locale || currentLocale;
			if (!availableLocales.includes(currentLocale)) {
				availableLocales = [...availableLocales, currentLocale];
			}
			showTemplateSelector = false;
			addingTranslationLocale = '';
			newTranslationLocale = '';
			await refreshData();
			await checkAndAcquireLock();
		}
	}

	async function switchLocale(locale: string) {
		if (locale === currentLocale) return;
		// Release lock on current revision
		if (currentRevision?.id && hasLock) {
			await proxyPost({ _action: 'stop-editing', revision_id: currentRevision.id });
			hasLock = false;
			stopHeartbeat();
		}
		// Fetch the document for the target locale
		const res = await fetch(
			`/policies/${policy.id}/document?_action=documents-by-locale&locale=${locale}`
		);
		if (!res.ok) return;
		const docData = await res.json();
		if (docData) {
			document = docData;
			currentLocale = locale;
			previewContent = '';
			showPreview = false;
			showDiff = false;
			await refreshData();
			// Acquire lock if editable
			if (isDraft || isChangeRequested) {
				await checkAndAcquireLock();
			}
		}
		showLocalePicker = false;
	}

	function startAddTranslation() {
		showLocalePicker = false;
		// Show template selector for the new locale
		addingTranslationLocale = newTranslationLocale;
		showTemplateSelector = true;
	}

	let addingTranslationLocale = $state('');
	let newTranslationLocale = $state('');

	async function refreshData() {
		if (!document) return;

		const revRes = await proxyGet({ _action: 'revisions', document: document.id });
		const revData = await revRes.json();
		revisions = revData.results || [];

		const editable = revisions.find(
			(r: any) => r.status === 'draft' || r.status === 'change_requested'
		);
		if (editable) {
			const fullRes = await proxyGet({ _action: 'revision', revision_id: editable.id });
			currentRevision = await fullRes.json();
			content = currentRevision.content || '';
			lastLoadedAt = currentRevision.updated_at || '';
		} else if (revisions.length > 0) {
			const fullRes = await proxyGet({ _action: 'revision', revision_id: revisions[0].id });
			currentRevision = await fullRes.json();
			content = currentRevision.content || '';
			lastLoadedAt = currentRevision.updated_at || '';
		}
	}

	let saveConflict = $state('');

	async function saveContent(): Promise<boolean> {
		if (!canEdit) return false;
		saving = true;
		saved = false;
		saveConflict = '';
		if (saveTimeout) clearTimeout(saveTimeout);
		try {
			const res = await proxyPost({
				_action: 'save-revision',
				revision_id: currentRevision.id,
				content,
				change_summary: changeSummary,
				expected_updated_at: lastLoadedAt
			});
			if (res.ok) {
				currentRevision = await res.json();
				lastLoadedAt = currentRevision.updated_at || '';
				saved = true;
				saveTimeout = setTimeout(() => (saved = false), 3000);
				return true;
			} else {
				const errData = await res.json().catch(() => null);
				if (res.status === 400 && errData) {
					const msg =
						typeof errData === 'string'
							? errData
							: errData.non_field_errors?.[0] || errData.detail || JSON.stringify(errData);
					saveConflict = msg;
				}
				return false;
			}
		} finally {
			saving = false;
		}
	}

	async function submitForReview() {
		if (!currentRevision) return;
		const saveOk = await saveContent();
		if (!saveOk) return;
		const res = await proxyPost({
			_action: 'submit-for-review',
			revision_id: currentRevision.id
		});
		if (res.ok) {
			changeSummary = '';
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
		confirmAndDelete(m.deleteRevision(), m.deleteRevisionConfirmation(), async () => {
			const qs = new URLSearchParams({ _type: 'revision', id: revisionId }).toString();
			const res = await fetch(`${proxyUrl}?${qs}`, { method: 'DELETE' });
			if (res.ok) {
				await refreshData();
			}
		});
	}

	function deleteDocument() {
		if (!document) return;
		confirmAndDelete(m.deleteDocumentTitle(), m.deleteDocumentConfirmation(), async () => {
			const qs = new URLSearchParams({ _type: 'document', id: document.id }).toString();
			const res = await fetch(`${proxyUrl}?${qs}`, { method: 'DELETE' });
			if (res.ok) {
				document = null;
				currentRevision = null;
				revisions = [];
				showTemplateSelector = true;
			}
		});
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
			editDiffResult = '';
			editDiffMeta = {};
			showDiff = true;
		}
	}

	async function loadRevision(revisionId: string) {
		// Release lock on previous revision
		if (hasLock && currentRevision?.id) {
			await proxyPost({ _action: 'stop-editing', revision_id: currentRevision.id });
		}
		hasLock = false;
		const res = await proxyGet({ _action: 'revision', revision_id: revisionId });
		if (res.ok) {
			currentRevision = await res.json();
			content = currentRevision.content || '';
			lastLoadedAt = currentRevision.updated_at || '';
			// Reset edit history when switching revisions
			editHistory = [];
			showEditHistory = false;
			// Check editing status and try to acquire lock for editable revisions
			if (currentRevision.status === 'draft' || currentRevision.status === 'change_requested') {
				await checkAndAcquireLock();
			} else {
				lockedBy = null;
			}
		}
	}

	async function checkAndAcquireLock() {
		if (!currentRevision) return;
		const wasLocked = !!lockedBy;
		const res = await proxyPost({
			_action: 'start-editing',
			revision_id: currentRevision.id
		});
		if (res.ok) {
			const data = await res.json();
			if (data.locked) {
				lockedBy = data.editing_user;
				hasLock = false;
				stopHeartbeat();
			} else {
				lockedBy = null;
				hasLock = true;
				startHeartbeat();
				// If we were previously locked out, reload to get latest content
				if (wasLocked) {
					await refreshData();
				}
			}
		}
	}

	function confirmTakeOver() {
		const editorName = lockedBy
			? `${lockedBy.first_name || ''} ${lockedBy.last_name || lockedBy.email}`.trim()
			: 'another user';
		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal,
			props: {
				bodyComponent: undefined
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.takeOverEditingTitle(),
			body: m.takeOverEditingConfirmation({ user: editorName }),
			response: (confirmed: boolean) => {
				if (confirmed) takeOverEditing();
			}
		};
		modalStore.trigger(modal);
	}

	async function takeOverEditing() {
		if (!currentRevision) return;
		const res = await proxyPost({
			_action: 'take-over-editing',
			revision_id: currentRevision.id
		});
		if (res.ok) {
			lockedBy = null;
			hasLock = true;
			startHeartbeat();
			await refreshData();
		}
	}

	// Release lock when leaving the page
	function releaseLock() {
		if (currentRevision?.id && hasLock) {
			// Use sendBeacon for beforeunload (fire-and-forget), fetch for normal nav
			proxyPost({ _action: 'stop-editing', revision_id: currentRevision.id }).catch(() => {});
		}
	}

	let heartbeatInterval: ReturnType<typeof setInterval> | null = null;

	function startHeartbeat() {
		stopHeartbeat();
		heartbeatInterval = setInterval(
			async () => {
				if (hasLock && currentRevision) {
					try {
						const res = await proxyPost({
							_action: 'start-editing',
							revision_id: currentRevision.id
						});
						if (res.ok) {
							const data = await res.json();
							if (data.locked) {
								// Someone else took over — we've been evicted
								lockedBy = data.editing_user;
								hasLock = false;
								stopHeartbeat();
							}
						} else {
							// Server rejected the heartbeat — assume lock is lost
							hasLock = false;
							stopHeartbeat();
						}
					} catch {
						// Network failure — assume lock is lost
						hasLock = false;
						stopHeartbeat();
					}
				}
			},
			3 * 60 * 1000
		); // every 3 minutes
	}

	function stopHeartbeat() {
		if (heartbeatInterval) {
			clearInterval(heartbeatInterval);
			heartbeatInterval = null;
		}
	}

	onMount(() => {
		if (isDraft || isChangeRequested) {
			checkAndAcquireLock().then(() => {
				if (!lockedBy) startHeartbeat();
			});
		}
		window.addEventListener('beforeunload', releaseLock);
	});

	onDestroy(() => {
		if (saveTimeout) clearTimeout(saveTimeout);
		stopHeartbeat();
		releaseLock();
		if (typeof window !== 'undefined') {
			window.removeEventListener('beforeunload', releaseLock);
		}
	});

	async function toggleEditHistory() {
		if (showEditHistory) {
			showEditHistory = false;
			return;
		}
		if (!currentRevision) return;
		loadingEditHistory = true;
		try {
			const res = await proxyGet({
				_action: 'edit-history',
				revision_id: currentRevision.id
			});
			if (res.ok) {
				editHistory = await res.json();
				showEditHistory = true;
			}
		} finally {
			loadingEditHistory = false;
		}
	}

	async function loadEditSnapshot(editId: string) {
		if (!currentRevision) return;
		const res = await proxyGet({
			_action: 'edit-snapshot',
			revision_id: currentRevision.id,
			edit_id: editId
		});
		if (res.ok) {
			const snapshot = await res.json();
			previewContent = snapshot.content;
			showPreview = true;
			showDiff = false;
		}
	}

	let isDraft = $derived(currentRevision?.status === 'draft');
	let isChangeRequested = $derived(currentRevision?.status === 'change_requested');
	let canEdit = $derived((isDraft || isChangeRequested) && hasLock);
	let isInReview = $derived(currentRevision?.status === 'in_review');
	let hasDraft = $derived(revisions.some((r: any) => r.status === 'draft'));

	// Image upload state
	let uploading = $state(false);
	let textareaEl: HTMLTextAreaElement | undefined = $state();
	let fileInputEl: HTMLInputElement | undefined = $state();

	async function uploadImage(file: File) {
		if (!document) return;
		uploading = true;
		try {
			const formData = new FormData();
			formData.append('file', file);
			const uploadUrl = `${proxyUrl}?_action=upload-image&document_id=${document.id}`;
			const res = await fetch(uploadUrl, { method: 'POST', body: formData });
			if (res.ok) {
				const data = await res.json();
				const imageUrl = `${proxyUrl}?_action=serve-image&attachment_id=${data.id}`;
				const markdownImg = `![image](${imageUrl})`;
				insertAtCursor(markdownImg);
			}
		} finally {
			uploading = false;
		}
	}

	function insertAtCursor(text: string) {
		if (!textareaEl) {
			content += '\n' + text;
			return;
		}
		const start = textareaEl.selectionStart;
		const end = textareaEl.selectionEnd;
		content = content.substring(0, start) + text + content.substring(end);
		const newPos = start + text.length;
		requestAnimationFrame(() => {
			textareaEl?.setSelectionRange(newPos, newPos);
			textareaEl?.focus();
		});
	}

	function wrapSelection(before: string, after: string) {
		if (!textareaEl) return;
		const start = textareaEl.selectionStart;
		const end = textareaEl.selectionEnd;
		const selected = content.substring(start, end);
		const placeholder = selected || 'text';
		const replacement = before + placeholder + after;
		content = content.substring(0, start) + replacement + content.substring(end);
		requestAnimationFrame(() => {
			if (selected) {
				// Keep the original text selected (inside the markers)
				textareaEl?.setSelectionRange(
					start + before.length,
					start + before.length + selected.length
				);
			} else {
				// Select the placeholder so the user can type over it
				textareaEl?.setSelectionRange(
					start + before.length,
					start + before.length + placeholder.length
				);
			}
			textareaEl?.focus();
		});
	}

	function insertLinePrefix(prefix: string) {
		if (!textareaEl) return;
		const start = textareaEl.selectionStart;
		// Find the beginning of the current line
		const lineStart = content.lastIndexOf('\n', start - 1) + 1;
		content = content.substring(0, lineStart) + prefix + content.substring(lineStart);
		const newPos = start + prefix.length;
		requestAnimationFrame(() => {
			textareaEl?.setSelectionRange(newPos, newPos);
			textareaEl?.focus();
		});
	}

	function handlePaste(e: ClipboardEvent) {
		if (!canEdit || !e.clipboardData) return;
		const items = e.clipboardData.items;
		for (const item of items) {
			if (item.type.startsWith('image/')) {
				e.preventDefault();
				const file = item.getAsFile();
				if (file) uploadImage(file);
				return;
			}
		}
	}

	function handleFileInput(e: Event) {
		const input = e.target as HTMLInputElement;
		if (input.files?.[0]) {
			uploadImage(input.files[0]);
			input.value = '';
		}
	}

	// Edit diff state
	let editDiffA = $state('');
	let editDiffB = $state('');
	let editDiffResult = $state('');
	let editDiffMeta: { from_edit?: any; to_edit?: any } = $state({});

	async function compareEdits() {
		if (!currentRevision || !editDiffA || !editDiffB) return;
		const res = await proxyGet({
			_action: 'edit-diff',
			revision_id: currentRevision.id,
			edit_a_id: editDiffA,
			edit_b_id: editDiffB
		});
		if (res.ok) {
			const data = await res.json();
			editDiffResult = data.diff;
			editDiffMeta = { from_edit: data.from_edit, to_edit: data.to_edit };
			showDiff = true;
			showPreview = false;
		}
	}
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
				title={m.backToPolicy()}
			>
				<i class="fa-solid fa-arrow-left"></i>
			</a>
			<div class="flex items-center gap-2">
				<h1 class="text-lg font-semibold truncate max-w-md">{policy.name}</h1>

				<!-- Locale selector -->
				{#if document || availableLocales.length > 0}
					<div class="relative">
						<button
							class="btn btn-sm preset-tonal-surface gap-1"
							onclick={() => (showLocalePicker = !showLocalePicker)}
							title={m.documentLanguage()}
						>
							{#if LOCALE_MAP[currentLocale as keyof typeof LOCALE_MAP]?.flag}
								<span>{LOCALE_MAP[currentLocale as keyof typeof LOCALE_MAP].flag}</span>
							{/if}
							<span class="uppercase text-xs font-semibold">{currentLocale}</span>
							<i class="fa-solid fa-chevron-down text-[8px] ml-0.5"></i>
						</button>

						{#if showLocalePicker}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="absolute top-full left-0 mt-1 bg-white border border-surface-200 rounded-lg shadow-lg z-50 min-w-[180px] py-1"
								onmouseleave={() => (showLocalePicker = false)}
							>
								{#each availableLocales as locale}
									<button
										class="w-full text-left px-3 py-1.5 text-sm hover:bg-surface-50 flex items-center gap-2 {locale ===
										currentLocale
											? 'bg-primary-50 text-primary-700'
											: ''}"
										onclick={() => switchLocale(locale)}
									>
										{#if LOCALE_MAP[locale as keyof typeof LOCALE_MAP]?.flag}
											<span>{LOCALE_MAP[locale as keyof typeof LOCALE_MAP].flag}</span>
										{/if}
										<span class="uppercase font-medium">{locale}</span>
										{#if locale === currentLocale}
											<i class="fa-solid fa-check text-xs ml-auto"></i>
										{/if}
									</button>
								{/each}
								<div class="border-t border-surface-200 mt-1 pt-1">
									<div class="px-3 py-1.5">
										<select class="select text-xs w-full py-1" bind:value={newTranslationLocale}>
											<option value=""
												>{m.addTranslation ? m.addTranslation() : 'Add translation...'}</option
											>
											{#each Object.entries(LOCALE_MAP) as [code, info]}
												{#if !availableLocales.includes(code)}
													<option value={code}>
														{info.flag || ''}
														{code.toUpperCase()}
													</option>
												{/if}
											{/each}
										</select>
										{#if newTranslationLocale}
											<button
												class="btn btn-sm preset-filled-primary-500 w-full mt-1"
												onclick={() => startAddTranslation()}
											>
												<i class="fa-solid fa-plus mr-1"></i>
												{m.create ? m.create() : 'Create'}
											</button>
										{/if}
									</div>
								</div>
							</div>
						{/if}
					</div>
				{/if}

				{#if currentRevision}
					{@const style = getStatusStyle(currentRevision.status)}
					<span
						class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border {style.bg} {style.text}"
					>
						<i class="fa-solid {style.icon} text-[10px]"></i>
						{currentRevision.status_display || currentRevision.status}
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

			{#if canEdit}
				<button
					class="btn btn-sm {saved
						? 'preset-filled-success-500'
						: 'preset-filled-primary-500'} disabled:opacity-50"
					onclick={() => saveContent()}
					disabled={saving}
				>
					{#if saving}
						<i class="fa-solid fa-spinner fa-spin"></i>
						<span class="ml-1">{m.saving()}</span>
					{:else if saved}
						<i class="fa-solid fa-check"></i>
						<span class="ml-1">{m.saved()}</span>
					{:else}
						<i class="fa-solid fa-floppy-disk"></i>
						<span class="ml-1">{m.save()}</span>
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
					<span class="ml-1">{m.approve()}</span>
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
					title={m.deleteDocumentAndRevisions()}
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
					<p class="text-surface-500">{m.chooseDocumentTemplate()}</p>
				</div>

				{#if addingTranslationLocale}
					<div
						class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-50 text-primary-700 text-sm font-medium mb-2"
					>
						<i class="fa-solid fa-language"></i>
						{m.addingTranslation()}
						{#if LOCALE_MAP[addingTranslationLocale as keyof typeof LOCALE_MAP]?.flag}
							<span>{LOCALE_MAP[addingTranslationLocale as keyof typeof LOCALE_MAP].flag}</span>
						{/if}
						<span class="uppercase">{addingTranslationLocale}</span>
					</div>
				{/if}

				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					<button
						class="group card p-5 border-2 border-dashed border-surface-300 hover:border-primary-400 hover:shadow-md transition-all text-left"
						onclick={() => createDocument(null, addingTranslationLocale || undefined)}
					>
						<div
							class="w-10 h-10 rounded-lg bg-surface-100 group-hover:bg-primary-100 flex items-center justify-center mb-3 transition-colors"
						>
							<i
								class="fa-solid fa-file text-surface-400 group-hover:text-primary-500 transition-colors"
							></i>
						</div>
						<h3 class="font-medium text-sm">{m.startFromScratch()}</h3>
						<p class="text-xs text-surface-400 mt-1">{m.startWithBlankDocument()}</p>
					</button>

					{#each templates as template}
						<button
							class="group card p-5 border border-surface-200 hover:border-primary-400 hover:shadow-md transition-all text-left"
							onclick={() => createDocument(template.id, addingTranslationLocale || undefined)}
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
	{#if document && currentRevision && !showTemplateSelector}
		<!-- Lock / conflict banners -->
		{#if lockedBy}
			<div
				class="mx-6 mt-4 flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3"
			>
				<i class="fa-solid fa-lock text-amber-500"></i>
				<div class="flex-1 text-sm text-amber-800">
					{m.userEditingDraft({
						user: `${lockedBy.first_name || ''} ${lockedBy.last_name || lockedBy.email}`.trim()
					})}
				</div>
				<button class="btn btn-sm preset-tonal-warning" onclick={() => checkAndAcquireLock()}>
					<i class="fa-solid fa-rotate mr-1"></i>
					{m.retry()}
				</button>
				<button class="btn btn-sm preset-tonal-error" onclick={() => confirmTakeOver()}>
					<i class="fa-solid fa-unlock mr-1"></i>
					{m.takeOverEditing()}
				</button>
			</div>
		{/if}

		{#if saveConflict}
			<div
				class="mx-6 mt-4 flex items-center gap-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3"
			>
				<i class="fa-solid fa-triangle-exclamation text-red-500"></i>
				<div class="flex-1 text-sm text-red-700">{saveConflict}</div>
				<button
					class="btn btn-sm preset-tonal-error"
					onclick={async () => {
						saveConflict = '';
						await refreshData();
					}}
				>
					<i class="fa-solid fa-rotate mr-1"></i> Reload
				</button>
			</div>
		{/if}

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
						placeholder={m.addReviewerComments()}
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
								previewContent = '';
							}}
						>
							<i class="fa-solid fa-pen mr-1.5 text-xs"></i>{m.editTab()}
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

					{#if canEdit && !showPreview && !showDiff}
						<div class="flex items-center gap-0.5 ml-2 border-l border-surface-200 pl-2">
							<button
								class="btn btn-sm preset-tonal-surface px-2"
								onclick={() => wrapSelection('**', '**')}
								title={`${m.formatBold()} (Ctrl+B)`}
							>
								<i class="fa-solid fa-bold text-xs"></i>
							</button>
							<button
								class="btn btn-sm preset-tonal-surface px-2"
								onclick={() => wrapSelection('*', '*')}
								title={`${m.formatItalic()} (Ctrl+I)`}
							>
								<i class="fa-solid fa-italic text-xs"></i>
							</button>
							<button
								class="btn btn-sm preset-tonal-surface px-2"
								onclick={() => insertLinePrefix('# ')}
								title={m.formatHeading()}
							>
								<i class="fa-solid fa-heading text-xs"></i>
							</button>
							<button
								class="btn btn-sm preset-tonal-surface px-2"
								onclick={() => insertLinePrefix('- ')}
								title={m.bulletList()}
							>
								<i class="fa-solid fa-list-ul text-xs"></i>
							</button>
							<button
								class="btn btn-sm preset-tonal-surface px-2"
								onclick={() => insertLinePrefix('1. ')}
								title={m.numberedList()}
							>
								<i class="fa-solid fa-list-ol text-xs"></i>
							</button>
							<button
								class="btn btn-sm preset-tonal-surface px-2"
								onclick={() => wrapSelection('[', '](url)')}
								title={m.insertLink()}
							>
								<i class="fa-solid fa-link text-xs"></i>
							</button>
							<button
								class="btn btn-sm preset-tonal-surface px-2"
								onclick={() =>
									insertAtCursor(
										'\n| Column 1 | Column 2 |\n|----------|----------|\n| Cell	 | Cell	 |\n'
									)}
								title={m.insertTable()}
							>
								<i class="fa-solid fa-table text-xs"></i>
							</button>
							<button
								class="btn btn-sm preset-tonal-surface px-2"
								onclick={() => fileInputEl?.click()}
								title={m.insertImage()}
								disabled={uploading}
							>
								{#if uploading}
									<i class="fa-solid fa-spinner fa-spin text-xs"></i>
								{:else}
									<i class="fa-solid fa-image text-xs"></i>
								{/if}
							</button>
							<input
								type="file"
								accept="image/*"
								class="hidden"
								bind:this={fileInputEl}
								onchange={handleFileInput}
							/>
						</div>
					{/if}

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
								placeholder={m.describeYourChanges()}
							/>
						</div>
					{/if}
				</div>

				<!-- Content area -->
				{#if showDiff}
					{#if editDiffMeta.from_edit && editDiffMeta.to_edit}
						<div
							class="flex items-stretch gap-0 mb-2 rounded-lg border border-surface-200 overflow-hidden text-xs"
						>
							<div class="flex-1 px-3 py-2 bg-red-50/60">
								<div class="flex items-center gap-1.5 text-red-700">
									<i class="fa-solid fa-minus-circle text-[10px]"></i>
									<span class="font-semibold">
										{editDiffMeta.from_edit.editor?.first_name || ''}
										{editDiffMeta.from_edit.editor?.last_name ||
											editDiffMeta.from_edit.editor?.email ||
											'Unknown'}
									</span>
								</div>
								<p class="text-surface-400 mt-0.5">
									{new Date(editDiffMeta.from_edit.created_at).toLocaleString(undefined, {
										month: 'short',
										day: 'numeric',
										hour: '2-digit',
										minute: '2-digit'
									})}
									{#if editDiffMeta.from_edit.summary}
										&middot; <span class="italic">{editDiffMeta.from_edit.summary}</span>
									{/if}
								</p>
							</div>
							<div class="flex items-center px-2 bg-surface-100 text-surface-400">
								<i class="fa-solid fa-arrow-right text-[10px]"></i>
							</div>
							<div class="flex-1 px-3 py-2 bg-emerald-50/60">
								<div class="flex items-center gap-1.5 text-emerald-700">
									<i class="fa-solid fa-plus-circle text-[10px]"></i>
									<span class="font-semibold">
										{editDiffMeta.to_edit.editor?.first_name || ''}
										{editDiffMeta.to_edit.editor?.last_name ||
											editDiffMeta.to_edit.editor?.email ||
											'Unknown'}
									</span>
								</div>
								<p class="text-surface-400 mt-0.5">
									{new Date(editDiffMeta.to_edit.created_at).toLocaleString(undefined, {
										month: 'short',
										day: 'numeric',
										hour: '2-digit',
										minute: '2-digit'
									})}
									{#if editDiffMeta.to_edit.summary}
										&middot; <span class="italic">{editDiffMeta.to_edit.summary}</span>
									{/if}
								</p>
							</div>
						</div>
					{/if}
					<DiffViewer diff={editDiffResult || diffResult} />
				{:else if showPreview}
					<div class="card border border-surface-200 p-6 overflow-auto flex-1 min-h-[500px]">
						<MarkdownRenderer content={previewContent || content} />
					</div>
				{:else}
					<textarea
						bind:value={content}
						bind:this={textareaEl}
						onpaste={handlePaste}
						class="input w-full flex-1 min-h-[500px] resize-y font-mono text-sm leading-relaxed p-4 {!canEdit
							? 'bg-surface-50 cursor-not-allowed'
							: ''}"
						disabled={!canEdit}
						placeholder={m.writeDocumentPlaceholder()}
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
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div
									class="w-full text-left px-3 py-2.5 rounded-lg transition-colors cursor-pointer {isActive
										? 'bg-primary-50 ring-1 ring-primary-200'
										: 'hover:bg-surface-50'}"
									onclick={() => loadRevision(revision.id)}
									onkeydown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') loadRevision(revision.id);
									}}
									role="button"
									tabindex="0"
								>
									<div class="flex items-center justify-between mb-1">
										<span class="text-sm font-semibold {isActive ? 'text-primary-700' : ''}">
											v{revision.version_number}
										</span>
										<span
											class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border {style.bg} {style.text}"
										>
											<i class="fa-solid {style.icon} text-[8px]"></i>
											{revision.status_display || revision.status}
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
											{new Date(revision.created_at).toLocaleString(undefined, {
												month: 'short',
												day: 'numeric',
												hour: '2-digit',
												minute: '2-digit'
											})}
										</p>
										{#if revision.status === 'draft' || revision.status === 'deprecated'}
											<button
												class="text-[10px] text-surface-400 hover:text-red-500 transition-colors p-0.5"
												onclick={(e) => {
													e.stopPropagation();
													deleteRevision(revision.id);
												}}
												title={m.deleteRevision()}
											>
												<i class="fa-solid fa-trash"></i>
											</button>
										{/if}
									</div>
								</div>
							{/each}

							{#if revisions.length === 0}
								<div class="text-center py-6 text-surface-400 text-sm">
									<i class="fa-solid fa-inbox text-xl mb-2"></i>
									<p>{m.noRevisionsYet()}</p>
								</div>
							{/if}
						</div>

						<!-- Edit history for current revision -->
						{#if currentRevision}
							<div class="border-t border-surface-200">
								<button
									class="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-surface-500 uppercase tracking-wide hover:bg-surface-50 transition-colors"
									onclick={() => toggleEditHistory()}
								>
									<span class="flex items-center gap-1.5">
										<i class="fa-solid fa-list-ul"></i>
										{m.editHistory()}
									</span>
									{#if loadingEditHistory}
										<i class="fa-solid fa-spinner fa-spin text-[10px]"></i>
									{:else}
										<i class="fa-solid fa-chevron-{showEditHistory ? 'up' : 'down'} text-[10px]"
										></i>
									{/if}
								</button>

								{#if showEditHistory}
									<div class="max-h-48 overflow-auto">
										{#if editHistory.length === 0}
											<p class="px-4 py-3 text-xs text-surface-400 italic">
												{m.noEditsRecordedYet()}
											</p>
										{:else}
											<div class="flex items-center gap-1 px-4 pt-2 pb-1">
												<span
													class="w-3 text-center text-[9px] font-bold text-red-400 flex-shrink-0"
													title={m.olderVersion()}>A</span
												>
												<span
													class="w-3 text-center text-[9px] font-bold text-emerald-500 flex-shrink-0"
													title={m.newerVersion()}>B</span
												>
												<span class="flex-1"></span>
											</div>
											{#each editHistory as edit}
												<div
													class="flex items-center gap-1 px-4 py-2 hover:bg-surface-50 border-t border-surface-100 transition-colors"
												>
													<input
														type="radio"
														name="edit-diff-a"
														value={edit.id}
														bind:group={editDiffA}
														class="w-3 h-3 flex-shrink-0 accent-red-400"
														title={m.selectAsFrom()}
														onclick={(e) => e.stopPropagation()}
													/>
													<input
														type="radio"
														name="edit-diff-b"
														value={edit.id}
														bind:group={editDiffB}
														class="w-3 h-3 flex-shrink-0 accent-emerald-500"
														title={m.selectAsTo()}
														onclick={(e) => e.stopPropagation()}
													/>
													<button
														class="flex-1 text-left"
														onclick={() => loadEditSnapshot(edit.id)}
														title={m.viewSnapshot()}
													>
														<div class="flex items-center justify-between">
															<span class="text-xs text-surface-600">
																{#if edit.editor}
																	{edit.editor.first_name || ''}
																	{edit.editor.last_name || edit.editor.email}
																{:else}
																	Unknown
																{/if}
															</span>
															<span class="text-[10px] text-surface-400">
																{new Date(edit.created_at).toLocaleString(undefined, {
																	month: 'short',
																	day: 'numeric',
																	hour: '2-digit',
																	minute: '2-digit'
																})}
															</span>
														</div>
														{#if edit.summary}
															<p class="text-[10px] text-surface-400 mt-0.5 truncate italic">
																{edit.summary}
															</p>
														{/if}
													</button>
												</div>
											{/each}
											{#if editHistory.length >= 2}
												<div class="px-4 py-2 border-t border-surface-100">
													<button
														class="btn btn-sm preset-tonal-primary w-full"
														onclick={() => compareEdits()}
														disabled={!editDiffA || !editDiffB}
													>
														<i class="fa-solid fa-code-compare mr-1"></i>
														{m.compareEdits()}
													</button>
												</div>
											{/if}
										{/if}
									</div>
								{/if}
							</div>
						{/if}

						<!-- Diff comparison -->
						{#if revisions.length >= 2}
							<div class="p-3 border-t border-surface-200 bg-surface-50 space-y-2">
								<h4 class="text-xs font-semibold text-surface-500 uppercase tracking-wide">
									{m.compareDiff()}
								</h4>
								<div class="flex gap-1.5">
									<select bind:value={diffRevisionA} class="select text-xs flex-1 py-1">
										<option value="">{m.diffFrom()}...</option>
										{#each revisions as rev}
											<option value={rev.id}>v{rev.version_number}</option>
										{/each}
									</select>
									<select bind:value={diffRevisionB} class="select text-xs flex-1 py-1">
										<option value="">{m.diffTo()}...</option>
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
