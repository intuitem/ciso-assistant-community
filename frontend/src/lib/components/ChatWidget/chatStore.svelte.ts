import type { ChatMessage, ChatView, SuggestedAction } from './types';

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

function simulateResponse(userMessage: string) {
	isTyping = true;
	setTimeout(() => {
		isTyping = false;
		messages.push({
			id: generateId(),
			role: 'assistant',
			content: `Thank you for your question about "${userMessage.slice(0, 60)}${userMessage.length > 60 ? '...' : ''}". This is a placeholder response — backend integration is coming soon.`,
			timestamp: new Date()
		});
	}, 1200);
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
	simulateResponse(trimmed);
}
