import type { MappingRequirement, MappingRow } from './types';

export type MappingViewMode = 'one_to_one' | 'per_source' | 'per_target';
export type CoverageFilter = 'all' | 'mapped' | 'unmapped';

/** Strongest first: drives the group badge and the relationship sort. */
export const RELATIONSHIP_ORDER = ['equal', 'superset', 'subset', 'intersect', 'not_related'];

export interface Counterpart {
	/** The originating row's index; distinguishes repeated links. */
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
	/** Strongest relationship in the group; null when unmapped. */
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

/** Group mappings under every assessable requirement of one side, unmapped ones included. */
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

/** Case-insensitive substring match; normalizes `query` itself. */
export function matchesQuery(values: (string | null | undefined)[], query: string): boolean {
	const needle = query.toLowerCase();
	return values.some((value) => value && value.toLowerCase().includes(needle));
}

/** Frontend counterpart of the backend's `escape_excel_formula`. */
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
