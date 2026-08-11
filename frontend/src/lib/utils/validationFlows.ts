import { m } from '$paraglide/messages';

export type ValidationFlowAction =
	'approve' | 'reject' | 'request_changes' | 'drop' | 'revoke' | 'resubmit';

export const VALIDATION_FLOW_MODEL_URLS: Record<string, string> = {
	compliance_assessments: 'compliance-assessments',
	risk_assessments: 'risk-assessments',
	business_impact_analysis: 'business-impact-analysis',
	crq_studies: 'quantitative-risk-studies',
	ebios_studies: 'ebios-rm',
	entity_assessments: 'entity-assessments',
	findings_assessments: 'findings-assessments',
	evidences: 'evidences',
	security_exceptions: 'security-exceptions',
	policies: 'policies',
	processings: 'processings',
	accreditations: 'accreditations',
	contracts: 'contracts',
	managed_documents: 'managed-documents'
};

export function validationFlowModelLabels(): Record<string, string> {
	return {
		compliance_assessments: m.complianceAssessments(),
		risk_assessments: m.riskAssessments(),
		business_impact_analysis: m.businessImpactAnalysis(),
		crq_studies: m.quantitativeRiskStudies(),
		ebios_studies: m.ebiosRMStudies(),
		entity_assessments: m.entityAssessments(),
		findings_assessments: m.findingsAssessments(),
		evidences: m.evidences(),
		security_exceptions: m.securityExceptions(),
		policies: m.policies(),
		processings: m.processings(),
		accreditations: m.accreditations(),
		contracts: m.contracts(),
		managed_documents: m.managedDocuments()
	};
}

export function validationFlowItemHref(key: string, item: any): string {
	if (key === 'managed_documents' && item.policy?.id) {
		return `/policies/${item.policy.id}/document`;
	}
	return `/${VALIDATION_FLOW_MODEL_URLS[key]}/${item.id}`;
}

/** Flattened view of everything a flow is about, across all its m2m buckets. */
export function validationFlowLinkedObjects(flow: any): { key: string; item: any; href: string }[] {
	const objects: { key: string; item: any; href: string }[] = [];
	for (const key of Object.keys(VALIDATION_FLOW_MODEL_URLS)) {
		const value = flow[key];
		if (!Array.isArray(value)) continue;
		for (const item of value) {
			objects.push({ key, item, href: validationFlowItemHref(key, item) });
		}
	}
	return objects;
}

export const VALIDATION_STATUS_COLORS: Record<string, string> = {
	submitted: 'bg-blue-100 text-blue-800',
	accepted: 'bg-green-100 text-green-800',
	rejected: 'bg-red-100 text-red-800',
	revoked: 'bg-surface-100-900 text-surface-950-50',
	expired: 'bg-orange-100 text-orange-800',
	dropped: 'bg-surface-100-900 text-surface-950-50',
	change_requested: 'bg-yellow-100 text-yellow-800'
};

export function validationStatusColor(status: string): string {
	return VALIDATION_STATUS_COLORS[status] ?? 'bg-surface-100-900 text-surface-950-50';
}

/** Transitions the given user may trigger on a flow, mirroring the backend rules. */
export function validationFlowActions(flow: any, userId: string): ValidationFlowAction[] {
	const isApprover = String(userId) === String(flow.approver?.id);
	const isRequester = String(userId) === String(flow.requester?.id);
	switch (flow.status) {
		case 'submitted':
			if (isApprover) return ['approve', 'reject', 'request_changes', 'drop'];
			return isRequester ? ['drop'] : [];
		case 'accepted':
			return isApprover ? ['revoke'] : [];
		case 'change_requested':
			return isRequester ? ['resubmit', 'drop'] : [];
		default:
			return [];
	}
}

export const VALIDATION_ACTION_ICONS: Record<ValidationFlowAction, string> = {
	approve: 'fa-check',
	reject: 'fa-xmark',
	request_changes: 'fa-pencil',
	drop: 'fa-trash',
	revoke: 'fa-ban',
	resubmit: 'fa-paper-plane'
};

export const VALIDATION_ACTION_CLASSES: Record<ValidationFlowAction, string> = {
	approve: 'preset-filled-success-500',
	reject: 'preset-filled-error-500',
	request_changes: 'preset-tonal-warning',
	drop: 'preset-tonal-surface',
	revoke: 'preset-filled-warning-500',
	resubmit: 'preset-filled-primary-500'
};

export function validationActionLabels(): Record<ValidationFlowAction, string> {
	return {
		approve: m.approve(),
		reject: m.reject(),
		request_changes: m.requestChanges(),
		drop: m.drop(),
		revoke: m.revoke(),
		resubmit: m.resubmit()
	};
}
