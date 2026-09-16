import { describe, expect, it } from 'vitest';
import {
	aggregateBySide,
	bestRelationship,
	compareValues,
	filterByCoverage,
	matchesQuery,
	relationshipRank
} from './aggregate';
import type { MappingRequirement, MappingRow } from './types';

function requirement(urn: string, ref_id: string | null, name: string | null): MappingRequirement {
	return { urn, ref_id, name, description: null };
}

function mapping(
	source: MappingRequirement,
	target: MappingRequirement,
	relationship: string | null
): MappingRow {
	return {
		source_urn: source.urn,
		source_ref_id: source.ref_id,
		source_name: source.name,
		target_urn: target.urn,
		target_ref_id: target.ref_id,
		target_name: target.name,
		relationship,
		rationale: 'semantic',
		strength_of_relationship: null,
		annotation: null
	};
}

const s1 = requirement('urn:src:a', 'A.1', 'Source one');
const s2 = requirement('urn:src:b', 'A.2', 'Source two');
const s3 = requirement('urn:src:c', 'A.3', 'Source three');
const t1 = requirement('urn:tgt:x', 'X.1', 'Target one');
const t2 = requirement('urn:tgt:y', 'X.2', 'Target two');
const t3 = requirement('urn:tgt:z', null, null);

const sources = [s1, s2, s3];
const targets = [t1, t2, t3];

// s1 -> t1, t2 ; s2 -> t1 ; s3 unmapped ; t3 unmapped
const rows = [mapping(s1, t1, 'intersect'), mapping(s1, t2, 'equal'), mapping(s2, t1, 'subset')];

describe('bestRelationship', () => {
	it('picks the strongest relationship of the group', () => {
		expect(bestRelationship(rows)).toBe('equal');
		expect(bestRelationship([mapping(s2, t1, 'subset')])).toBe('subset');
	});

	it('is null for an empty group', () => {
		expect(bestRelationship([])).toBeNull();
	});
});

describe('aggregateBySide', () => {
	it('groups every target under its source, keeping unmapped sources', () => {
		const result = aggregateBySide(sources, rows, 'source');

		expect(result).toHaveLength(3);
		expect(result.map((row) => row.urn)).toEqual([s1.urn, s2.urn, s3.urn]);
		expect(result[0].counterparts.map((c) => c.urn)).toEqual([t1.urn, t2.urn]);
		expect(result[0].relationship).toBe('equal');
		expect(result[1].counterparts).toHaveLength(1);
		expect(result[2].counterparts).toEqual([]);
		expect(result[2].relationship).toBeNull();
	});

	it('groups every source under its target, keeping unmapped targets', () => {
		const result = aggregateBySide(targets, rows, 'target');

		expect(result.map((row) => row.urn)).toEqual([t1.urn, t2.urn, t3.urn]);
		expect(result[0].counterparts.map((c) => c.ref_id)).toEqual([s1.ref_id, s2.ref_id]);
		expect(result[1].counterparts.map((c) => c.urn)).toEqual([s1.urn]);
		expect(result[2].counterparts).toEqual([]);
	});

	it('carries the per-link relationship on each counterpart', () => {
		const [first] = aggregateBySide(sources, rows, 'source');
		expect(first.counterparts.map((c) => c.relationship)).toEqual(['intersect', 'equal']);
	});

	it('preserves the requirement order it is given', () => {
		const reversed = aggregateBySide([...sources].reverse(), rows, 'source');
		expect(reversed.map((row) => row.urn)).toEqual([s3.urn, s2.urn, s1.urn]);
	});

	it('accounts for every link exactly once across a side', () => {
		const total = aggregateBySide(targets, rows, 'target').reduce(
			(sum, row) => sum + row.counterparts.length,
			0
		);
		expect(total).toBe(rows.length);
	});
});

describe('filterByCoverage', () => {
	const aggregated = aggregateBySide(sources, rows, 'source');

	it('keeps everything under "all"', () => {
		expect(filterByCoverage(aggregated, 'all')).toHaveLength(3);
	});

	it('keeps only groups with counterparts under "mapped"', () => {
		expect(filterByCoverage(aggregated, 'mapped').map((row) => row.urn)).toEqual([s1.urn, s2.urn]);
	});

	it('keeps only empty groups under "unmapped"', () => {
		expect(filterByCoverage(aggregated, 'unmapped').map((row) => row.urn)).toEqual([s3.urn]);
	});

	it('reports a source as unmapped once a relationship filter drops its only link', () => {
		const onlyEqual = rows.filter((row) => row.relationship === 'equal');
		const aggregatedEqual = aggregateBySide(sources, onlyEqual, 'source');
		expect(filterByCoverage(aggregatedEqual, 'unmapped').map((row) => row.urn)).toEqual([
			s2.urn,
			s3.urn
		]);
	});
});

describe('matchesQuery', () => {
	it('matches case-insensitively and ignores nullish values', () => {
		expect(matchesQuery(['A.1', null, undefined], 'a.1')).toBe(true);
		expect(matchesQuery([null, undefined], 'a')).toBe(false);
		expect(matchesQuery(['Source one'], 'one')).toBe(true);
	});
});

describe('relationshipRank', () => {
	it('ranks stronger relationships lower', () => {
		expect(relationshipRank('equal')).toBeLessThan(relationshipRank('intersect'));
		expect(relationshipRank('subset')).toBeLessThan(relationshipRank('not_related'));
	});

	it('sorts unknown and missing relationships last', () => {
		expect(relationshipRank(null)).toBeGreaterThan(relationshipRank('not_related'));
		expect(relationshipRank('bogus')).toBe(relationshipRank(null));
	});
});

describe('compareValues', () => {
	it('sorts ref_ids numerically rather than lexically', () => {
		expect(compareValues('A.2', 'A.10')).toBeLessThan(0);
	});

	it('sorts numbers numerically', () => {
		expect(compareValues(2, 10)).toBeLessThan(0);
	});

	it('pushes missing values to the end in either direction', () => {
		expect(compareValues(null, 'A.1')).toBeGreaterThan(0);
		expect(compareValues('A.1', null)).toBeLessThan(0);
		expect(compareValues(null, null)).toBe(0);
	});
});
