<script lang="ts">
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { browser } from '$app/environment';
	import {
		getModalStore,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	type CommentParentType =
		| 'requirement_assessment'
		| 'risk_scenario'
		| 'applied_control'
		| 'finding';

	interface CommentAuthor {
		id: string;
		email: string;
		first_name: string;
		last_name: string;
	}

	interface Comment {
		id: string;
		body: string;
		is_tainted: boolean;
		is_active: boolean;
		author: CommentAuthor;
		created_at: string;
		updated_at: string;
	}

	interface Props {
		parentType: CommentParentType;
		parentId: string;
	}

	let { parentType, parentId }: Props = $props();

	let comments: Comment[] = $state([]);
	let newCommentBody = $state('');
	let editingId: string | null = $state(null);
	let editBody = $state('');
	let submitting = $state(false);
	let loading = $state(true);
	let composerFocused = $state(false);
	let hideProcessed = $state(false);

	let visibleComments = $derived(hideProcessed ? comments.filter((c) => c.is_active) : comments);
	let processedCount = $derived(comments.filter((c) => !c.is_active).length);

	const currentUserId: string = page.data.user?.id ?? '';
	const isAdmin: boolean = page.data.user?.is_admin ?? false;
	const modalStore: ModalStore = getModalStore();

	const avatarColors = [
		'bg-violet-100 text-violet-700',
		'bg-sky-100 text-sky-700',
		'bg-amber-100 text-amber-700',
		'bg-emerald-100 text-emerald-700',
		'bg-rose-100 text-rose-700',
		'bg-indigo-100 text-indigo-700',
		'bg-teal-100 text-teal-700',
		'bg-orange-100 text-orange-700'
	];

	function getAvatarColor(authorId: string): string {
		let hash = 0;
		for (let i = 0; i < authorId.length; i++) {
			hash = authorId.charCodeAt(i) + ((hash << 5) - hash);
		}
		return avatarColors[Math.abs(hash) % avatarColors.length];
	}

	function getInitials(author: CommentAuthor): string {
		const first = author.first_name?.[0] ?? '';
		const last = author.last_name?.[0] ?? '';
		if (first || last) return (first + last).toUpperCase();
		return author.email?.[0]?.toUpperCase() ?? '?';
	}

	function getDisplayName(author: CommentAuthor): string {
		if (author.first_name || author.last_name) {
			return `${author.first_name ?? ''} ${author.last_name ?? ''}`.trim();
		}
		return author.email ?? 'Unknown';
	}

	function timeAgo(dateStr: string): string {
		const now = Date.now();
		const date = new Date(dateStr).getTime();
		const seconds = Math.floor((now - date) / 1000);

		if (seconds < 60) return m.justNow();
		const minutes = Math.floor(seconds / 60);
		if (minutes < 60) return m.minutesAgo({ count: String(minutes) });
		const hours = Math.floor(minutes / 60);
		if (hours < 24) return m.hoursAgo({ count: String(hours) });
		const days = Math.floor(hours / 24);
		if (days < 30) return m.daysAgo({ count: String(days) });
		return new Date(dateStr).toLocaleDateString();
	}

	async function fetchComments() {
		loading = true;
		try {
			const res = await fetch(`/fe-api/comments?${parentType}=${parentId}&ordering=created_at`);
			if (res.ok) {
				const data = await res.json();
				comments = data.results ?? [];
			} else {
				comments = [];
			}
		} catch {
			comments = [];
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (browser && parentId) {
			fetchComments();
		}
	});

	async function postComment() {
		if (!newCommentBody.trim() || submitting) return;
		submitting = true;
		try {
			const res = await fetch('/fe-api/comments', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					body: newCommentBody.trim(),
					[parentType]: parentId
				})
			});
			if (res.ok) {
				newCommentBody = '';
				await fetchComments();
			}
		} finally {
			submitting = false;
		}
	}

	function startEdit(comment: Comment) {
		editingId = comment.id;
		editBody = comment.body;
	}

	function cancelEdit() {
		editingId = null;
		editBody = '';
	}

	async function saveEdit(commentId: string) {
		if (!editBody.trim() || submitting) return;
		submitting = true;
		try {
			const res = await fetch(`/fe-api/comments/${commentId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ body: editBody.trim() })
			});
			if (res.ok) {
				editingId = null;
				editBody = '';
				await fetchComments();
			}
		} finally {
			submitting = false;
		}
	}

	async function toggleActive(comment: Comment) {
		await fetch(`/fe-api/comments/${comment.id}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ is_active: !comment.is_active })
		});
		await fetchComments();
	}

	function deleteComment(commentId: string) {
		const modal: ModalSettings = {
			type: 'confirm',
			title: m.deleteCommentConfirmation(),
			buttonTextConfirm: m.delete(),
			response: async (confirmed: boolean) => {
				if (!confirmed) return;
				await fetch(`/fe-api/comments/${commentId}`, {
					method: 'DELETE'
				});
				await fetchComments();
			}
		};
		modalStore.trigger(modal);
	}

	function canEdit(comment: Comment): boolean {
		return comment.author?.id === currentUserId;
	}

	function canDelete(comment: Comment): boolean {
		return comment.author?.id === currentUserId || isAdmin;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
			postComment();
		}
	}
</script>

<div class="comments-panel">
	<!-- Header -->
	<div class="flex items-center gap-2.5 mb-4">
		<div class="flex items-center justify-center w-7 h-7 rounded-md bg-surface-100">
			<i class="fa-solid fa-comments text-xs text-surface-500"></i>
		</div>
		<h4 class="text-sm font-semibold tracking-tight text-surface-700">
			{m.comments()}
		</h4>
		{#if !loading}
			<span
				class="inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full
				text-[11px] font-medium bg-surface-100 text-surface-500"
			>
				{comments.length}
			</span>
		{/if}
		{#if processedCount > 0}
			<button
				class="ml-auto inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px]
				transition-all duration-150
				{hideProcessed
					? 'bg-emerald-50 text-emerald-600 border border-emerald-200'
					: 'text-surface-400 hover:text-surface-600 hover:bg-surface-50'}"
				onclick={() => (hideProcessed = !hideProcessed)}
			>
				<i class="fa-solid {hideProcessed ? 'fa-eye' : 'fa-eye-slash'} text-[10px]"></i>
				{hideProcessed ? m.showProcessed({ count: String(processedCount) }) : m.hideProcessed()}
			</button>
		{/if}
	</div>

	<!-- Thread -->
	{#if loading}
		<div class="flex items-center justify-center py-8">
			<div class="loading-dot"></div>
			<div class="loading-dot" style="animation-delay: 0.15s"></div>
			<div class="loading-dot" style="animation-delay: 0.3s"></div>
		</div>
	{:else if comments.length === 0}
		<div class="flex flex-col items-center py-6 text-surface-400">
			<i class="fa-regular fa-comment-dots text-2xl mb-2 opacity-40"></i>
			<p class="text-xs">{m.noComments()}</p>
		</div>
	{:else}
		<div class="relative">
			<!-- Timeline connector -->
			{#if visibleComments.length > 1}
				<div
					class="absolute left-[15px] top-4 bottom-4 w-px bg-surface-200"
					style="z-index: 0;"
				></div>
			{/if}

			<div class="space-y-1">
				{#each visibleComments as comment, i (comment.id)}
					<div
						class="comment-entry group relative"
						class:comment-processed={!comment.is_active}
						style="animation-delay: {i * 40}ms"
					>
						<!-- Avatar -->
						<div
							class="relative z-10 flex-shrink-0 w-8 h-8 rounded-full
							flex items-center justify-center text-[11px] font-semibold
							ring-2 ring-white transition-transform duration-200
							group-hover:scale-105 {getAvatarColor(comment.author?.id ?? '')}"
						>
							{getInitials(comment.author)}
						</div>

						<!-- Content -->
						<div class="flex-1 min-w-0 pt-0.5">
							<!-- Meta line -->
							<div class="flex items-center gap-1.5 flex-wrap">
								<span class="text-[13px] font-medium text-surface-800">
									{getDisplayName(comment.author)}
								</span>
								<span class="text-[11px] text-surface-400">
									{timeAgo(comment.created_at)}
								</span>
								{#if comment.is_tainted}
									<span class="text-[10px] text-surface-400 italic">
										({m.commentEdited()})
									</span>
								{/if}
								{#if !comment.is_active}
									<span
										class="inline-flex items-center gap-0.5 px-1.5 py-px rounded-full
										text-[10px] font-medium bg-emerald-50 text-emerald-600 border border-emerald-200"
									>
										<i class="fa-solid fa-check text-[8px]"></i>
										{m.processed()}
									</span>
								{/if}
							</div>

							<!-- Body or Edit form -->
							{#if editingId === comment.id}
								<div class="mt-2 space-y-2">
									<textarea
										class="textarea text-sm w-full rounded-xl border-surface-300
										focus:border-primary-400 focus:ring-1 focus:ring-primary-200
										transition-all duration-200"
										rows="3"
										bind:value={editBody}
									></textarea>
									<div class="flex gap-2">
										<button
											class="btn btn-sm preset-filled-primary-500 text-xs rounded-md"
											disabled={submitting || !editBody.trim()}
											onclick={() => saveEdit(comment.id)}
										>
											{m.save()}
										</button>
										<button
											class="btn btn-sm text-xs rounded-md text-surface-500
											hover:text-surface-700 hover:bg-surface-100 transition-colors duration-150"
											onclick={cancelEdit}
										>
											{m.cancel()}
										</button>
									</div>
								</div>
							{:else}
								<p
									class="text-[13px] leading-relaxed mt-0.5 text-surface-600
									whitespace-pre-wrap break-words"
								>
									{comment.body}
								</p>
							{/if}

							<!-- Actions (appear on hover) -->
							{#if editingId !== comment.id && (canEdit(comment) || canDelete(comment))}
								<div
									class="flex gap-0.5 mt-1.5 opacity-0 group-hover:opacity-100
									transition-opacity duration-150"
								>
									{#if canEdit(comment)}
										<button
											class="comment-action-btn"
											onclick={() => toggleActive(comment)}
											title={comment.is_active ? m.markAsProcessed() : m.markAsActive()}
										>
											<i
												class="fa-solid {comment.is_active
													? 'fa-check'
													: 'fa-rotate-left'} text-[10px]"
											></i>
											<span>
												{comment.is_active ? m.markAsProcessed() : m.markAsActive()}
											</span>
										</button>
										<button class="comment-action-btn" onclick={() => startEdit(comment)}>
											<i class="fa-solid fa-pen text-[10px]"></i>
										</button>
									{/if}
									{#if canDelete(comment)}
										<button
											class="comment-action-btn comment-action-btn-danger"
											onclick={() => deleteComment(comment.id)}
										>
											<i class="fa-solid fa-trash text-[10px]"></i>
										</button>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Composer -->
	<div class="mt-4 pt-4 border-t border-surface-200">
		<div class="composer-box" class:composer-focused={composerFocused}>
			<textarea
				class="w-full bg-transparent text-[13px] text-surface-700
				placeholder:text-surface-400 resize-none outline-none
				border-none leading-relaxed"
				rows="2"
				placeholder={m.commentPlaceholder()}
				bind:value={newCommentBody}
				onkeydown={handleKeydown}
				onfocus={() => (composerFocused = true)}
				onblur={() => (composerFocused = false)}
			></textarea>
			<div class="flex items-center justify-between mt-1">
				<span class="text-[10px] text-surface-400">
					{#if composerFocused || newCommentBody.trim()}
						{m.ctrlEnterToPost()}
					{/if}
				</span>
				<button
					class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
					transition-all duration-200
					{newCommentBody.trim() && !submitting
						? 'bg-primary-500 text-white shadow-sm shadow-primary-200 hover:bg-primary-600 hover:shadow-md hover:shadow-primary-200 active:scale-[0.97]'
						: 'bg-surface-100 text-surface-400 cursor-not-allowed'}"
					disabled={submitting || !newCommentBody.trim()}
					onclick={postComment}
				>
					{#if submitting}
						<i class="fa-solid fa-spinner fa-spin text-[10px]"></i>
					{:else}
						<i class="fa-solid fa-paper-plane text-[10px]"></i>
					{/if}
					{m.postComment()}
				</button>
			</div>
		</div>
	</div>
</div>

<style>
	.comments-panel {
		padding: 1.25rem;
		border-radius: 0.75rem;
		background: white;
		border: 1px solid var(--color-surface-200);
	}

	.comment-entry {
		display: flex;
		gap: 0.75rem;
		padding: 0.625rem 0.5rem;
		border-radius: 0.5rem;
		transition: background-color 0.15s ease;
		animation: comment-in 0.25s ease-out both;
	}

	.comment-entry:hover {
		background-color: var(--color-surface-50);
	}

	.comment-processed {
		opacity: 0.55;
	}

	.comment-processed:hover {
		opacity: 0.8;
	}

	.comment-action-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.6875rem;
		color: var(--color-surface-500);
		transition: all 0.15s ease;
		cursor: pointer;
		border: none;
		background: none;
	}

	.comment-action-btn:hover {
		background-color: var(--color-surface-100);
		color: var(--color-surface-700);
	}

	.comment-action-btn-danger:hover {
		background-color: oklch(93% 0.03 25deg);
		color: var(--color-error-500);
	}

	.composer-box {
		padding: 0.75rem;
		border-radius: 0.75rem;
		border: 1px solid var(--color-surface-200);
		background: var(--color-surface-50);
		transition: all 0.2s ease;
	}

	.composer-focused {
		border-color: var(--color-primary-300);
		background: white;
		box-shadow: 0 0 0 3px oklch(92.4% 0.03 290.03deg / 0.4);
	}

	.loading-dot {
		width: 6px;
		height: 6px;
		margin: 0 3px;
		border-radius: 50%;
		background: var(--color-surface-300);
		animation: dot-pulse 1s ease-in-out infinite;
	}

	@keyframes dot-pulse {
		0%,
		80%,
		100% {
			opacity: 0.3;
			transform: scale(0.8);
		}
		40% {
			opacity: 1;
			transform: scale(1);
		}
	}

	@keyframes comment-in {
		from {
			opacity: 0;
			transform: translateY(6px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
