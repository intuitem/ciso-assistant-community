/** One weakest-link rule's result on an audit (the `weakest_links` field), as
 *  core/weakest_link.py computes it. */
export interface WeakestLinkResult {
	ref_id: string;
	/** Mean weight of the audit's assessed rated nodes, 0 to 1; null when none is assessed. */
	score: number | null;
	sections: WeakestLinkSection[];
}

export type WeakestLinkRating =
	'compliant' | 'partially_compliant' | 'non_compliant' | 'not_assessed' | 'not_applicable';

export interface WeakestLinkSection {
	/** The top-level requirement node; null when the whole audit is one section. */
	urn: string | null;
	ref_id: string | null;
	name: string | null;
	score: number | null;
	counts: Record<'compliant' | 'partially_compliant' | 'non_compliant' | 'not_assessed', number>;
	nodes: {
		urn: string;
		ref_id: string | null;
		name: string | null;
		rating: WeakestLinkRating;
		/** The requirements that set the rating. */
		drivers: {
			id: string;
			urn: string;
			ref_id: string | null;
			name: string | null;
			result: string | null;
		}[];
	}[];
}
