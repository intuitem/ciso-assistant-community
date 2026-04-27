import type { ChatMessage, ChatSession, ChatView, PendingAction, SuggestedAction } from './types';
import { browser } from '$app/environment';
import { m } from '$paraglide/messages';

const CHAT_API = '/fe-api/chat';
const STORAGE_KEY = 'ciso-chat-state';

function getWelcomeMessage(): ChatMessage {
	return {
		id: 'welcome',
		role: 'assistant',
		content: m.chatWelcomeMessage(),
		timestamp: new Date()
	};
}

// --- Session storage persistence ---

interface PersistedState {
	messages: ChatMessage[];
	sessionId: string | null;
	view: ChatView;
}

function loadPersistedState(): PersistedState | null {
	if (!browser) return null;
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return null;
		const data = JSON.parse(raw);
		// Restore Date objects and Sets from serialized form
		if (Array.isArray(data.messages)) {
			data.messages = data.messages.map((m: ChatMessage) => ({
				...m,
				timestamp: new Date(m.timestamp),
				...(m.pendingAction && {
					pendingAction: {
						...m.pendingAction,
						selectedIndices: m.pendingAction.selectedIndices
							? new Set(m.pendingAction.selectedIndices as unknown as number[])
							: undefined
					}
				})
			}));
		}
		return data;
	} catch {
		return null;
	}
}

function saveState() {
	if (!browser) return;
	try {
		// Serialize Sets as arrays for JSON compatibility
		const serializable = messages.map((m) => ({
			...m,
			...(m.pendingAction && {
				pendingAction: {
					...m.pendingAction,
					selectedIndices: m.pendingAction.selectedIndices
						? [...m.pendingAction.selectedIndices]
						: undefined
				}
			})
		}));
		const data = { messages: serializable, sessionId, view };
		sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
	} catch {
		// Storage full or unavailable — ignore
	}
}

const restored = loadPersistedState();

// Current page context — updated by ChatWidget via setPageContext()
let currentPageContext = $state<{ path: string; model?: string; title?: string } | null>(null);

let view = $state<ChatView>(restored?.view ?? 'closed');
let messages = $state<ChatMessage[]>(restored?.messages ?? [getWelcomeMessage()]);
let inputText = $state('');
let isTyping = $state(false);
let isStreaming = $state(false);
let sessionId = $state<string | null>(restored?.sessionId ?? null);
let abortController = $state<AbortController | null>(null);
let sessionHistory = $state<ChatSession[]>([]);
let loadingHistory = $state(false);

function getDefaultActions(): SuggestedAction[] {
	return [
		{
			label: m.chatActionOverdueControls(),
			prompt: m.chatActionOverdueControlsPrompt(),
			icon: 'fa-solid fa-clock'
		},
		{
			label: m.chatActionRiskOverview(),
			prompt: m.chatActionRiskOverviewPrompt(),
			icon: 'fa-solid fa-shield-halved'
		},
		{
			label: m.chatActionControlsNoEvidence(),
			prompt: m.chatActionControlsNoEvidencePrompt(),
			icon: 'fa-solid fa-triangle-exclamation'
		},
		{
			label: m.chatActionMyDomains(),
			prompt: m.chatActionMyDomainsPrompt(),
			icon: 'fa-solid fa-folder-tree'
		}
	];
}

// Contextual actions based on the current page
function getContextualActions(): Record<string, SuggestedAction[]> {
	return {
		'requirement-assessments': [
			{
				label: m.chatActionSuggestControls(),
				prompt: m.chatActionSuggestControlsPrompt(),
				icon: 'fa-solid fa-lightbulb'
			},
			{
				label: m.chatActionSuggestEvidence(),
				prompt: m.chatActionSuggestEvidencePrompt(),
				icon: 'fa-solid fa-file-circle-check'
			}
		],
		'risk-scenarios': [
			{
				label: m.chatActionSuggestTreatment(),
				prompt: m.chatActionSuggestTreatmentPrompt(),
				icon: 'fa-solid fa-shield-halved'
			}
		],
		'compliance-assessments': [
			{
				label: m.chatActionComplianceOverview(),
				prompt: m.chatActionComplianceOverviewPrompt(),
				icon: 'fa-solid fa-chart-pie'
			}
		],
		'risk-assessments': [
			{
				label: m.chatActionRiskAssessmentOverview(),
				prompt: m.chatActionRiskAssessmentOverviewPrompt(),
				icon: 'fa-solid fa-triangle-exclamation'
			}
		],
		'ebios-rm': [
			{
				label: m.chatActionAssistStudy(),
				prompt: m.chatActionAssistStudyPrompt(),
				icon: 'fa-solid fa-wand-magic-sparkles'
			}
		]
	};
}

/**
 * Detect the URL slug from the current page path.
 * e.g. "/requirement-assessments/abc-123/edit" → "requirement-assessments"
 */
function getPageSlug(): string | null {
	const path = currentPageContext?.path;
	if (!path) return null;
	const segments = path.replace(/^\//, '').split('/');
	return segments[0] || null;
}

/**
 * Check if the current page is a detail/edit page (has a UUID segment).
 */
function isDetailPage(): boolean {
	const path = currentPageContext?.path;
	if (!path) return false;
	const segments = path.replace(/^\//, '').split('/');
	return segments.length >= 2 && /^[0-9a-f-]{36}$/i.test(segments[1]);
}

export function getSuggestedActions(): SuggestedAction[] {
	const slug = getPageSlug();
	const contextual = getContextualActions();
	const defaults = getDefaultActions();
	if (slug && isDetailPage() && contextual[slug]) {
		return [...contextual[slug], ...defaults];
	}
	return defaults;
}

function generateId(): string {
	return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

async function ensureSession(): Promise<string> {
	if (sessionId) return sessionId;

	const response = await fetch(`${CHAT_API}/sessions`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({})
	});

	if (!response.ok) {
		throw new Error(`Failed to create chat session: ${response.statusText}`);
	}

	const data = await response.json();
	sessionId = data.id;
	saveState();
	return data.id;
}

async function streamResponse(userMessage: string) {
	isTyping = true;

	try {
		const sid = await ensureSession();

		// Cancel any in-flight request
		if (abortController) {
			abortController.abort();
		}
		abortController = new AbortController();

		const response = await fetch(`${CHAT_API}/sessions/${sid}/message`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				content: userMessage,
				...(currentPageContext && { page_context: currentPageContext })
			}),
			signal: abortController.signal
		});

		if (!response.ok) {
			if (response.status === 429) {
				throw new Error('rate_limited');
			}
			throw new Error(`Chat request failed: ${response.statusText}`);
		}

		// Create the assistant message placeholder for streaming
		const assistantMessageId = generateId();
		// Resolve any spinning pending choices from previous messages
		for (const msg of messages) {
			if (msg.pendingChoice?.status === 'selected') {
				msg.pendingChoice.status = 'done';
			}
		}

		messages.push({
			id: assistantMessageId,
			role: 'assistant',
			content: '',
			timestamp: new Date()
		});
		isTyping = false;
		isStreaming = true;

		// Read SSE stream
		const reader = response.body?.getReader();
		const decoder = new TextDecoder();

		if (!reader) {
			throw new Error('No response body');
		}

		let buffer = '';
		let needsFlush = false;
		let flushTimer: ReturnType<typeof setTimeout> | null = null;

		// Batch reactivity updates — flush at most every 30ms to avoid
		// creating a new array copy on every single token
		function scheduleFlush() {
			if (!needsFlush) return;
			if (flushTimer) return;
			flushTimer = setTimeout(() => {
				flushTimer = null;
				if (needsFlush) {
					messages = [...messages];
					needsFlush = false;
				}
			}, 30);
		}

		const STREAM_TIMEOUT_MS = 120_000; // 2 minutes with no data → abort

		while (true) {
			const readResult = await Promise.race([
				reader.read(),
				new Promise<never>((_, reject) =>
					setTimeout(() => reject(new Error('Stream timeout')), STREAM_TIMEOUT_MS)
				)
			]);
			const { done, value } = readResult;
			if (done) break;

			buffer += decoder.decode(value, { stream: true });
			const lines = buffer.split('\n');
			buffer = lines.pop() ?? '';

			for (const line of lines) {
				if (!line.startsWith('data: ')) continue;

				try {
					const data = JSON.parse(line.slice(6));

					if (data.type === 'token') {
						const msg = messages.find((m) => m.id === assistantMessageId);
						if (msg) {
							msg.content += data.content;
							needsFlush = true;
							scheduleFlush();
						}
					} else if (data.type === 'thinking') {
						const msg = messages.find((m) => m.id === assistantMessageId);
						if (msg) {
							msg.thinking = (msg.thinking || '') + data.content;
							needsFlush = true;
							scheduleFlush();
						}
					} else if (data.type === 'navigate') {
						// Workflow wants to redirect — navigate without closing the chat
						if (data.url) {
							const { goto } = await import('$lib/utils/breadcrumbs');
							goto(data.url, { label: '', breadcrumbAction: 'push' });
						}
					} else if (data.type === 'pending_choice') {
						const msg = messages.find((m) => m.id === assistantMessageId);
						if (msg) {
							msg.pendingChoice = {
								id: generateId(),
								field: data.field,
								label: data.label,
								items: data.items,
								status: 'pending'
							};
							messages = [...messages];
						}
					} else if (data.type === 'pending_action') {
						const msg = messages.find((m) => m.id === assistantMessageId);
						if (msg) {
							if (data.action === 'attach') {
								const indices = new Set<number>(data.items.map((_: unknown, i: number) => i));
								msg.pendingAction = {
									id: generateId(),
									action: 'attach',
									displayName: data.related_display,
									items: data.items,
									status: 'pending',
									selectedIndices: indices,
									parentModelKey: data.parent_model_key,
									parentId: data.parent_id,
									parentUrlSlug: data.parent_url_slug,
									m2mField: data.m2m_field
								};
							} else {
								const indices = new Set<number>(data.items.map((_: unknown, i: number) => i));
								msg.pendingAction = {
									id: generateId(),
									action: data.action,
									modelKey: data.model_key,
									urlSlug: data.url_slug,
									displayName: data.display_name,
									items: data.items,
									status: 'pending',
									selectedIndices: indices,
									folderId: data.folder_id,
									folderName: data.folder_name,
									availableFolders: data.available_folders
								};
							}
							messages = [...messages];
						}
					} else if (data.type === 'done') {
						const msg = messages.find((m) => m.id === assistantMessageId);
						if (msg && data.context_refs) {
							msg.contextRefs = data.context_refs;
							messages = [...messages];
						}
					} else if (data.type === 'error') {
						const msg = messages.find((m) => m.id === assistantMessageId);
						if (msg) {
							msg.content = data.content;
							messages = [...messages];
						}
					}
				} catch {
					// Skip malformed SSE lines
				}
			}
		}
		// Final flush for any pending batched updates
		if (flushTimer) clearTimeout(flushTimer);
		if (needsFlush) messages = [...messages];
		isStreaming = false;
		abortController = null;
		saveState();
	} catch (error) {
		isTyping = false;
		isStreaming = false;
		abortController = null;
		if (error instanceof DOMException && error.name === 'AbortError') {
			// Only modify messages if we're still in the same session
			// (avoids tainting messages after switchToSession/startNewSession)
			if (sessionId === sid) {
				const lastMsg = messages[messages.length - 1];
				if (lastMsg?.role === 'assistant' && lastMsg.content) {
					lastMsg.content += '\n\n*— stopped*';
					messages = [...messages];
				}
			}
			saveState();
			return;
		}

		const errMsg = error instanceof Error ? error.message : '';
		let userMessage: string;
		if (errMsg === 'rate_limited') {
			userMessage =
				'Chat is temporarily rate-limited. Please wait a moment before sending another message.';
		} else if (errMsg === 'Stream timeout') {
			userMessage =
				'The response took too long. The LLM service may be overloaded. Your message was not lost — try again.';
		} else {
			userMessage =
				'Sorry, I could not connect to the chat service. Please check that the LLM service is configured and running.';
		}
		messages.push({
			id: generateId(),
			role: 'assistant',
			content: userMessage,
			timestamp: new Date()
		});
		saveState();
	}
}

export function getView(): ChatView {
	return view;
}

export function getMessages(): ChatMessage[] {
	return messages;
}

export function getInputText(): string {
	return inputText;
}

export function setInputText(text: string) {
	inputText = text;
}

export function getIsTyping(): boolean {
	return isTyping;
}

export function getIsStreaming(): boolean {
	return isStreaming;
}

export function getSessionId(): string | null {
	return sessionId;
}

export function stopStreaming() {
	if (abortController) {
		abortController.abort();
		abortController = null;
	}
	isStreaming = false;
	isTyping = false;
}

export function openChat() {
	view = 'window';
	saveState();
}

export function closeChat() {
	view = 'closed';
	if (abortController) {
		abortController.abort();
		abortController = null;
	}
	saveState();
}

export function expandChat() {
	view = 'expanded';
	saveState();
}

export function collapseChat() {
	view = 'window';
	saveState();
}

export function sendMessage(text: string) {
	const trimmed = text.trim();
	if (!trimmed) return;

	messages.push({
		id: generateId(),
		role: 'user',
		content: trimmed,
		timestamp: new Date()
	});
	inputText = '';
	saveState();
	streamResponse(trimmed);
}

export function retryLastMessage() {
	// Find the last user message
	const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
	if (!lastUserMsg || isTyping) return;

	// Remove the user message and everything after it — sendMessage will re-add it
	const lastUserIdx = messages.lastIndexOf(lastUserMsg);
	messages = messages.slice(0, lastUserIdx);

	// Re-send
	sendMessage(lastUserMsg.content);
}

export async function copyToClipboard(text: string): Promise<boolean> {
	try {
		await navigator.clipboard.writeText(text);
		return true;
	} catch {
		return false;
	}
}

export function setPageContext(context: { path: string; model?: string; title?: string }) {
	currentPageContext = context;
}

export async function confirmAction(messageId: string) {
	const msg = messages.find((m) => m.id === messageId);
	if (!msg?.pendingAction || msg.pendingAction.status !== 'pending') return;

	const action = msg.pendingAction;
	const selected = action.selectedIndices ?? new Set(action.items.map((_, i) => i));

	if (selected.size === 0) return; // Nothing selected

	// Filter to only selected items
	const selectedItems = action.items.filter((_, i) => selected.has(i));

	action.status = 'creating';
	action.results = [];
	messages = [...messages];

	if (action.action === 'attach') {
		// Attach flow: PATCH the parent object to add M2M relationships
		try {
			const itemIds = selectedItems.map((i) => i.id).filter(Boolean);
			const res = await fetch(`/fe-api/chat/attach-object`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					parent_url_slug: action.parentUrlSlug,
					parent_id: action.parentId,
					m2m_field: action.m2mField,
					item_ids: itemIds
				})
			});

			if (res.ok) {
				action.results = selectedItems.map((i) => ({ name: i.name, id: i.id }));
				action.status = 'created';
				const names = selectedItems.map((i) => i.name).join(', ');
				messages.push({
					id: generateId(),
					role: 'assistant',
					content: `Attached ${selectedItems.length} ${action.displayName}: ${names}.`,
					timestamp: new Date()
				});
				messages = [...messages];
				saveState();
				window.location.reload();
			} else {
				const err = await res.json().catch(() => ({ detail: res.statusText }));
				action.results = selectedItems.map((i) => ({
					name: i.name,
					error: err.detail || err.error || 'Attachment failed'
				}));
				action.status = 'error';
			}
		} catch {
			action.results = selectedItems.map((i) => ({
				name: i.name,
				error: 'Network error'
			}));
			action.status = 'error';
		}
		messages = [...messages];
	} else {
		// Create flow: POST each selected item individually
		for (const item of selectedItems) {
			try {
				const res = await fetch(`/fe-api/chat/create-object`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						url_slug: action.urlSlug,
						fields: item
					})
				});

				if (res.ok) {
					const data = await res.json();
					action.results!.push({ name: item.name, id: data.id });
				} else {
					const err = await res.json().catch(() => ({ detail: res.statusText }));
					action.results!.push({
						name: item.name,
						error: err.detail || err.error || 'Creation failed'
					});
				}
			} catch {
				action.results!.push({ name: item.name, error: 'Network error' });
			}
			messages = [...messages];
		}

		const allOk = action.results!.every((r) => !r.error);
		action.status = allOk ? 'created' : 'error';

		// Record the outcome so the chat history knows what was created
		if (allOk) {
			const names = action.results!.map((r) => r.name).join(', ');
			const folderInfo = action.folderName ? ` in domain "${action.folderName}"` : '';
			messages.push({
				id: generateId(),
				role: 'assistant',
				content: `Created ${action.results!.length} ${action.displayName}${folderInfo}: ${names}.`,
				timestamp: new Date()
			});
		}
		messages = [...messages];
		if (allOk) {
			saveState();
			// Navigate to the created object if it's a complex type (study, assessment)
			const navigableModels: Record<string, string> = {
				ebios_rm_study: '/ebios-rm/',
				risk_assessment: '/risk-assessments/',
				compliance_assessment: '/compliance-assessments/'
			};
			const basePath = action.modelKey ? navigableModels[action.modelKey] : undefined;
			if (basePath && action.results!.length === 1 && action.results![0].id) {
				const { goto } = await import('$lib/utils/breadcrumbs');
				goto(`${basePath}${action.results![0].id}`, { label: '', breadcrumbAction: 'push' });
			} else {
				window.location.reload();
			}
		}
	}
	saveState();
}

export function toggleItemSelection(messageId: string, index: number) {
	const msg = messages.find((m) => m.id === messageId);
	if (!msg?.pendingAction || msg.pendingAction.status !== 'pending') return;

	const selected = msg.pendingAction.selectedIndices ?? new Set<number>();
	if (selected.has(index)) {
		selected.delete(index);
	} else {
		selected.add(index);
	}
	msg.pendingAction.selectedIndices = new Set(selected);
	messages = [...messages];
}

export function toggleAllSelection(messageId: string) {
	const msg = messages.find((m) => m.id === messageId);
	if (!msg?.pendingAction || msg.pendingAction.status !== 'pending') return;

	const selected = msg.pendingAction.selectedIndices ?? new Set<number>();
	if (selected.size === msg.pendingAction.items.length) {
		// All selected → deselect all
		msg.pendingAction.selectedIndices = new Set<number>();
	} else {
		// Some or none selected → select all
		msg.pendingAction.selectedIndices = new Set(msg.pendingAction.items.map((_, i) => i));
	}
	messages = [...messages];
}

export function changeActionFolder(messageId: string, folderId: string, folderName: string) {
	const msg = messages.find((m) => m.id === messageId);
	if (!msg?.pendingAction || msg.pendingAction.status !== 'pending') return;
	msg.pendingAction.folderId = folderId;
	msg.pendingAction.folderName = folderName;
	// Update all items' folder field
	for (const item of msg.pendingAction.items) {
		item.folder = folderId;
	}
	messages = [...messages];
	saveState();
}

export function rejectAction(messageId: string) {
	const msg = messages.find((m) => m.id === messageId);
	if (!msg?.pendingAction || msg.pendingAction.status !== 'pending') return;

	msg.pendingAction.status = 'rejected';
	messages = [...messages];
	saveState();
}

export function selectChoice(messageId: string, itemId: string) {
	const msg = messages.find((m) => m.id === messageId);
	if (!msg?.pendingChoice || msg.pendingChoice.status !== 'pending') return;

	const item = msg.pendingChoice.items.find((i) => i.id === itemId);
	if (!item) return;

	// Mark the choice as selected
	msg.pendingChoice.status = 'selected';
	msg.pendingChoice.selectedId = itemId;
	messages = [...messages];
	saveState();

	// Send the selection as a user message so the workflow can pick it up
	sendMessage(item.name);
}

export function startNewSession() {
	// Abort any in-flight request
	if (abortController) {
		abortController.abort();
		abortController = null;
	}
	isTyping = false;

	// Clear backend session reference — next message creates a fresh session
	sessionId = null;

	// Reset messages to welcome state
	messages = [getWelcomeMessage()];
	saveState();
}

export function getSessionHistory() {
	return sessionHistory;
}

export function getLoadingHistory() {
	return loadingHistory;
}

export async function loadSessionHistory() {
	loadingHistory = true;
	try {
		const res = await fetch(`${CHAT_API}/sessions`);
		if (res.ok) {
			const data = await res.json();
			sessionHistory = (data.results ?? data)
				.map((s: any) => ({
					id: s.id,
					title: s.title || `Chat ${new Date(s.created_at).toLocaleDateString()}`,
					folder: s.folder?.str ?? '',
					message_count: s.message_count ?? 0,
					created_at: s.created_at
				}))
				.sort(
					(a: ChatSession, b: ChatSession) =>
						new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
				)
				.slice(0, 30);
		}
	} catch {
		// Ignore — sidebar just stays empty
	}
	loadingHistory = false;
}

export async function deleteSession(targetSessionId: string) {
	try {
		await fetch(`${CHAT_API}/sessions/${targetSessionId}`, { method: 'DELETE' });
	} catch {
		// Ignore
	}
	// Remove from local list
	sessionHistory = sessionHistory.filter((s) => s.id !== targetSessionId);
	// If we deleted the active session, start fresh
	if (sessionId === targetSessionId) {
		sessionId = null;
		messages = [getWelcomeMessage()];
		saveState();
	}
}

export async function switchToSession(targetSessionId: string) {
	if (abortController) {
		abortController.abort();
		abortController = null;
	}
	isTyping = false;
	isStreaming = false;

	try {
		const res = await fetch(`${CHAT_API}/sessions/${targetSessionId}`);
		if (!res.ok) return;
		const data = await res.json();
		const loadedMessages: ChatMessage[] = (data.messages ?? []).map((msg: any) => ({
			id: msg.id,
			role: msg.role as 'user' | 'assistant',
			content: msg.content,
			timestamp: new Date(msg.created_at),
			contextRefs: msg.context_refs
		}));
		messages = loadedMessages.length > 0 ? loadedMessages : [getWelcomeMessage()];
	} catch {
		messages = [getWelcomeMessage()];
	}

	sessionId = targetSessionId;
	saveState();
}
