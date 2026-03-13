import type { ChatMessage, ChatView, SuggestedAction } from './types';

const CHAT_API = '/fe-api/chat';

let view = $state<ChatView>('closed');
let messages = $state<ChatMessage[]>([
	{
		id: 'welcome',
		role: 'assistant',
		content:
			"Hello! I'm your CISO Assistant. I can help you search for controls, navigate frameworks, explain risk scenarios, and more. How can I help you today?",
		timestamp: new Date()
	}
]);
let inputText = $state('');
let isTyping = $state(false);
let sessionId = $state<string | null>(null);
let abortController = $state<AbortController | null>(null);

export const suggestedActions: SuggestedAction[] = [
	{
		label: 'Search controls',
		prompt: 'Help me find controls related to access management',
		icon: 'fa-solid fa-magnifying-glass'
	},
	{
		label: 'Explain a framework',
		prompt: 'Explain the ISO 27001 framework and its key requirements',
		icon: 'fa-solid fa-book'
	},
	{
		label: 'Risk assessment help',
		prompt: 'Guide me through creating a risk assessment',
		icon: 'fa-solid fa-shield-halved'
	},
	{
		label: 'Compliance status',
		prompt: 'Show me an overview of my compliance status',
		icon: 'fa-solid fa-chart-pie'
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
			body: JSON.stringify({ content: userMessage }),
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
}

export function closeChat() {
	view = 'closed';
	if (abortController) {
		abortController.abort();
		abortController = null;
	}
}

export function expandChat() {
	view = 'expanded';
}

export function collapseChat() {
	view = 'window';
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
	streamResponse(trimmed);
}

export function startNewSession() {
	sessionId = null;
	messages = [
		{
			id: 'welcome',
			role: 'assistant',
			content:
				"Hello! I'm your CISO Assistant. I can help you search for controls, navigate frameworks, explain risk scenarios, and more. How can I help you today?",
			timestamp: new Date()
		}
	];
}
