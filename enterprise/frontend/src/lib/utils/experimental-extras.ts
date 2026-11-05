export interface ExperimentalEntry {
	title: string;
	desc: string;
	link: string;
	tags: string[];
}

/** PRO-only experiments; these routes are absent from a community build. */
export const experimentalExtras: ExperimentalEntry[] = [
	{
		title: 'Domain Whiteboard',
		desc: 'Restructure your domain hierarchy on a canvas. Drag a domain onto another — or just where its sub-domains sit — to nest it, create sub-domains in place, rename inline. Every move is confirmed with its access impact spelled out.',
		link: '/experimental/domain-board',
		tags: ['domains', 'iam', 'graph', 'canvas', 'prototype']
	}
];
