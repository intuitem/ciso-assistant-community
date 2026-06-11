// Shared types for the experimental BatchUpload widget set.
// Designed to be reused by future ingest flows (e.g. RAG framework indexing).

export const CONFLICT_STRATEGIES = ['skip', 'add_revision', 'replace', 'rename'] as const;
export type ConflictStrategy = (typeof CONFLICT_STRATEGIES)[number];

export type FileEntryStatus = 'pending' | 'uploading' | 'done' | 'error';

export interface FileEntry {
	id: string;
	field: string; // multipart field name, e.g. "file_0"
	file: File;
	name: string; // user-visible name (defaults to file.name)
	relPath: string; // webkitRelativePath when picking a directory, otherwise ""
	size: number;
	status: FileEntryStatus;
	outcome?: BatchOutcome;
	message?: string;
	evidenceId?: string;
	revisionId?: string;
	version?: number;
	renamedTo?: string;
}

export type BatchOutcome =
	| 'created'
	| 'revision_added'
	| 'replaced'
	| 'renamed'
	| 'skipped'
	| 'duplicate'
	| 'error';

export interface BatchSummary {
	total: number;
	created: number;
	revision_added: number;
	replaced: number;
	renamed: number;
	skipped: number;
	duplicate: number;
	errors: number;
}

export interface BatchResultRow {
	field: string;
	name: string;
	rel_path: string | null;
	outcome: BatchOutcome;
	error?: string;
	evidence_id?: string;
	evidence_name?: string;
	revision_id?: string;
	version?: number;
	renamed_from?: string;
	renamed_to?: string;
}

export interface BatchResponse {
	summary: BatchSummary;
	results: BatchResultRow[];
}
