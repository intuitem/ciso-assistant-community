/** One staircase rule's result on an audit (the `staircases` field), as
 *  core/staircase.py computes it. */
export interface StaircaseResult {
	/** The rule. */
	ref_id: string;
	/** The lowest section level; null when one is not determined. */
	level: number | null;
	sections: StaircaseSection[];
}

export interface StaircaseSection {
	/** The top-level requirement node; null when the whole audit is one section. */
	urn: string | null;
	ref_id: string | null;
	name: string | null;
	/** Levels met in a row from the lowest; null when a lower level is missing from the audit. */
	level: number | null;
	/** In the rule's order: levels[n - 1] is level n. */
	levels: StaircaseLevel[];
	/** What keeps the section from its next level. */
	blocking: {
		/** The requirement assessment. */
		id: string | null;
		urn: string;
		ref_id: string | null;
		name: string | null;
		result: string | null;
	}[];
}

export interface StaircaseLevel {
	implementation_group: string;
	status: 'met' | 'not_met' | 'pending' | 'out_of_scope';
	/** Null when the audit does not include that level. */
	passing: number | null;
	total: number | null;
}
