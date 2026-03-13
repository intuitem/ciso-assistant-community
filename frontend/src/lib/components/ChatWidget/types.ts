export type ChatView = 'closed' | 'window' | 'expanded';

export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	timestamp: Date;
	contextRefs?: ContextRef[];
}

export interface ContextRef {
	type: string;
	id?: string;
	name: string;
	ref_id?: string;
	score?: number;
	source?: string;
	url?: string;
}

export interface SuggestedAction {
	label: string;
	prompt: string;
	icon: string;
}

export interface ChatSession {
	id: string;
	title: string;
	folder: string;
	message_count: number;
	created_at: string;
}
