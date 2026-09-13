/** Shape returned by /{model}/{id}/neighborhood — mirrors what a future backend
 *  `neighborhood` action would return, so swapping the source is a URL change. */
export interface GraphNode {
	id: string;
	urlModel: string;
	name: string;
	/** Short code used as the on-graph label; names never fit. */
	ref?: string;
	/** `${verb}|${urlModel}`, the unit the fan-out cap applies to. */
	group?: string;
	meta?: Record<string, string>;
}

export interface GraphLink {
	source: string;
	target: string;
	verb: string;
}

export interface Neighborhood {
	root: GraphNode;
	nodes: GraphNode[];
	links: GraphLink[];
	/** group key -> how many exist in total, which may exceed what was fetched. */
	totals: Record<string, number>;
}
