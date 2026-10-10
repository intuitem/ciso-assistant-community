// Pure helpers mapping an internal_event trigger's filter tree ({operator,
// conditions, children}) to and from the DNF ("or of and-groups") shape the
// builder UI edits.

// The comparison operators offered by both the DNF filter builder and the
// condition-node branch builder (mirrors the backend Condition.Operator set).
export const FILTER_OPS = [
	'eq',
	'neq',
	'gt',
	'lt',
	'gte',
	'lte',
	'in',
	'not_in',
	'contains',
	'is_null'
];

export interface Condition {
	field: string;
	op: string;
	value: string;
	changed: boolean;
}

export function newCondition(): Condition {
	return { field: '', op: 'eq', value: '', changed: false };
}

// Render a stored value for the text input such that parseValue() on the way
// back reproduces it exactly. A string that itself JSON-parses to a non-string
// (e.g. "5", "true") must be shown QUOTED, or the round-trip would coerce it to
// a number/boolean and silently change the condition.
function displayValue(v: unknown): string {
	if (v === undefined || v === null) return '';
	if (typeof v !== 'string') return JSON.stringify(v);
	try {
		if (typeof JSON.parse(v) !== 'string') return JSON.stringify(v);
	} catch {
		/* not JSON — safe to show verbatim */
	}
	return v;
}

function conditionsFrom(list: any[]): Condition[] {
	return list.map((c: any) => ({
		field: c.field ?? '',
		op: c.op ?? 'eq',
		value: displayValue(c.value),
		changed: !!c.changed
	}));
}

// Returns the DNF groups, or null when the tree doesn't fit the
// "or of and-groups" shape (deeper nesting, "not", ...).
export function treeToGroups(tree: any): Condition[][] | null {
	if (tree === null || tree === undefined) return [];
	if (typeof tree !== 'object' || Array.isArray(tree)) return null;
	if (Object.keys(tree).length === 0) return [];
	const conditions = Array.isArray(tree.conditions) ? tree.conditions : [];
	const children = Array.isArray(tree.children) ? tree.children : [];
	if (tree.operator === 'and') {
		if (children.length) return null;
		return [conditionsFrom(conditions)];
	}
	if (tree.operator === 'or') {
		const out: Condition[][] = [];
		for (const child of children) {
			if (
				!child ||
				typeof child !== 'object' ||
				child.operator !== 'and' ||
				(Array.isArray(child.children) ? child.children : []).length
			) {
				return null;
			}
			out.push(conditionsFrom(Array.isArray(child.conditions) ? child.conditions : []));
		}
		// Root-level conditions on an "or" node each count as one extra group.
		for (const cond of conditions) out.push(conditionsFrom([cond]));
		return out;
	}
	return null;
}

// "3" -> 3, "true" -> true, "[1,2]" -> [1,2]; anything unparseable stays a string.
function parseValue(raw: string): unknown {
	const trimmed = raw.trim();
	if (!trimmed) return raw;
	try {
		return JSON.parse(trimmed);
	} catch {
		return raw;
	}
}

function serializeCondition(c: Condition): Record<string, unknown> {
	const out: Record<string, unknown> = { field: c.field.trim(), op: c.op };
	if (c.op !== 'is_null') out.value = parseValue(c.value);
	if (c.changed) out.changed = true;
	return out;
}

export function groupsToTree(dnf: Condition[][]): Record<string, unknown> {
	const serialized = dnf
		.map((group) => group.filter((c) => c.field.trim()).map(serializeCondition))
		.filter((group) => group.length);
	if (!serialized.length) return {};
	if (serialized.length === 1) return { operator: 'and', conditions: serialized[0] };
	return {
		operator: 'or',
		conditions: [],
		children: serialized.map((conditions) => ({ operator: 'and', conditions }))
	};
}
