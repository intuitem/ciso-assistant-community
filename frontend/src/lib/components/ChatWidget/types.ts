export type ChatView = 'closed' | 'window' | 'expanded';

export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	timestamp: Date;
}

export interface SuggestedAction {
	label: string;
	prompt: string;
	icon: string;
}
