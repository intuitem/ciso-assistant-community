export interface MappingRow {
	/** Index in the library's mapping list; the only stable row identity. */
	index: number;
	source_urn: string;
	source_ref_id: string | null;
	source_name: string | null;
	target_urn: string;
	target_ref_id: string | null;
	target_name: string | null;
	relationship: string | null;
	rationale: string | null;
	strength_of_relationship: number | null;
	annotation: string | null;
}

export interface MappingRequirement {
	urn: string;
	ref_id: string | null;
	name: string | null;
	description: string | null;
}

export interface MappingMeta {
	display_name: string;
	source_framework: string;
	target_framework: string;
	source_coverage: number;
	target_coverage: number;
	source_total: number;
	source_linked: number;
	target_total: number;
	target_linked: number;
}

export interface MappingTableData {
	rows: MappingRow[];
	source_requirements: MappingRequirement[];
	target_requirements: MappingRequirement[];
	meta: MappingMeta;
}
