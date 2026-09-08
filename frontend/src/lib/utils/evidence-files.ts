export interface EvidenceAttachment {
	id: string;
	revision_id: string;
	filename: string;
	size: string | null;
	attachment_hash: string | null;
}

/** Preserve metadata types while sending the file set in one request. */
export function evidenceMultipart(data: Record<string, unknown>, files: File[]): FormData {
	const body = new FormData();
	body.set('payload', JSON.stringify(data));
	for (const file of files) body.append('attachments', file);
	return body;
}
