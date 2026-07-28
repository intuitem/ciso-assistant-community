export type ChatView = 'closed' | 'window' | 'expanded';

export interface PendingAction {
	id: string;
	action: 'create' | 'attach' | 'import';
	modelKey?: string;
	urlSlug?: string;
	displayName: string;
	items: { id?: string; name: string; description?: string; folder?: string }[];
	status: 'pending' | 'creating' | 'created' | 'error' | 'rejected';
	selectedIndices?: Set<number>;
	results?: { name: string; id?: string; error?: string }[];
	// Folder targeting
	folderId?: string;
	folderName?: string;
	availableFolders?: { id: string; name: string }[];
	// Attach-specific fields
	parentModelKey?: string;
	parentId?: string;
	parentUrlSlug?: string;
	m2mField?: string;
	// Import-specific fields (dry-run counts)
	documentId?: string;
	targetName?: string;
	rowCount?: number;
	createdCount?: number;
	updatedCount?: number;
	skippedCount?: number;
	failedCount?: number;
}

export interface PendingChoice {
	id: string;
	field: string;
	label: string;
	items: { id: string; name: string; description?: string }[];
	status: 'pending' | 'selected' | 'done';
	selectedId?: string;
}

export interface ChatAttachment {
	id: string;
	filename: string;
}

export interface PendingAttachment {
	id: string;
	filename: string;
	status: 'uploading' | 'ready' | 'error';
	error?: string;
}

export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	thinking?: string;
	timestamp: Date;
	contextRefs?: ContextRef[];
	pendingAction?: PendingAction;
	pendingChoice?: PendingChoice;
	attachments?: ChatAttachment[];
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
