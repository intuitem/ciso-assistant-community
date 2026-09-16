import type { MappingRequirement, MappingRow } from './types';

export type MappingViewMode = 'one_to_one' | 'per_source' | 'per_target';
export type CoverageFilter = 'all' | 'mapped' | 'unmapped';

/**
 * Strongest first. A group's summary badge is its best link rather than an
 * arbitrary one, and sorting on the relationship column follows this order
 * instead of the alphabet.
 */
export const RELATIONSHIP_ORDER = ['equal', 'superset', 'subset', 'intersect', 'not_related'];

export interface Counterpart {
	/** The originating row's occurrence index — distinguishes repeated links. */
	index: number;
	urn: string;
	ref_id: string | null;
	name: string | null;
	relationship: string | null;
}

export interface AggregateRow {
	urn: string;
	ref_id: string | null;
	name: string | null;
	/** The strongest relationship among this group's links, null when unmapped. */
	relationship: string | null;
	counterparts: Counterpart[];
}

export function bestRelationship(rows: MappingRow[]): string | null {
	return (
		RELATIONSHIP_ORDER.find((relationship) =>
			rows.some((row) => row.relationship === relationship)
		) ?? null
	);
}

/**
 * Group mappings under every assessable requirement of one side.
 *
 * Requirements with no mapping are kept: they are the coverage gaps the
 * aggregate views exist to surface.
 */
export function aggregateBySide(
	requirements: MappingRequirement[],
	rows: MappingRow[],
	side: 'source' | 'target'
): AggregateRow[] {
	const grouped = new Map<string, MappingRow[]>();
	for (const row of rows) {
		const key = side === 'source' ? row.source_urn : row.target_urn;
		const bucket = grouped.get(key);
		if (bucket) bucket.push(row);
		else grouped.set(key, [row]);
	}

	return requirements.map((requirement) => {
		const groupRows = grouped.get(requirement.urn) ?? [];
		return {
			urn: requirement.urn,
			ref_id: requirement.ref_id,
			name: requirement.name,
			relationship: bestRelationship(groupRows),
			counterparts: groupRows.map((row) => ({
				index: row.index,
				urn: side === 'source' ? row.target_urn : row.source_urn,
				ref_id: side === 'source' ? row.target_ref_id : row.source_ref_id,
				name: side === 'source' ? row.target_name : row.source_name,
				relationship: row.relationship
			}))
		};
	});
}

export function filterByCoverage(rows: AggregateRow[], coverage: CoverageFilter): AggregateRow[] {
	if (coverage === 'mapped') return rows.filter((row) => row.counterparts.length > 0);
	if (coverage === 'unmapped') return rows.filter((row) => row.counterparts.length === 0);
	return rows;
}

/** Case-insensitive substring match; `query` need not be normalized by the caller. */
export function matchesQuery(values: (string | null | undefined)[], query: string): boolean {
	const needle = query.toLowerCase();
	return values.some((value) => value && value.toLowerCase().includes(needle));
}

/**
 * Neutralize spreadsheet formula injection, mirroring the backend's
 * `escape_excel_formula`: a value whose first non-blank character is =, +, - or @
 * is executed on open by Excel and Sheets unless it is quoted out.
 */
export function escapeSpreadsheetFormula(value: string): string {
	return /^\s*[=+\-@]/.test(value) ? `'${value}` : value;
}

export function compareValues(a: string | number | null, b: string | number | null): number {
	if (a == null && b == null) return 0;
	if (a == null) return 1;
	if (b == null) return -1;
	if (typeof a === 'number' && typeof b === 'number') return a - b;
	return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
}

export function relationshipRank(relationship: string | null): number {
	const index = RELATIONSHIP_ORDER.indexOf(relationship ?? '');
	return index === -1 ? RELATIONSHIP_ORDER.length : index;
}
