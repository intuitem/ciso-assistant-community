import type { Component } from 'svelte';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type NodeComponent = Component<any>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type NodeProps = Record<string, any>;

export interface TreeViewNode {
	/** Nodes Unique ID */
	id: string;
	/** Main content. accepts HTML or svelte component. */
	content: string | NodeComponent;
	/** Main content props. only used when the Content is a svelte component. */
	contentProps?: NodeProps;
	/** Lead content. accepts HTML or svelte component. */
	lead?: string | NodeComponent;
	/** lead props. only used when the Lead is a svelte component. */
	leadProps?: NodeProps;
	/** children nodes. */
	children?: TreeViewNode[];
	/** Set the input's value. */
	value?: unknown;
}
