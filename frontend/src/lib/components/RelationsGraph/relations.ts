import { getModelInfo } from '$lib/utils/crud';

/**
 * Which relations a mini graph shows, per model.
 *
 * Strictly opt-in, like batch actions: a model with no entry gets no graph button.
 * A generic ORM walk is not an option — AppliedControl alone exposes ten forward
 * and twenty-one reverse relations, most of which nobody wants to look at.
 *
 * Verbs follow the product-docs convention (satisfied by / mitigated by /
 * remediated by / maintains), so the graph reads the same way the docs do.
 */

export interface ForwardRelation {
	/** Field on the detail payload, resolved by the read serializer. */
	field: string;
	urlModel: string;
	verb: string;
	/** Draw the arrow neighbour -> root (the neighbour owns the relation). */
	inbound?: boolean;
}

export interface ReverseRelation {
	/** List endpoint to query. */
	urlModel: string;
	/** Filter parameter on that endpoint holding the root's id. */
	param: string;
	verb: string;
}

export interface RelationSpec {
	forward: ForwardRelation[];
	reverse: ReverseRelation[];
}

export const RELATION_MAP: Record<string, RelationSpec> = {
	'applied-controls': {
		forward: [
			{
				field: 'reference_control',
				urlModel: 'reference-controls',
				verb: 'templates',
				inbound: true
			},
			{ field: 'assets', urlModel: 'assets', verb: 'protects' },
			{ field: 'evidences', urlModel: 'evidences', verb: 'evidenced by' },
			{ field: 'owner', urlModel: 'actors', verb: 'owned by' },
			{ field: 'security_exceptions', urlModel: 'security-exceptions', verb: 'excepted by' },
			{ field: 'objectives', urlModel: 'organisation-objectives', verb: 'serves' },
			{ field: 'incidents', urlModel: 'incidents', verb: 'responds to' },
			{ field: 'folder', urlModel: 'folders', verb: 'scopes', inbound: true }
		],
		reverse: [
			{
				urlModel: 'requirement-assessments',
				param: 'applied_controls',
				verb: 'satisfied by'
			},
			{ urlModel: 'risk-scenarios', param: 'applied_controls', verb: 'mitigated by' },
			{ urlModel: 'findings', param: 'applied_controls', verb: 'remediated by' },
			{ urlModel: 'task-templates', param: 'applied_controls', verb: 'maintains' },
			{ urlModel: 'document-containers', param: 'applied_controls', verb: 'documented by' }
		]
	},

	'risk-scenarios': {
		forward: [
			{ field: 'risk_assessment', urlModel: 'risk-assessments', verb: 'comprises', inbound: true },
			{ field: 'assets', urlModel: 'assets', verb: 'targets' },
			{ field: 'threats', urlModel: 'threats', verb: 'driven by' },
			{ field: 'applied_controls', urlModel: 'applied-controls', verb: 'mitigated by' },
			{
				field: 'existing_applied_controls',
				urlModel: 'applied-controls',
				verb: 'already mitigated by'
			},
			{ field: 'incidents', urlModel: 'incidents', verb: 'realised by' },
			{ field: 'owner', urlModel: 'actors', verb: 'owned by' },
			{ field: 'security_exceptions', urlModel: 'security-exceptions', verb: 'excepted by' },
			{
				field: 'operational_scenario',
				urlModel: 'operational-scenarios',
				verb: 'derived from',
				inbound: true
			},
			{ field: 'folder', urlModel: 'folders', verb: 'scopes', inbound: true }
		],
		reverse: [
			{ urlModel: 'findings', param: 'risk_scenarios', verb: 'evidenced by' },
			// Not a forward relation despite being an M2M on the model: the read
			// serializer does not resolve it, so it has to be asked for.
			{ urlModel: 'vulnerabilities', param: 'risk_scenarios', verb: 'exploits' }
		]
	},

	assets: {
		forward: [
			{ field: 'parent_assets', urlModel: 'assets', verb: 'supports', inbound: true },
			{ field: 'support_assets', urlModel: 'assets', verb: 'supported by' },
			{ field: 'applied_controls', urlModel: 'applied-controls', verb: 'protected by' },
			{ field: 'solutions', urlModel: 'solutions', verb: 'delivered by' },
			{ field: 'personal_data', urlModel: 'personal-data', verb: 'holds' },
			{ field: 'owner', urlModel: 'actors', verb: 'owned by' },
			{ field: 'asset_class', urlModel: 'asset-classes', verb: 'classifies', inbound: true },
			{ field: 'security_exceptions', urlModel: 'security-exceptions', verb: 'excepted by' },
			{ field: 'folder', urlModel: 'folders', verb: 'scopes', inbound: true }
		],
		reverse: [
			{ urlModel: 'risk-scenarios', param: 'assets', verb: 'targets' },
			{ urlModel: 'findings', param: 'assets', verb: 'affects' },
			{ urlModel: 'vulnerabilities', param: 'assets', verb: 'exposes' },
			{ urlModel: 'compliance-assessments', param: 'assets', verb: 'audits' },
			{ urlModel: 'incidents', param: 'assets', verb: 'hit by' },
			{ urlModel: 'asset-assessments', param: 'asset', verb: 'assessed by' },
			{ urlModel: 'ebios-rm', param: 'assets', verb: 'studied by' },
			{ urlModel: 'quantitative-risk-scenarios', param: 'assets', verb: 'quantified by' }
		]
	}
};

/** Labels and bookkeeping rather than objects worth a node of their own. */
const GENERIC_SKIP = new Set(['filtering_labels', 'custom_field_values']);

export interface GenericRelation {
	field: string;
	urlModel: string;
	verb: string;
}

/**
 * Forward relations for a model with no curated entry, read off the field-to-model
 * metadata `crud.ts` already maintains for form pickers. A read serializer resolves
 * every forward relation as `{id, str}`, so this costs nothing beyond the fetch of
 * the object itself.
 *
 * Forward only, deliberately. The reverse direction would mean guessing a filter
 * name on a list endpoint, and DRF silently ignores a query parameter it does not
 * know — a wrong guess would not fail, it would return the entire table.
 */
export function genericForward(urlModel: string): GenericRelation[] {
	const info = getModelInfo(urlModel) as {
		foreignKeyFields?: { field: string; urlModel?: string }[];
	};
	return (info?.foreignKeyFields ?? [])
		.filter((f) => f?.field && f?.urlModel && !GENERIC_SKIP.has(f.field))
		.map((f) => ({ field: f.field, urlModel: f.urlModel!, verb: f.field.replace(/_/g, ' ') }));
}

/** Whether the drawer offers a Relations button for this model: curated only. */
export function hasRelationGraph(urlModel: string | undefined): boolean {
	return Boolean(urlModel && urlModel in RELATION_MAP);
}

/** Whether a node reached inside the drawer can be expanded further. */
export function canExploreModel(urlModel: string): boolean {
	return urlModel in RELATION_MAP || genericForward(urlModel).length > 0;
}
