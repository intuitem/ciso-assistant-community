import { describe, expect, it } from 'vitest';
import {
	interviewPlan,
	requestList,
	requestListTsv,
	sessionPlan,
	type PrereadItem
} from './preread';

const item = (ref: string, readiness: PrereadItem['readiness'], who: string[]): PrereadItem => ({
	id: ref,
	urn_suffix: ref.toLowerCase(),
	ref_id: ref,
	name: `Req ${ref}`,
	result: 'compliant',
	status: 'done',
	guidance: {
		questions: [{ id: 'q1', stage: 2, text: 'q' }],
		requests: [{ id: 'r1', label: `Rec\t${ref}`, kind: 'record', fresh_days: 400 }],
		sampling: [],
		interviewees: who,
		pitfalls: []
	},
	evidences: [],
	applied_controls: [],
	findings: [],
	prior_findings: [],
	filed: {},
	guide_key: null,
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
		expect(requestList(items).map((r) => r.items[0].ref_id)).toEqual(['A.2', 'A.1']);
	});

	it('groups by interviewee, busiest first', () => {
		expect(interviewPlan(items).map(([who, rs]) => [who, rs.length])).toEqual([
			['hr', 2],
			['ciso', 1]
		]);
	});

	it('merges requests sharing a reference control and keeps the tightest window', () => {
		const shared = (ref: string, days: number, filed: PrereadItem['filed']) => {
			const i = item(ref, 'weak', []);
			i.guidance!.requests = [
				{ id: 'r9', label: 'Minutes', kind: 'record', fresh_days: days, reference_control: 'u' }
			];
			i.filed = filed;
			return i;
		};
		const ev = { id: 'e1', name: 'Review', updated_at: null, here: true, manual: false };
		const rows = requestList([shared('9.3', 400, { r9: [ev] }), shared('5.1', 200, { r9: [ev] })]);
		expect(rows).toHaveLength(1);
		expect(rows[0].items.map((i) => i.ref_id)).toEqual(['9.3', '5.1']);
		expect(rows[0].fresh_days).toBe(200);
		expect(rows[0].filed).toEqual([ev]);
		const twice = shared('6.1.3', 400, { r9: [ev] });
		twice.guidance!.requests.push({ ...twice.guidance!.requests[0], id: 'r10' });
		expect(requestList([twice])[0].items).toHaveLength(1);
		expect(requestList(items).every((r) => r.filed === null)).toBe(true);
	});

	it('keeps session order, drops empty sessions, merges interviewees', () => {
		const plan = sessionPlan(items, [
			{
				id: 'open',
				label: 'Opening',
				members: [],
				requests: [{ id: 'r1', label: 'x', kind: 'document' }]
			},
			{ id: 'none', label: 'Empty', members: ['a.9'] },
			{ id: 'b', label: 'B', members: ['a.2', 'a.1'] }
		]);
		expect(plan.map((s) => s.session.id)).toEqual(['open', 'b']);
		expect(plan[1].reqs.map((r) => r.ref_id)).toEqual(['A.2', 'A.1']);
		expect(plan[1].people).toEqual(['hr', 'ciso']);
	});

	it('groups several requirements of a projected framework under one entry', () => {
		const a = { ...item('4.2 a)', 'gap', []), guide_key: '4.2' };
		const b = { ...item('4.2 b)', 'weak', []), id: 'x', guide_key: '4.2' };
		const plan = sessionPlan([a, b], [{ id: 'ctx', label: 'Context', members: ['4.2'] }]);
		expect(plan[0].reqs.map((r) => r.ref_id)).toEqual(['4.2 a)', '4.2 b)']);
	});

	it('shows a hand-paired request as filed even without a reference control', () => {
		const i = item('A.9', 'weak', []);
		i.filed = { r1: [{ id: 'e', name: 'Export', updated_at: null, here: true, manual: true }] };
		expect(requestList([i])[0].filed).toHaveLength(1);
	});

	it('escapes tabs in the TSV export', () => {
		const lines = requestListTsv(requestList(items)).split('\n');
		expect(lines).toHaveLength(3);
		expect(lines[1].split('\t')).toHaveLength(8);
	});
});

describe('isStale', () => {
	const g = {
		questions: [],
		requests: [{ id: 'r1', label: 'r', kind: 'record', fresh_days: 40 }],
		sampling: [],
		interviewees: [],
		pitfalls: []
	};
	const now = Date.parse('2026-11-15T00:00:00Z');
	it('flags unpaired evidence older than the tightest unpairable window', async () => {
		const { isStale } = await import('./preread');
		expect(isStale('2026-09-01T00:00:00Z', g, now)).toBe(true);
		expect(isStale('2026-11-01T00:00:00Z', g, now)).toBe(false);
		expect(isStale('2020-01-01T00:00:00Z', { ...g, requests: [] }, now)).toBe(false);
		const paired = [{ ...g.requests[0], reference_control: 'u' }];
		expect(isStale('2020-01-01T00:00:00Z', { ...g, requests: paired }, now)).toBe(false);
	});
});
