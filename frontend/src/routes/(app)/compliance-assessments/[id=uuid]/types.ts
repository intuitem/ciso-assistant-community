export interface Node {
	name: string;
	description?: string;
	urn: string;
	parent_urn?: string;
	node_content: string;
	assessable: boolean;
	style: string;
	children?: Record<string, Node>;
	status?: string; // Assuming that the status field exists in nodes similar to leaves
}
