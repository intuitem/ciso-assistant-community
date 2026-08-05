// Saved-filter-eligible URLModels → their backend app_label.model.
// Mirrors CUSTOM_FIELD_HOST_MODELS: an explicit opt-in set, not derived from
// the backend's full registry (core/saved_filters/registry.py), so it can
// drift if a listed model's router registration changes -- same known
// limitation already accepted for custom fields.
export const SAVED_FILTER_TARGET_MODELS: Record<string, string> = {
	'risk-assessments': 'core.riskassessment',
	'compliance-assessments': 'core.complianceassessment',
	'applied-controls': 'core.appliedcontrol',
	assets: 'core.asset',
	entities: 'tprm.entity'
};

export interface SavedFilterEntry {
	id: string;
	shared_id: string | null;
	name: string;
	model: string;
	properties: Record<string, { value: string }[]>;
	updated_at: string;
}

export interface SharedSavedFilter {
	id: string;
	name: string;
	folder: string;
	model: string;
	properties: Record<string, { value: string }[]>;
	updated_at: string;
}
