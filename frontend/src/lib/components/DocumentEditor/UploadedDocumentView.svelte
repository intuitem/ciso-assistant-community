<script lang="ts">
	import { m } from '$paraglide/messages';
	import { invalidateAll, goto } from '$app/navigation';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import { getToastStore } from '$lib/components/Toast/stores';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';

	interface Props {
		parent: { id: string; name: string };
		data: any;
		proxyBase: string;
		backHref: string;
	}

	let { parent, data, proxyBase, backHref }: Props = $props();

	const toastStore = getToastStore();
	const modalStore: ModalStore = getModalStore();

	let document = $derived(data.document);
	let currentRevision = $derived(data.currentRevision);
	let revisions = $derived((data.revisions ?? []) as any[]);
	let busy = $state(false);
	let fileInput: HTMLInputElement;
	let reviewerComments = $state('');

	function notifyError(msg: string) {
		toastStore.trigger({ message: msg, preset: 'error' });
	}

	let availableLocales = $derived((data.availableLocales ?? []) as string[]);
	let currentLocale = $derived((document?.locale ?? 'en') as string);
	let missingLocales = $derived(
		Object.keys(LOCALE_MAP).filter((l) => !availableLocales.includes(l))
	);
	const localeName = (loc: string) =>
		LOCALE_MAP[loc as keyof typeof LOCALE_MAP]?.name ?? loc.toUpperCase();

	let addingLang = $state(false);
	let newLocale = $state('');
	let newLangFile = $state<File | null>(null);

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
			else {
				const data = await res.json().catch(() => null);
				notifyError(data?.detail || data?.error || m.error());
			}
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
			const res = await fetch(`${proxyBase}?_action=upload-revision&document_id=${document.id}`, {
				method: 'POST',
				body: fd
			});
			if (res.ok) await invalidateAll();
			else notifyError(m.uploadFailed());
		} finally {
			busy = false;
			if (fileInput) fileInput.value = '';
		}
	}

	function switchLocale(loc: string) {
		if (loc === currentLocale) return;
		goto(`${proxyBase}?locale=${loc}`, { invalidateAll: true });
	}

	function startAddLang() {
		newLocale = missingLocales[0] ?? '';
		newLangFile = null;
		addingLang = true;
	}
	async function addLanguage() {
		if (!newLocale || !newLangFile) return;
		busy = true;
		try {
			// Single atomic call: the backend creates the locale document and its
			// uploaded revision in one transaction, so a rejected upload can't
			// strand an empty authored document.
			const fd = new FormData();
			fd.append('file', newLangFile);
			fd.append('locale', newLocale);
			fd.append('source', 'uploaded');
			const res = await fetch(`${proxyBase}?_action=add-locale`, {
				method: 'POST',
				body: fd
			});
			if (!res.ok) {
				const e = await res.json().catch(() => null);
				notifyError(e?.file || e?.locale || e?.detail || e?.error || m.uploadFailed());
				return;
			}
			addingLang = false;
			await goto(`${proxyBase}?locale=${newLocale}`, { invalidateAll: true });
		} finally {
			busy = false;
		}
	}

	const submitForReview = () =>
		proxyPost({ _action: 'submit-for-review', revision_id: currentRevision.id });
	const approve = () => proxyPost({ _action: 'approve', revision_id: currentRevision.id });
	const publish = () => proxyPost({ _action: 'publish', revision_id: currentRevision.id });
	async function requestChanges() {
		const res = await proxyPost({
			_action: 'request-changes',
			revision_id: currentRevision.id,
			reviewer_comments: reviewerComments
		});
		if (res?.ok) reviewerComments = '';
	}

	function deleteDocument() {
		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal,
			props: { bodyComponent: undefined }
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.deleteDocumentTitle(),
			body: m.deleteDocumentConfirmation(),
			response: (confirmed: boolean) => {
				if (confirmed) performDelete();
			}
		};
		modalStore.trigger(modal);
	}
	async function performDelete() {
		busy = true;
		try {
			const res = await fetch(`${proxyBase}?_type=document&id=${document.id}`, {
				method: 'DELETE'
			});
			if (res.ok) await goto(backHref);
			else notifyError(m.deleteFailed());
		} finally {
			busy = false;
		}
	}
</script>

<div class="mx-auto max-w-4xl space-y-6 p-4 sm:p-6">
	<a
		href={backHref}
		class="inline-flex items-center gap-1.5 text-sm text-surface-500 transition-colors hover:text-primary-500"
	>
		<i class="fa-solid fa-arrow-left"></i>{m.documents()}
	</a>

	<!-- Header: spined card -->
	<header
		class="relative overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 pl-7"
	>
		<span class="absolute inset-y-0 left-0 w-1.5 bg-primary-500"></span>
		<div class="flex items-center gap-4">
			<div
				class="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-primary-500/10 text-xl text-primary-500 ring-1 ring-primary-500/20"
			>
				<i class="fa-solid fa-file-lines"></i>
			</div>
			<div class="min-w-0">
				<h1 class="text-2xl font-bold leading-tight tracking-tight">
					{parent?.name || m.untitled()}
				</h1>
				{#if currentRevision}
					<span class="badge {statusStyles[status ?? 'draft']} mt-1 text-xs">
						{status} · v{currentRevision.version_number}
					</span>
				{/if}
			</div>
		</div>
	</header>

	<!-- Locale switcher -->
	{#if document}
		<div class="flex flex-wrap items-center gap-1.5">
			<span class="mr-1 text-[10px] font-semibold uppercase tracking-wider text-surface-400">
				{m.language()}
			</span>
			{#each availableLocales as loc (loc)}
				<button
					type="button"
					onclick={() => switchLocale(loc)}
					class="rounded-md border px-2.5 py-1 text-xs font-medium transition-colors {loc ===
					currentLocale
						? 'border-primary-500 bg-primary-500 text-white'
						: 'border-surface-200-800 bg-surface-50-950 text-surface-600-400 hover:border-primary-500/50 hover:text-primary-500'}"
				>
					{localeName(loc)}
				</button>
			{/each}
			{#if missingLocales.length}
				<button
					type="button"
					class="rounded-md border border-dashed border-surface-300-700 px-2.5 py-1 text-xs text-surface-500 transition-colors hover:border-primary-500/50 hover:text-primary-500"
					onclick={startAddLang}
				>
					<i class="fa-solid fa-plus mr-1"></i>{m.addLanguage()}
				</button>
			{/if}
		</div>

		{#if addingLang}
			<div
				class="flex flex-wrap items-end gap-3 rounded-lg border border-surface-200-800 bg-surface-100-900 p-3"
			>
				<label class="label">
					<span class="text-xs font-semibold">{m.language()}</span>
					<select bind:value={newLocale} class="select mt-1">
						{#each missingLocales as loc (loc)}
							<option value={loc}>{localeName(loc)}</option>
						{/each}
					</select>
				</label>
				<label class="label min-w-[16rem] flex-1">
					<span class="text-xs font-semibold">{m.file()}</span>
					<input
						type="file"
						class="input mt-1"
						onchange={(e) => (newLangFile = (e.target as HTMLInputElement).files?.[0] ?? null)}
					/>
				</label>
				<button
					class="btn btn-sm variant-filled-primary"
					disabled={busy || !newLocale || !newLangFile}
					onclick={addLanguage}
				>
					{m.add()}
				</button>
				<button class="btn btn-sm variant-soft" onclick={() => (addingLang = false)}>
					{m.cancel()}
				</button>
			</div>
		{/if}
	{/if}

	<!-- File card -->
	<div class="space-y-4 rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 shadow-sm">
		{#if currentFileUrl}
			<a href={currentFileUrl} target="_blank" rel="noopener" class="btn variant-filled-primary">
				<i class="fa-solid fa-download mr-2"></i>{m.download()}
			</a>
			{#if isPdf}
				<iframe
					src={currentFileUrl}
					title={parent?.name}
					class="h-[70vh] w-full rounded-xl border border-surface-200-800"
				></iframe>
			{/if}
		{:else}
			<p class="text-sm text-surface-500">{m.noFileUploaded()}</p>
		{/if}

		<!-- Reviewer comments (shown while under review) -->
		{#if isInReview}
			<div
				class="flex items-start gap-3 rounded-lg border border-primary-500/30 bg-primary-500/5 px-4 py-3"
			>
				<i class="fa-solid fa-pen-to-square mt-0.5 text-primary-400"></i>
				<label class="min-w-0 flex-1 text-sm">
					<span class="mb-1 block font-medium text-primary-700 dark:text-primary-300">
						{m.reviewerComments()}
					</span>
					<textarea
						bind:value={reviewerComments}
						class="input w-full text-sm"
						rows="2"
						placeholder={m.addReviewerComments()}
					></textarea>
				</label>
			</div>
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
			<button
				class="btn btn-sm variant-soft-error ml-auto"
				disabled={busy}
				onclick={deleteDocument}
			>
				<i class="fa-solid fa-trash mr-2"></i>{m.delete()}
			</button>
		</div>
	</div>

	<!-- Version history -->
	{#if revisions.length}
		<section class="space-y-2">
			<h2 class="text-sm font-semibold uppercase tracking-wide text-surface-600-400">
				{m.versionHistory()}
			</h2>
			<ul
				class="divide-y divide-surface-200-800 overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950"
			>
				{#each revisions as rev (rev.id)}
					<li class="flex items-center justify-between gap-2 px-4 py-2.5 text-sm">
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
