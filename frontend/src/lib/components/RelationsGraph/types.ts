/** Payload returned by /{model}/{id}/neighborhood. */
export interface GraphNode {
	id: string;
	urlModel: string;
	name: string;
	ref?: string;
	group?: string;
	expandable?: boolean;
	model?: string;
	navigable?: boolean;
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
	/** group key -> total, which may exceed what was fetched. */
	totals: Record<string, number>;
}
