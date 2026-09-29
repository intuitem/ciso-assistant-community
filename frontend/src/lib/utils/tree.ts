/** A row of a self-referencing collection: its own id and the id of the row it
 * hangs from. */
export interface TreeRow {
	id: string | number;
	parent_folder?: { id?: string | number } | null;
}

/**
 * Ids of `roots` together with every row filed below one of them.
 *
 * Walks each row's parent chain, so `rows` must hold the whole collection: a row
 * whose chain is cut short is left out rather than guessed at. A chain that loops
 * back on itself stops instead of spinning — the API rejects cycles, but this must
 * not depend on data it did not produce.
 */
export function subtreeIds(rows: TreeRow[], roots: string[]): Set<string> {
	const included = new Set(roots);
	const parentOf = new Map<string, string | undefined>(
		rows.map((row) => [
			String(row.id),
			row.parent_folder?.id ? String(row.parent_folder.id) : undefined
		])
	);
	for (const id of parentOf.keys()) {
		const walked = new Set<string>([id]);
		let cursor = parentOf.get(id);
		while (cursor && !walked.has(cursor)) {
			if (included.has(cursor)) {
				included.add(id);
				break;
			}
			walked.add(cursor);
			cursor = parentOf.get(cursor);
		}
	}
	return included;
}
