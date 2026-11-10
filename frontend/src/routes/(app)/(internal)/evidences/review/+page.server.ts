import { BASE_API_URL } from '#lib/utils/constants.js';
import { getSecureRedirect } from '#lib/utils/helpers.js';
import type { PageServerLoad } from './$types';
import { PAGE_SIZE, SCOPES, type Scope } from './types';

// Page-only params; everything else is an evidence filter passed through to the API.
const UI_PARAMS = ['scope', 'backUrl', 'backLabel', 'limit', 'offset', 'ordering'];

export const load: PageServerLoad = async ({ fetch, url }) => {
	const raw = url.searchParams.get('scope');
	const scope: Scope = SCOPES.some((s) => s.key === raw) ? (raw as Scope) : 'pending';

	const filters = new URLSearchParams();
	for (const [key, value] of url.searchParams) {
		if (!UI_PARAMS.includes(key)) filters.append(key, value);
	}

	const query = (s: Scope, extra: Record<string, string>) => {
		const q = new URLSearchParams(filters);
		// "All" still means "has something to review": a definition with no file is not reviewable.
		q.delete('review_status');
		for (const v of s === 'all' ? ['pending', 'approved', 'rejected'] : [s])
			q.append('review_status', v);
		for (const [k, v] of Object.entries(extra)) q.set(k, v);
		return `${BASE_API_URL}/evidences/?${q}`;
	};
	const get = (u: string) =>
		fetch(u)
			.then((r) => (r.ok ? r.json() : { count: 0, results: [] }))
			.catch(() => ({ count: 0, results: [] }));

	// Oldest first while reviewing (first in, first out); newest first when browsing decisions.
	const ordering =
		url.searchParams.get('ordering') ?? (scope === 'pending' ? 'updated_at' : '-updated_at');
	const [page, ...counts] = await Promise.all([
		get(query(scope, { limit: String(PAGE_SIZE), offset: '0', ordering })),
		...SCOPES.map((s) => get(query(s.key, { limit: '1' })))
	]);

	const listQuery = new URL(query(scope, { ordering })).searchParams.toString();
	const searchParams = new URLSearchParams(filters);
	searchParams.delete('search');

	// Opened from an audit: its evidences, direct and through requirements, controls and tasks.
	const auditId = filters.get('compliance_assessment');
	searchParams.delete('compliance_assessment');
	const audit = auditId
		? await fetch(`${BASE_API_URL}/compliance-assessments/${encodeURIComponent(auditId)}/`)
				.then((r) => (r.ok ? r.json() : undefined))
				.catch(() => undefined)
		: undefined;
	const auditHref = audit ? `/compliance-assessments/${audit.id}` : undefined;

	return {
		evidences: page.results ?? [],
		count: page.count ?? 0,
		counts: Object.fromEntries(SCOPES.map((s, i) => [s.key, counts[i].count ?? 0])),
		listQuery,
		scope,
		search: filters.get('search') ?? '',
		hasFilters: searchParams.size > 0,
		audit: audit ? { name: audit.name as string, href: auditHref } : undefined,
		backUrl: getSecureRedirect(url.searchParams.get('backUrl')) || auditHref || '/evidences',
		backLabel: url.searchParams.get('backLabel'),
		title: 'evidenceReview'
	};
};
