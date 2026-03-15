<script lang="ts">
	import { fly, fade, scale } from 'svelte/transition';
	import { tick } from 'svelte';
	import { page } from '$app/stores';
	import type { ChatMessage } from './types';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import {
		getView,
		getMessages,
		getInputText,
		setInputText,
		getIsTyping,
		openChat,
		closeChat,
		expandChat,
		collapseChat,
		sendMessage,
		startNewSession,
		retryLastMessage,
		copyToClipboard,
		setPageContext,
		confirmAction,
		rejectAction,
		suggestedActions
	} from './chatStore.svelte';

	let copiedId = $state<string | null>(null);
	let expandedThinking = $state<Set<string>>(new Set());

	// Keep page context in sync with current route
	$effect(() => {
		const path = $page.url.pathname;
		const model = $page.data?.modelVerboseName;
		const title = $page.data?.title;
		setPageContext({ path, model, title });
	});

	async function handleCopy(text: string, id: string) {
		const ok = await copyToClipboard(text);
		if (ok) {
			copiedId = id;
			setTimeout(() => (copiedId = null), 1500);
		}
	}

	let messagesContainer: HTMLElement | null = $state(null);
	let inputElement: HTMLInputElement | null = $state(null);

	const view = $derived(getView());
	const messages = $derived(getMessages());
	const inputText = $derived(getInputText());
	const isTyping = $derived(getIsTyping());
	const hasUserMessages = $derived(messages.some((m) => m.role === 'user'));

	$effect(() => {
		// Trigger scroll whenever messages change or typing state changes
		messages.length;
		isTyping;
		scrollToBottom();
	});

	$effect(() => {
		if (view === 'window' || view === 'expanded') {
			tick().then(() => inputElement?.focus());
		}
	});

	async function scrollToBottom() {
		await tick();
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	}

	function handleSend() {
		sendMessage(inputText);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSend();
		}
	}

	function handleGlobalKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && view !== 'closed') {
			e.preventDefault();
			closeChat();
		}
	}

	function formatTime(date: Date): string {
		return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
	}
</script>

<svelte:window onkeydown={handleGlobalKeydown} />

<!-- State 1: FAB Button -->
{#if view === 'closed'}
	<button
		transition:scale={{ duration: 150 }}
		onclick={openChat}
		class="fixed bottom-6 right-6 z-950 flex h-14 w-14 items-center justify-center rounded-full
			bg-gradient-to-br from-violet-600 to-purple-700 text-white shadow-lg
			transition-transform hover:scale-110 active:scale-95"
		aria-label="Open chat assistant"
	>
		<i class="fa-solid fa-comments text-lg"></i>
		<!-- Pulse dot -->
		<span class="absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5">
			<span
				class="absolute inline-flex h-full w-full animate-ping rounded-full bg-pink-400 opacity-75"
			></span>
			<span class="relative inline-flex h-3.5 w-3.5 rounded-full bg-pink-500"></span>
		</span>
	</button>
{/if}

<!-- State 2: Chat Window (compact) -->
{#if view === 'window'}
	<div
		transition:fly={{ y: 20, duration: 200 }}
		class="fixed bottom-6 right-6 z-950 flex h-[520px] w-[400px] flex-col overflow-hidden
			rounded-2xl bg-white shadow-2xl"
	>
		<!-- Header -->
		<div
			class="flex items-center justify-between bg-gradient-to-r from-violet-600 to-purple-700 px-4 py-3"
		>
			<div class="flex items-center gap-2.5">
				<div class="flex h-8 w-8 items-center justify-center rounded-full bg-white/20">
					<i class="fa-solid fa-robot text-sm text-white"></i>
				</div>
				<div>
					<div class="text-sm font-semibold text-white">CISO Assistant</div>
					<div class="text-xs text-violet-200">AI-powered help</div>
				</div>
			</div>
			<div class="flex items-center gap-1">
				<button
					onclick={startNewSession}
					class="flex h-8 w-8 items-center justify-center rounded-lg text-white/80
						transition-colors hover:bg-white/20 hover:text-white"
					aria-label="New conversation"
				>
					<i class="fa-solid fa-plus text-sm"></i>
				</button>
				<button
					onclick={expandChat}
					class="flex h-8 w-8 items-center justify-center rounded-lg text-white/80
						transition-colors hover:bg-white/20 hover:text-white"
					aria-label="Expand chat"
				>
					<i class="fa-solid fa-expand text-sm"></i>
				</button>
				<button
					onclick={closeChat}
					class="flex h-8 w-8 items-center justify-center rounded-lg text-white/80
						transition-colors hover:bg-white/20 hover:text-white"
					aria-label="Close chat"
				>
					<i class="fa-solid fa-xmark text-sm"></i>
				</button>
			</div>
		</div>

		<!-- Messages -->
		<div bind:this={messagesContainer} class="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-3">
			{#each messages as message (message.id)}
				{#if message.role === 'assistant'}
					<div class="group flex gap-2.5">
						<div
							class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full
								bg-violet-100 text-violet-600"
						>
							<i class="fa-solid fa-robot text-xs"></i>
						</div>
						<div>
							{#if message.thinking}
								{@const thinkingDone = !!message.content}
								<button
									onclick={() => {
										const next = new Set(expandedThinking);
										if (next.has(message.id)) next.delete(message.id);
										else next.add(message.id);
										expandedThinking = next;
									}}
									class="mb-1.5 flex items-center gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5
										text-[11px] text-amber-700 transition-colors hover:bg-amber-100"
								>
									<i
										class="fa-solid fa-chevron-{expandedThinking.has(message.id)
											? 'down'
											: 'right'} text-[9px] transition-transform"
									></i>
									<i class="fa-solid fa-brain text-[10px] text-amber-500"></i>
									{thinkingDone ? 'Thought' : 'Thinking...'}
								</button>
								{#if expandedThinking.has(message.id)}
									<div
										class="mb-1.5 max-h-48 overflow-y-auto rounded-xl bg-amber-50/60 px-3 py-2
											text-[11px] leading-relaxed text-amber-900/70 border border-amber-100"
									>
										<MarkdownRenderer content={message.thinking} />
									</div>
								{/if}
							{/if}
							{#if message.content}
								<div
									class="rounded-2xl rounded-tl-sm bg-gray-100 px-3.5 py-2.5 text-sm
										text-gray-800"
								>
									<MarkdownRenderer content={message.content} />
								</div>
							{/if}
							{#if message.pendingAction}
								{@const pa = message.pendingAction}
								<div class="mt-2 rounded-xl border border-gray-200 bg-white p-3 shadow-sm">
									<div class="mb-2 flex items-center gap-2 text-xs font-medium text-gray-600">
										{#if pa.action === 'attach'}
											<i class="fa-solid fa-link text-violet-500"></i>
											Attach {pa.items.length}
											{pa.displayName}
										{:else}
											<i class="fa-solid fa-plus-circle text-violet-500"></i>
											Create {pa.items.length}
											{pa.displayName}
										{/if}
									</div>
									<ul class="mb-2 space-y-1">
										{#each pa.items as item, i}
											<li class="flex items-center gap-2 text-xs text-gray-700">
												{#if pa.status === 'created' && pa.results?.[i] && !pa.results[i].error}
													<i class="fa-solid fa-check text-green-500 text-[10px]"></i>
													<span>{item.name}</span>
												{:else if pa.status === 'error' && pa.results?.[i]?.error}
													<i class="fa-solid fa-xmark text-red-500 text-[10px]"></i>
													<span>{item.name}</span>
													<span class="text-red-400">({pa.results[i].error})</span>
												{:else if pa.status === 'creating'}
													{#if pa.results && pa.results.length > i}
														<i class="fa-solid fa-check text-green-500 text-[10px]"></i>
													{:else}
														<i class="fa-solid fa-spinner fa-spin text-violet-400 text-[10px]"></i>
													{/if}
													<span>{item.name}</span>
												{:else}
													<i class="fa-solid fa-circle text-gray-300 text-[8px]"></i>
													<span>{item.name}</span>
												{/if}
											</li>
										{/each}
									</ul>
									{#if pa.status === 'pending'}
										<div class="flex gap-2">
											<button
												onclick={() => confirmAction(message.id)}
												class="rounded-lg bg-violet-600 px-3 py-1.5 text-[11px] font-medium text-white
													transition-colors hover:bg-violet-700"
											>
												<i class="fa-solid fa-check mr-1"></i>Confirm
											</button>
											<button
												onclick={() => rejectAction(message.id)}
												class="rounded-lg bg-gray-100 px-3 py-1.5 text-[11px] font-medium text-gray-600
													transition-colors hover:bg-gray-200"
											>
												Cancel
											</button>
										</div>
									{:else if pa.status === 'rejected'}
										<div class="text-[11px] text-gray-400 italic">Cancelled</div>
									{:else if pa.status === 'created'}
										<div class="text-[11px] text-green-600 font-medium">
											<i class="fa-solid fa-check-circle mr-1"></i>
											{pa.action === 'attach' ? 'Attached successfully' : 'Created successfully'}
										</div>
									{/if}
								</div>
							{/if}
							<div class="mt-1 flex items-center gap-1 px-1">
								<span class="text-[10px] text-gray-400">{formatTime(message.timestamp)}</span>
								{#if message.id !== 'welcome' && message.content}
									<button
										onclick={() => handleCopy(message.content, message.id)}
										class="ml-1 text-gray-300 opacity-0 transition-opacity hover:text-gray-500 group-hover:opacity-100"
										title="Copy response"
									>
										<i
											class="fa-solid {copiedId === message.id
												? 'fa-check text-green-500'
												: 'fa-copy'} text-[10px]"
										></i>
									</button>
								{/if}
							</div>
						</div>
					</div>
				{:else}
					<div class="group flex flex-row-reverse gap-2.5">
						<div
							class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full
								bg-violet-600 text-white"
						>
							<i class="fa-solid fa-user text-xs"></i>
						</div>
						<div class="flex flex-col items-end">
							<div
								class="rounded-2xl rounded-tr-sm bg-violet-600 px-3.5 py-2.5 text-sm
									text-white"
							>
								{message.content}
							</div>
							<div class="mt-1 flex items-center gap-1 px-1">
								<span class="text-[10px] text-gray-400">{formatTime(message.timestamp)}</span>
								<button
									onclick={() => handleCopy(message.content, message.id)}
									class="ml-1 text-gray-300 opacity-0 transition-opacity hover:text-gray-500 group-hover:opacity-100"
									title="Copy prompt"
								>
									<i
										class="fa-solid {copiedId === message.id
											? 'fa-check text-green-500'
											: 'fa-copy'} text-[10px]"
									></i>
								</button>
								<button
									onclick={retryLastMessage}
									class="text-gray-300 opacity-0 transition-opacity hover:text-gray-500 group-hover:opacity-100"
									title="Retry this prompt"
								>
									<i class="fa-solid fa-rotate-right text-[10px]"></i>
								</button>
							</div>
						</div>
					</div>
				{/if}
			{/each}

			<!-- Typing indicator -->
			{#if isTyping}
				<div class="flex gap-2.5">
					<div
						class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full
							bg-violet-100 text-violet-600"
					>
						<i class="fa-solid fa-robot text-xs"></i>
					</div>
					<div class="flex items-center gap-1 rounded-2xl bg-gray-100 px-4 py-3">
						<span
							class="h-2 w-2 animate-bounce rounded-full bg-gray-400"
							style="animation-delay: 0ms"
						></span>
						<span
							class="h-2 w-2 animate-bounce rounded-full bg-gray-400"
							style="animation-delay: 150ms"
						></span>
						<span
							class="h-2 w-2 animate-bounce rounded-full bg-gray-400"
							style="animation-delay: 300ms"
						></span>
					</div>
				</div>
			{/if}

			<!-- Suggested actions (compact: 1-column list) -->
			{#if !hasUserMessages}
				<div class="mt-2 flex flex-col gap-2">
					{#each suggestedActions as action}
						<button
							onclick={() => sendMessage(action.prompt)}
							class="flex items-center gap-2.5 rounded-xl border border-violet-200 bg-violet-50
								px-3.5 py-2.5 text-left text-sm text-violet-700 transition-colors
								hover:border-violet-300 hover:bg-violet-100"
						>
							<i class="{action.icon} text-xs text-violet-500"></i>
							{action.label}
						</button>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Input area -->
		<div class="border-t border-gray-200 px-4 py-3">
			<div class="flex items-center gap-2">
				<input
					bind:this={inputElement}
					bind:value={() => inputText, (v) => setInputText(v)}
					onkeydown={handleKeydown}
					type="text"
					placeholder="Ask a question..."
					class="flex-1 rounded-xl border border-gray-300 bg-gray-50 px-3.5 py-2.5 text-sm
						outline-none transition-colors placeholder:text-gray-400
						focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
				/>
				<button
					onclick={handleSend}
					disabled={!inputText.trim()}
					class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl
						bg-violet-600 text-white transition-colors hover:bg-violet-700
						disabled:opacity-40 disabled:hover:bg-violet-600"
					aria-label="Send message"
				>
					<i class="fa-solid fa-paper-plane text-sm"></i>
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- State 3: Expanded Modal -->
{#if view === 'expanded'}
	<!-- Backdrop -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		transition:fade={{ duration: 200 }}
		class="fixed inset-0 z-[9990] bg-surface-950/60 backdrop-blur-sm"
		onclick={closeChat}
		onkeydown={(e) => e.key === 'Escape' && closeChat()}
	></div>

	<!-- Panel -->
	<div
		transition:fly={{ y: 40, duration: 250 }}
		class="fixed inset-0 z-[9990] flex items-center justify-center p-6"
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="flex h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
		>
			<!-- Header -->
			<div
				class="flex items-center justify-between bg-gradient-to-r from-violet-600 to-purple-700 px-5 py-4"
			>
				<div class="flex items-center gap-3">
					<div class="flex h-10 w-10 items-center justify-center rounded-full bg-white/20">
						<i class="fa-solid fa-robot text-white"></i>
					</div>
					<div>
						<div class="font-semibold text-white">CISO Assistant</div>
						<div class="text-sm text-violet-200">AI-powered help</div>
					</div>
				</div>
				<div class="flex items-center gap-1">
					<button
						onclick={startNewSession}
						class="flex h-9 w-9 items-center justify-center rounded-lg text-white/80
							transition-colors hover:bg-white/20 hover:text-white"
						aria-label="New conversation"
					>
						<i class="fa-solid fa-plus text-sm"></i>
					</button>
					<button
						onclick={collapseChat}
						class="flex h-9 w-9 items-center justify-center rounded-lg text-white/80
							transition-colors hover:bg-white/20 hover:text-white"
						aria-label="Collapse chat"
					>
						<i class="fa-solid fa-compress text-sm"></i>
					</button>
					<button
						onclick={closeChat}
						class="flex h-9 w-9 items-center justify-center rounded-lg text-white/80
							transition-colors hover:bg-white/20 hover:text-white"
						aria-label="Close chat"
					>
						<i class="fa-solid fa-xmark text-sm"></i>
					</button>
				</div>
			</div>

			<!-- Messages -->
			<div
				bind:this={messagesContainer}
				class="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-4"
			>
				{#each messages as message (message.id)}
					{#if message.role === 'assistant'}
						<div class="group flex gap-3">
							<div
								class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full
									bg-violet-100 text-violet-600"
							>
								<i class="fa-solid fa-robot text-sm"></i>
							</div>
							<div class="max-w-[80%]">
								{#if message.thinking}
									{@const thinkingDone = !!message.content}
									<button
										onclick={() => {
											const next = new Set(expandedThinking);
											if (next.has(message.id)) next.delete(message.id);
											else next.add(message.id);
											expandedThinking = next;
										}}
										class="mb-2 flex items-center gap-1.5 rounded-lg bg-amber-50 px-3 py-2
											text-xs text-amber-700 transition-colors hover:bg-amber-100"
									>
										<i
											class="fa-solid fa-chevron-{expandedThinking.has(message.id)
												? 'down'
												: 'right'} text-[10px] transition-transform"
										></i>
										<i class="fa-solid fa-brain text-xs text-amber-500"></i>
										{thinkingDone ? 'Thought' : 'Thinking...'}
									</button>
									{#if expandedThinking.has(message.id)}
										<div
											class="mb-2 max-h-64 overflow-y-auto rounded-xl bg-amber-50/60 px-4 py-3
												text-xs leading-relaxed text-amber-900/70 border border-amber-100"
										>
											<MarkdownRenderer content={message.thinking} />
										</div>
									{/if}
								{/if}
								{#if message.content}
									<div
										class="rounded-2xl rounded-tl-sm bg-gray-100 px-4 py-3 text-sm
											text-gray-800"
									>
										<MarkdownRenderer content={message.content} />
									</div>
								{/if}
								{#if message.pendingAction}
									{@const pa = message.pendingAction}
									<div class="mt-2 rounded-xl border border-gray-200 bg-white p-3.5 shadow-sm">
										<div class="mb-2 flex items-center gap-2 text-sm font-medium text-gray-600">
											{#if pa.action === 'attach'}
												<i class="fa-solid fa-link text-violet-500"></i>
												Attach {pa.items.length}
												{pa.displayName}
											{:else}
												<i class="fa-solid fa-plus-circle text-violet-500"></i>
												Create {pa.items.length}
												{pa.displayName}
											{/if}
										</div>
										<ul class="mb-3 space-y-1.5">
											{#each pa.items as item, i}
												<li class="flex items-center gap-2 text-sm text-gray-700">
													{#if pa.status === 'created' && pa.results?.[i] && !pa.results[i].error}
														<i class="fa-solid fa-check text-green-500 text-xs"></i>
														<span>{item.name}</span>
													{:else if pa.status === 'error' && pa.results?.[i]?.error}
														<i class="fa-solid fa-xmark text-red-500 text-xs"></i>
														<span>{item.name}</span>
														<span class="text-red-400 text-xs">({pa.results[i].error})</span>
													{:else if pa.status === 'creating'}
														{#if pa.results && pa.results.length > i}
															<i class="fa-solid fa-check text-green-500 text-xs"></i>
														{:else}
															<i class="fa-solid fa-spinner fa-spin text-violet-400 text-xs"></i>
														{/if}
														<span>{item.name}</span>
													{:else}
														<i class="fa-solid fa-circle text-gray-300 text-[9px]"></i>
														<span>{item.name}</span>
													{/if}
												</li>
											{/each}
										</ul>
										{#if pa.status === 'pending'}
											<div class="flex gap-2">
												<button
													onclick={() => confirmAction(message.id)}
													class="rounded-lg bg-violet-600 px-4 py-2 text-xs font-medium text-white
														transition-colors hover:bg-violet-700"
												>
													<i class="fa-solid fa-check mr-1"></i>Confirm
												</button>
												<button
													onclick={() => rejectAction(message.id)}
													class="rounded-lg bg-gray-100 px-4 py-2 text-xs font-medium text-gray-600
														transition-colors hover:bg-gray-200"
												>
													Cancel
												</button>
											</div>
										{:else if pa.status === 'rejected'}
											<div class="text-xs text-gray-400 italic">Cancelled</div>
										{:else if pa.status === 'created'}
											<div class="text-xs text-green-600 font-medium">
												<i class="fa-solid fa-check-circle mr-1"></i>
												{pa.action === 'attach' ? 'Attached successfully' : 'Created successfully'}
											</div>
										{/if}
									</div>
								{/if}
								<div class="mt-1 flex items-center gap-1.5 px-1">
									<span class="text-[10px] text-gray-400">{formatTime(message.timestamp)}</span>
									{#if message.id !== 'welcome' && message.content}
										<button
											onclick={() => handleCopy(message.content, message.id)}
											class="ml-1 text-gray-300 opacity-0 transition-opacity hover:text-gray-500 group-hover:opacity-100"
											title="Copy response"
										>
											<i
												class="fa-solid {copiedId === message.id
													? 'fa-check text-green-500'
													: 'fa-copy'} text-xs"
											></i>
										</button>
									{/if}
								</div>
							</div>
						</div>
					{:else}
						<div class="group flex flex-row-reverse gap-3">
							<div
								class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full
									bg-violet-600 text-white"
							>
								<i class="fa-solid fa-user text-sm"></i>
							</div>
							<div class="flex max-w-[80%] flex-col items-end">
								<div
									class="rounded-2xl rounded-tr-sm bg-violet-600 px-4 py-3 text-sm
										text-white"
								>
									{message.content}
								</div>
								<div class="mt-1 flex items-center gap-1.5 px-1">
									<span class="text-[10px] text-gray-400">{formatTime(message.timestamp)}</span>
									<button
										onclick={() => handleCopy(message.content, message.id)}
										class="ml-1 text-gray-300 opacity-0 transition-opacity hover:text-gray-500 group-hover:opacity-100"
										title="Copy prompt"
									>
										<i
											class="fa-solid {copiedId === message.id
												? 'fa-check text-green-500'
												: 'fa-copy'} text-xs"
										></i>
									</button>
									<button
										onclick={retryLastMessage}
										class="text-gray-300 opacity-0 transition-opacity hover:text-gray-500 group-hover:opacity-100"
										title="Retry this prompt"
									>
										<i class="fa-solid fa-rotate-right text-xs"></i>
									</button>
								</div>
							</div>
						</div>
					{/if}
				{/each}

				<!-- Typing indicator -->
				{#if isTyping}
					<div class="flex gap-3">
						<div
							class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full
								bg-violet-100 text-violet-600"
						>
							<i class="fa-solid fa-robot text-sm"></i>
						</div>
						<div class="flex items-center gap-1 rounded-2xl bg-gray-100 px-5 py-3">
							<span
								class="h-2 w-2 animate-bounce rounded-full bg-gray-400"
								style="animation-delay: 0ms"
							></span>
							<span
								class="h-2 w-2 animate-bounce rounded-full bg-gray-400"
								style="animation-delay: 150ms"
							></span>
							<span
								class="h-2 w-2 animate-bounce rounded-full bg-gray-400"
								style="animation-delay: 300ms"
							></span>
						</div>
					</div>
				{/if}

				<!-- Suggested actions (expanded: 2x2 grid) -->
				{#if !hasUserMessages}
					<div class="mt-3 grid grid-cols-2 gap-3">
						{#each suggestedActions as action}
							<button
								onclick={() => sendMessage(action.prompt)}
								class="flex items-center gap-3 rounded-xl border border-violet-200 bg-violet-50
									px-4 py-3 text-left text-sm text-violet-700 transition-colors
									hover:border-violet-300 hover:bg-violet-100"
							>
								<i class="{action.icon} text-violet-500"></i>
								{action.label}
							</button>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Input area -->
			<div class="border-t border-gray-200 px-6 py-4">
				<div class="flex items-center gap-3">
					<input
						bind:this={inputElement}
						bind:value={() => inputText, (v) => setInputText(v)}
						onkeydown={handleKeydown}
						type="text"
						placeholder="Ask a question..."
						class="flex-1 rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-sm
							outline-none transition-colors placeholder:text-gray-400
							focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
					/>
					<button
						onclick={handleSend}
						disabled={!inputText.trim()}
						class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl
							bg-violet-600 text-white transition-colors hover:bg-violet-700
							disabled:opacity-40 disabled:hover:bg-violet-600"
						aria-label="Send message"
					>
						<i class="fa-solid fa-paper-plane text-sm"></i>
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
