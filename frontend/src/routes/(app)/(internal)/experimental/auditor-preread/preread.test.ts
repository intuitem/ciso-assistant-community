import { describe, expect, it } from 'vitest';
import { interviewPlan, requestList, requestListTsv, type PrereadItem } from './preread';

const item = (ref: string, readiness: PrereadItem['readiness'], who: string[]): PrereadItem => ({
	id: ref,
	urn_suffix: ref.toLowerCase(),
	ref_id: ref,
	name: `Req ${ref}`,
	result: 'compliant',
	status: 'done',
	guidance: {
		questions: [{ stage: 2, text: 'q' }],
		requests: [{ label: `Rec\t${ref}`, kind: 'record', fresh_days: 365 }],
		sampling: null,
		interviewees: who,
		pitfalls: []
	},
	evidences: [],
	applied_controls: [],
	findings: [],
	readiness,
	reasons: []
});

describe('auditor pre-read lists', () => {
	const items = [
		item('A.1', 'ready', ['hr']),
		item('A.2', 'gap', ['hr', 'ciso']),
		item('A.3', 'excluded', ['hr'])
	];

	it('orders requests worst first and drops excluded requirements', () => {
		expect(requestList(items).map((r) => r.item.ref_id)).toEqual(['A.2', 'A.1']);
	});

	it('groups by interviewee, busiest first', () => {
		expect(interviewPlan(items).map(([who, rs]) => [who, rs.length])).toEqual([
			['hr', 2],
			['ciso', 1]
		]);
	});

	it('escapes tabs in the TSV export', () => {
		const lines = requestListTsv(requestList(items)).split('\n');
		expect(lines).toHaveLength(3);
		expect(lines[1].split('\t')).toHaveLength(7);
	});
});

describe('isStale', () => {
	const g = {
		questions: [],
		requests: [{ label: 'r', kind: 'record', fresh_days: 30 }],
		sampling: null,
		interviewees: [],
		pitfalls: []
	};
	const now = Date.parse('2026-11-15T00:00:00Z');
	it('flags evidence older than the widest window', async () => {
		const { isStale } = await import('./preread');
		expect(isStale('2026-09-01T00:00:00Z', g, now)).toBe(true);
		expect(isStale('2026-11-01T00:00:00Z', g, now)).toBe(false);
		expect(isStale('2020-01-01T00:00:00Z', { ...g, requests: [] }, now)).toBe(false);
	});
});
