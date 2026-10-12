/** A node of a ring tree. Values are percentages (0..100), null when not measurable. */
export interface RingNode {
	id: string;
	label: string;
	sublabel?: string;
	/** Dimmed, italic label (e.g. a domain the viewer cannot see). */
	muted?: boolean;
	/** Inner ring; undefined when the node has no value of its own. */
	own?: number | null;
	/** Replaces the own value's text (e.g. "N/A"). */
	ownLabel?: string;
	/** Inner ring drawn as consecutive slices (fractions of the ring) instead of one arc. */
	ownSegments?: { fraction: number; color: string }[];
	/** Own value rests on too little data: faded with a dashed track. */
	faint?: boolean;
	/** Short caveat shown after the sublabel (e.g. "low coverage"). */
	warning?: string;
	/** Longer explanation of the caveat, for tooltips. */
	warningDetail?: string;
	/** Outer ring. */
	branch: number | null;
	/** False when the branch is just the node's own value (nothing else below): no outer ring. */
	showBranch?: boolean;
	/** Nothing measured anywhere below: dashed outer ring. */
	empty?: boolean;
	badge?: string;
	/** Number of nodes under this one, shown when it is collapsed. */
	hiddenCount?: number;
	children: RingNode[];
}

export type RingColor = (value: number | null) => string;
