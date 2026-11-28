export type Counts = Record<
	| 'requirement_assessments'
	| 'risk_scenarios'
	| 'risk_treatment'
	| 'risk_existing'
	| 'findings'
	| 'evidences'
	| 'documents',
	number
> &
	Record<
		| 'audits'
		| 'open_vulnerabilities'
		| 'resolved_vulnerabilities'
		| 'data_breaches'
		| 'incidents'
		| 'assets'
		| 'recurring_tasks'
		| 'threat_models'
		| 'security_exceptions'
		| 'quantitative_risk_existing'
		| 'quantitative_risk_added'
		| 'quantitative_risk_removed',
		number
	>;

export type ScoredLink =
	| 'requirement_assessments'
	| 'risk_scenarios'
	| 'findings'
	| 'open_vulnerabilities'
	| 'data_breaches'
	| 'quantitative_risk_existing';

export interface ControlRow {
	id: string;
	name: string;
	ref_id: string | null;
	score: number;
	counts: Counts;
}

export interface ReferenceRow extends ControlRow {
	implementations: number;
	catalog_requirements: number;
}

export type Priority = 1 | 2 | 3 | 4 | null;

export interface AppliedRow extends ControlRow {
	domain: string;
	priority: Priority;
	can_edit_priority: boolean;
}

export interface Portfolio {
	applied_controls: AppliedRow[];
	reference_controls: ReferenceRow[];
	weights: Record<ScoredLink, number>;
}
