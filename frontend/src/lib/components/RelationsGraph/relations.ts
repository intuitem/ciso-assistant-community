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
			{ field: 'reference_control', urlModel: 'reference-controls', verb: 'templates', inbound: true },
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
			{ urlModel: 'task-templates', param: 'applied_controls', verb: 'maintains' }
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
		reverse: [{ urlModel: 'findings', param: 'risk_scenarios', verb: 'evidenced by' }]
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
			{ urlModel: 'findings', param: 'assets', verb: 'affects' }
		]
	}
};

export function hasRelationGraph(urlModel: string | undefined): boolean {
	return Boolean(urlModel && urlModel in RELATION_MAP);
}
