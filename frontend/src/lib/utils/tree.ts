/** A row of a self-referencing collection: its own id and the id of the row it
 * hangs from. */
export interface TreeRow {
	id: string | number;
	parent_folder?: { id?: string | number } | null;
}

function parentIndex(rows: TreeRow[]): Map<string, string | undefined> {
	return new Map(
		rows.map((row) => [
			String(row.id),
			row.parent_folder?.id ? String(row.parent_folder.id) : undefined
		])
	);
}

/** Yields the ancestors of `id`, nearest first, stopping at a cycle. */
function* ancestors(parentOf: Map<string, string | undefined>, id: string): Generator<string> {
	const walked = new Set<string>([id]);
	let cursor = parentOf.get(id);
	while (cursor && !walked.has(cursor)) {
		yield cursor;
		walked.add(cursor);
		cursor = parentOf.get(cursor);
	}
}

/**
 * Ids of `roots` together with every row filed below one of them.
 *
 * Walks each row's parent chain, so `rows` must hold the whole collection: a row
 * whose chain is cut short is left out rather than guessed at.
 */
export function subtreeIds(rows: TreeRow[], roots: string[]): Set<string> {
	const included = new Set(roots);
	const parentOf = parentIndex(rows);
	for (const id of parentOf.keys()) {
		for (const ancestor of ancestors(parentOf, id)) {
			if (included.has(ancestor)) {
				included.add(id);
				break;
			}
		}
	}
	return included;
}

/**
 * Ids among `ids` filed below another of them, at any depth.
 *
 * Reparenting each id on its own detaches these from the selected ancestor they
 * hang from. `rows` must hold the whole collection, as for `subtreeIds`.
 */
export function nestedIds(rows: TreeRow[], ids: string[]): Set<string> {
	const selected = new Set(ids);
	const parentOf = parentIndex(rows);
	return new Set(
		ids.filter((id) => [...ancestors(parentOf, id)].some((ancestor) => selected.has(ancestor)))
	);
}
