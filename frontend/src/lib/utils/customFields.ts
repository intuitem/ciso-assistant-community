// Custom-field host url models → their backend app_label.model.
// Mirrors the explicit opt-in set of CustomFieldsMixin hosts on the backend.
// Kept component-free so it is safe to import from server load functions.
export const CUSTOM_FIELD_HOST_MODELS: Record<string, string> = {
	assets: 'core.asset',
	'applied-controls': 'core.appliedcontrol',
	policies: 'core.appliedcontrol',
	projects: 'pmbok.project'
};

export interface CustomFieldChoice {
	value: string;
	label_localized: string;
}

export interface CustomFieldDef {
	id: string;
	key: string;
	label_localized: string;
	help_text_localized?: string;
	field_type: string;
	choices: CustomFieldChoice[];
}
