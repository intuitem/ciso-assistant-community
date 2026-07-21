import { m } from '$paraglide/messages';

// Single source of truth for document-type presentation (label + icon), shared
// by the catalog, the reader, and any other document-facing surface.
export const DOCUMENT_TYPES: { key: string; label: () => string; icon: string }[] = [
	{ key: 'policy', label: m.policy, icon: 'fa-shield-halved' },
	{ key: 'procedure', label: m.procedure, icon: 'fa-list-check' },
	{ key: 'charter', label: m.charter, icon: 'fa-scroll' },
	{ key: 'record', label: m.record, icon: 'fa-box-archive' },
	{ key: 'meeting_minutes', label: m.meetingMinutes, icon: 'fa-users' },
	{ key: 'other', label: m.other, icon: 'fa-file-lines' }
];

const META: Record<string, { label: () => string; icon: string }> = Object.fromEntries(
	DOCUMENT_TYPES.map((t) => [t.key, t])
);

export const documentTypeLabel = (t: string): string => META[t]?.label() ?? t;
export const documentTypeIcon = (t: string): string => META[t]?.icon ?? 'fa-file-lines';
