/**
 * Domain tree feed: the contract between the backend and the domain tree view.
 *
 * Server-side rules (already applied when the feed arrives):
 * - one framework, optionally narrowed to one campaign;
 * - at most one audit per domain, deprecated ones excluded: a started audit
 *   wins over a planned one, then the most recently updated wins;
 * - only domains and the root (no enclaves, no personal folders);
 * - only audits the user can view; non-viewable domains are sent only when they
 *   sit on the path to a viewable one, with `viewable: false` and no audit;
 * - own results only, never inherited ones;
 * - audits whose results the viewer may not see (respondents) are sent with
 *   `results_hidden: true` and no counts;
 * - each audit counts only the requirements of its selected implementation groups.
 *
 * Client-side: implementation group, section, metric, aggregation, collapsing.
 *
 * Results are pre-summed per (audit, section, IG signature) so the payload stays
 * proportional to audits × sections × signatures, whatever the framework's size.
 */

export interface DomainTreeFeed {
	framework: {
		id: string;
		name: string;
		implementation_groups: { ref_id: string; name: string }[];
	};
	/** Top-level requirement nodes of the framework. */
	sections: { id: string; ref_id: string; name: string }[];
	/** Distinct sets of IGs a requirement belongs to; [] when the framework has none. */
	signatures: string[][];
	/** Assessable requirement count per section and signature: [section, signature, count]. */
	scope: [number, number, number][];
	folders: { id: string; name: string; parent_id: string | null; viewable: boolean }[];
	audits: {
		id: string;
		name: string;
		folder_id: string;
		status: string | null;
		updated_at: string;
		selected_implementation_groups: string[];
		results_hidden: boolean;
		/** The audit page's score gauge as 0..100; null when not scored or not visible. */
		score: number | null;
		/** The audit page's progress figure (whole audit); null when results are hidden. */
		progress: number | null;
	}[];
	/** See COUNT for the tuple layout. */
	counts: CountTuple[];
}

export type CountTuple = [
	audit: number,
	section: number,
	signature: number,
	compliant: number,
	partial: number,
	nonCompliant: number,
	notApplicable: number,
	notAssessed: number,
	/** Weighted sum of scores rebased to 0..1 on each requirement's scale. */
	scoreSum: number,
	/** Sum of the weights behind scoreSum. */
	scored: number
];

export const COUNT = {
	audit: 0,
	section: 1,
	signature: 2,
	compliant: 3,
	partial: 4,
	nonCompliant: 5,
	notApplicable: 6,
	notAssessed: 7,
	scoreSum: 8,
	scored: 9
} as const;
