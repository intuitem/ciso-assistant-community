<script lang="ts">
	import { fly, fade, scale } from 'svelte/transition';
	import { tick } from 'svelte';
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
		suggestedActions
	} from './chatStore.svelte';

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
					<div class="flex gap-2.5">
						<div
							class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full
								bg-violet-100 text-violet-600"
						>
							<i class="fa-solid fa-robot text-xs"></i>
						</div>
						<div>
							<div
								class="rounded-2xl rounded-tl-sm bg-gray-100 px-3.5 py-2.5 text-sm
									text-gray-800"
							>
								{message.content}
							</div>
							<div class="mt-1 px-1 text-[10px] text-gray-400">
								{formatTime(message.timestamp)}
							</div>
						</div>
					</div>
				{:else}
					<div class="flex flex-row-reverse gap-2.5">
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
							<div class="mt-1 px-1 text-[10px] text-gray-400">
								{formatTime(message.timestamp)}
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
						<div class="flex gap-3">
							<div
								class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full
									bg-violet-100 text-violet-600"
							>
								<i class="fa-solid fa-robot text-sm"></i>
							</div>
							<div class="max-w-[80%]">
								<div
									class="rounded-2xl rounded-tl-sm bg-gray-100 px-4 py-3 text-sm
										text-gray-800"
								>
									{message.content}
								</div>
								<div class="mt-1 px-1 text-[10px] text-gray-400">
									{formatTime(message.timestamp)}
								</div>
							</div>
						</div>
					{:else}
						<div class="flex flex-row-reverse gap-3">
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
								<div class="mt-1 px-1 text-[10px] text-gray-400">
									{formatTime(message.timestamp)}
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
