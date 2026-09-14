import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { RELATION_MAP, genericForward } from '$lib/components/RelationsGraph/relations';
import type { GraphLink, GraphNode, Neighborhood } from '$lib/components/RelationsGraph/types';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/** Enough to see the shape without shipping a 300-row ring; the rest is reported
 *  as a count so the "+N" placeholder tells the truth. */
const PER_RELATION = 25;

/** `str` is usually "REF - name"; the ref half is the only part that fits a label. */
function splitRef(str: string): { ref?: string; name: string } {
	const i = str.indexOf(' - ');
	if (i > 0 && i <= 24) return { ref: str.slice(0, i), name: str.slice(i + 3) };
	return { name: str };
}

function toNode(raw: any, urlModel: string, group?: string): GraphNode | null {
	if (!raw?.id) return null;
	const str = String(raw.str ?? raw.name ?? raw.ref_id ?? '').trim();
	const split = splitRef(str);
	return {
		id: String(raw.id),
		urlModel,
		name: split.name || str || raw.id,
		ref: raw.ref_id ?? split.ref,
		group,
		meta: pickMeta(raw)
	};
}

function pickMeta(raw: any): Record<string, string> | undefined {
	const out: Record<string, string> = {};
	for (const key of ['status', 'result', 'severity', 'priority', 'treatment', 'type', 'category']) {
		const v = raw?.[key];
		if (typeof v === 'string' && v) out[key] = v;
	}
	return Object.keys(out).length ? out : undefined;
}

export const GET: RequestHandler = async ({ fetch, params }) => {
	const urlModel = params.model as string;
	// Curated models get both directions and hand-written verbs. Everything else
	// gets whatever its own payload already resolves, so a graph started on a
	// curated model can still walk one more step through a requirement assessment
	// or an audit without each of those needing an entry of its own.
	const spec = RELATION_MAP[urlModel] ?? {
		forward: genericForward(urlModel).map((r) => ({ ...r, inbound: false })),
		reverse: []
	};
	if (!spec.forward.length && !spec.reverse.length) {
		error(404, 'No relations are known for this model');
	}

	const model = getModelInfo(urlModel);
	const res = await fetch(`${BASE_API_URL}/${model.endpointUrl ?? urlModel}/${params.id}/`);
	if (!res.ok) error(res.status as NumericRange<400, 599>, 'Could not load the object');
	const obj = await res.json();

	const rootStr = String(obj.str ?? obj.name ?? '').trim();
	const rootSplit = splitRef(rootStr);
	const root: GraphNode = {
		id: String(obj.id),
		urlModel,
		name: rootSplit.name || rootStr,
		ref: obj.ref_id ?? rootSplit.ref
	};

	const nodes = new Map<string, GraphNode>();
	const links: GraphLink[] = [];
	const totals: Record<string, number> = {};

	const add = (node: GraphNode | null, verb: string, inbound: boolean) => {
		if (!node || node.id === root.id) return;
		if (!nodes.has(node.id)) nodes.set(node.id, node);
		links.push(
			inbound
				? { source: node.id, target: root.id, verb }
				: { source: root.id, target: node.id, verb }
		);
	};

	for (const rel of spec.forward) {
		const value = obj[rel.field];
		if (!value) continue;
		const items = Array.isArray(value) ? value : [value];
		const group = `${rel.verb}|${rel.urlModel}`;
		totals[group] = (totals[group] ?? 0) + items.length;
		for (const item of items)
			add(toNode(item, rel.urlModel, group), rel.verb, Boolean(rel.inbound));
	}

	const reverse = await Promise.all(
		spec.reverse.map(async (rel) => {
			const query = `${BASE_API_URL}/${rel.urlModel}/?${rel.param}=${params.id}&limit=${PER_RELATION}`;
			const r = await fetch(query);
			// One unreachable relation must not blank the whole graph.
			if (!r.ok) return { rel, results: [], count: 0 };
			const body = await r.json();
			const results = Array.isArray(body) ? body : (body.results ?? []);
			return { rel, results, count: body?.count ?? results.length };
		})
	);

	for (const { rel, results, count } of reverse) {
		const group = `${rel.verb}|${rel.urlModel}`;
		totals[group] = count;
		for (const item of results) add(toNode(item, rel.urlModel, group), rel.verb, true);
	}

	const payload: Neighborhood = { root, nodes: [...nodes.values()], links, totals };
	return json(payload, { headers: { 'Cache-Control': 'no-store' } });
};
