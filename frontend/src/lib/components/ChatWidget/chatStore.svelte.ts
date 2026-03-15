import type { ChatMessage, ChatView, PendingAction, SuggestedAction } from './types';
import { browser } from '$app/environment';

const CHAT_API = '/fe-api/chat';
const STORAGE_KEY = 'ciso-chat-state';

const WELCOME_MESSAGE: ChatMessage = {
	id: 'welcome',
	role: 'assistant',
	content:
		"Hello! I'm your CISO Assistant. I can help you search for controls, navigate frameworks, explain risk scenarios, and more. How can I help you today?",
	timestamp: new Date()
};

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
		// Restore Date objects from ISO strings
		if (Array.isArray(data.messages)) {
			data.messages = data.messages.map((m: ChatMessage) => ({
				...m,
				timestamp: new Date(m.timestamp)
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
		const data: PersistedState = { messages, sessionId, view };
		sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
	} catch {
		// Storage full or unavailable — ignore
	}
}

const restored = loadPersistedState();

// Current page context — updated by ChatWidget via setPageContext()
let currentPageContext = $state<{ path: string; model?: string; title?: string } | null>(null);

let view = $state<ChatView>(restored?.view ?? 'closed');
let messages = $state<ChatMessage[]>(restored?.messages ?? [WELCOME_MESSAGE]);
let inputText = $state('');
let isTyping = $state(false);
let sessionId = $state<string | null>(restored?.sessionId ?? null);
let abortController = $state<AbortController | null>(null);

export const suggestedActions: SuggestedAction[] = [
	{
		label: 'Overdue controls',
		prompt: 'Show me the controls that have missed their ETA',
		icon: 'fa-solid fa-clock'
	},
	{
		label: 'Risk overview',
		prompt: 'Give me a summary of my risk scenarios',
		icon: 'fa-solid fa-shield-halved'
	},
	{
		label: 'Controls without evidence',
		prompt: 'List the controls that have no evidence attached',
		icon: 'fa-solid fa-triangle-exclamation'
	},
	{
		label: 'My domains',
		prompt: 'What are the domains I have access to?',
		icon: 'fa-solid fa-folder-tree'
	}
];

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
			throw new Error(`Chat request failed: ${response.statusText}`);
		}

		// Create the assistant message placeholder for streaming
		const assistantMessageId = generateId();
		messages.push({
			id: assistantMessageId,
			role: 'assistant',
			content: '',
			timestamp: new Date()
		});
		isTyping = false;

		// Read SSE stream
		const reader = response.body?.getReader();
		const decoder = new TextDecoder();

		if (!reader) {
			throw new Error('No response body');
		}

		let buffer = '';

		while (true) {
			const { done, value } = await reader.read();
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
							messages = [...messages];
						}
					} else if (data.type === 'thinking') {
						const msg = messages.find((m) => m.id === assistantMessageId);
						if (msg) {
							msg.thinking = (msg.thinking || '') + data.content;
							messages = [...messages];
						}
					} else if (data.type === 'pending_action') {
						const msg = messages.find((m) => m.id === assistantMessageId);
						if (msg) {
							if (data.action === 'attach') {
								msg.pendingAction = {
									id: generateId(),
									action: 'attach',
									displayName: data.related_display,
									items: data.items,
									status: 'pending',
									parentModelKey: data.parent_model_key,
									parentId: data.parent_id,
									parentUrlSlug: data.parent_url_slug,
									m2mField: data.m2m_field
								};
							} else {
								msg.pendingAction = {
									id: generateId(),
									action: data.action,
									modelKey: data.model_key,
									urlSlug: data.url_slug,
									displayName: data.display_name,
									items: data.items,
									status: 'pending'
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
		saveState();
	} catch (error) {
		isTyping = false;
		if (error instanceof DOMException && error.name === 'AbortError') {
			return;
		}

		messages.push({
			id: generateId(),
			role: 'assistant',
			content:
				'Sorry, I could not connect to the chat service. Please check that the LLM service is configured and running.',
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

	// Remove the last assistant response (if it exists after the last user message)
	const lastUserIdx = messages.lastIndexOf(lastUserMsg);
	if (lastUserIdx < messages.length - 1) {
		// Remove everything after the last user message
		messages = messages.slice(0, lastUserIdx);
	} else {
		// Remove the user message itself — it will be re-added by sendMessage
		messages = messages.slice(0, lastUserIdx);
	}

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
	action.status = 'creating';
	action.results = [];
	messages = [...messages];

	if (action.action === 'attach') {
		// Attach flow: PATCH the parent object to add M2M relationships
		try {
			const itemIds = action.items.map((i) => i.id).filter(Boolean);
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
				action.results = action.items.map((i) => ({ name: i.name, id: i.id }));
				action.status = 'created';
			} else {
				const err = await res.json().catch(() => ({ detail: res.statusText }));
				action.results = action.items.map((i) => ({
					name: i.name,
					error: err.detail || err.error || 'Attachment failed'
				}));
				action.status = 'error';
			}
		} catch {
			action.results = action.items.map((i) => ({
				name: i.name,
				error: 'Network error'
			}));
			action.status = 'error';
		}
		messages = [...messages];
	} else {
		// Create flow: POST each item individually
		for (const item of action.items) {
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
		messages = [...messages];
	}
	saveState();
}

export function rejectAction(messageId: string) {
	const msg = messages.find((m) => m.id === messageId);
	if (!msg?.pendingAction || msg.pendingAction.status !== 'pending') return;

	msg.pendingAction.status = 'rejected';
	messages = [...messages];
	saveState();
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
	messages = [WELCOME_MESSAGE];
	saveState();
}
