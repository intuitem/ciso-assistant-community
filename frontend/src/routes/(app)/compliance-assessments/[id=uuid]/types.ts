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
	score?: number; // Assuming that the score field exists in nodes similar to leaves
	is_scored?: boolean; // Assuming that the is_scored field exists in nodes similar to leaves
}
