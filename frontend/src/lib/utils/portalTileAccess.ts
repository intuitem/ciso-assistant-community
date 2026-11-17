type Tile = { kind: string; target?: Record<string, any> };

export type TileAccess = {
	/** Does the viewer hold this permission codename on at least one folder? */
	has: (codename: string) => boolean;
	/** Model name (e.g. `appliedcontrol`) behind a url-model, undefined for plain pages. */
	modelName: (urlModel: string) => string | undefined;
	/** Containers the viewer can read; only fetched when the portal has a document tile. */
	readableDocuments: Set<string>;
};

/** Whether a tile leads somewhere the viewer can go. Tiles the backend checks at
 *  click time (assessment, quick form) or that leave the app stay visible. */
export function canUseTile(item: Tile, access: TileAccess): boolean {
	const t = item.target ?? {};
	if (item.kind !== 'create' && item.kind !== 'navigate') return true;
	if (t.model === 'documents') {
		if (t.document) return access.readableDocuments.has(t.document);
		return access.has('view_documentcontainer') || access.has('view_published_documentcontainer');
	}
	const name = access.modelName(t.model);
	// Plain pages (my-assignments, auditee-dashboard…) carry their own access rules.
	if (!name) return true;
	return access.has(`${item.kind === 'create' ? 'add' : 'view'}_${name}`);
}
