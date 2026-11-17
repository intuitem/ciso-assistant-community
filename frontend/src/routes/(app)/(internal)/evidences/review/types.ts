import { m } from '#paraglide/messages.js';
import { getLocale } from '#paraglide/runtime.js';

export type Related = { id: string; str: string };

export type ReviewStatus = 'pending' | 'approved' | 'rejected';

export type Evidence = {
	id: string;
	name: string;
	status: string;
	expiry_date: string | null;
	updated_at: string;
	folder: Related;
	owner: Related[];
	requirement_assessments: Related[];
	latest_revision: {
		id: string;
		version: number;
		review_status: ReviewStatus;
		created_at: string;
		uploaded_by: string | null;
	} | null;
};

type User = { id: string; email: string; first_name?: string; last_name?: string };

export type Revision = {
	id: string;
	version: number;
	attachment: string | null;
	attachment_hash: string | null;
	link: string | null;
	observation: string | null;
	created_at: string;
	size: string | null;
	uploaded_by: User | null;
	review_status: ReviewStatus;
	reviewed_by: User | null;
	reviewed_at: string | null;
	review_comment: string;
};

export type RequirementDetail = {
	id: string;
	name: string;
	description: string | null;
	result: string;
	compliance_assessment: Related;
	requirement: { typical_evidence: string | null; ref_id: string | null };
};

export const SCOPES = [
	{ key: 'pending', label: m.reviewToReview },
	{ key: 'approved', label: m.reviewScopeApproved },
	{ key: 'rejected', label: m.reviewScopeRejected },
	{ key: 'all', label: m.reviewScopeAll }
] as const;
export type Scope = (typeof SCOPES)[number]['key'];

export const PAGE_SIZE = 50;

export const userName = (u: User | null) =>
	u ? [u.first_name, u.last_name].filter(Boolean).join(' ') || u.email : '—';

export function daysFrom(date: string | Date): number {
	const d = typeof date === 'string' ? new Date(date) : date;
	return Math.round((d.getTime() - Date.now()) / 86_400_000);
}

export function relative(date: string): string {
	const days = daysFrom(date);
	const rtf = new Intl.RelativeTimeFormat(getLocale(), { numeric: 'auto', style: 'long' });
	if (days > -31) return rtf.format(Math.min(days, 0), 'day');
	if (days > -365) return rtf.format(Math.round(days / 30), 'month');
	return rtf.format(Math.round(days / 365), 'year');
}
