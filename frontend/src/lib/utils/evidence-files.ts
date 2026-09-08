export interface EvidenceAttachment {
	id: string;
	revision_id: string;
	filename: string;
	size: string | null;
	attachment_hash: string | null;
}

export interface EvidenceFileDisplay {
	filename: string;
	size: string | null;
}

/** Normalize legacy single-file and current multi-file API values for table cells. */
export function evidenceFileDisplay(value: unknown): EvidenceFileDisplay[] {
	if (typeof value === 'string' && value) return [{ filename: value, size: null }];
	if (!Array.isArray(value)) return [];
	return value.flatMap((item) => {
		if (!item || typeof item !== 'object') return [];
		const { filename, size } = item as { filename?: unknown; size?: unknown };
		if (typeof filename !== 'string' || !filename) return [];
		return [{ filename, size: typeof size === 'string' ? size : null }];
	});
}

/** Preserve metadata types while sending the file set in one request. */
export function evidenceMultipart(data: Record<string, unknown>, files: File[]): FormData {
	const body = new FormData();
	body.set('payload', JSON.stringify(data));
	for (const file of files) body.append('attachments', file);
	return body;
}
