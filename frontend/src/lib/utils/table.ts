export const listViewFields = {
	folders: {
		head: ['name', 'description', 'parent domain'],
		body: ['name', 'description', 'parent_folder']
	},
	projects: {
		head: ['Name', 'Description', 'Domain'],
		body: ['name', 'description', 'folder']
	},
	'risk-matrices': {
		head: ['Name', 'Description', 'Provider', 'Domain'],
		body: ['name', 'description', 'provider', 'folder'],
		meta: ['id', 'urn']
	},
	'risk-assessments': {
		head: ['Name', 'Risk matrix', 'Description', 'Risk Scenarios', 'Project'],
		body: ['name', 'risk_matrix', 'description', 'risk_scenarios', 'project']
	},
	threats: {
		head: ['Ref', 'Name', 'Description', 'Provider', 'Domain'],
		body: ['ref_id', 'name', 'description', 'provider', 'folder'],
		meta: ['id', 'urn']
	},
	'risk-scenarios': {
		head: [
			'Name',
			'Threats',
			'Risk assessment',
			'Security measures',
			'Current level',
			'Residual level'
		],
		body: [
			'name',
			'threats',
			'risk_assessment',
			'security_measures',
			'current_level',
			'residual_level'
		]
	},
	'risk-acceptances': {
		head: ['Name', 'Description', 'Risk scenarios'],
		body: ['name', 'description', 'risk_scenarios']
	},
	'security-measures': {
		head: ['Name', 'Description', 'Category', 'ETA', 'Domain', 'Security function'],
		body: ['name', 'description', 'category', 'eta', 'folder', 'security_function']
	},
	policies: {
		head: ['Name', 'Description', 'ETA', 'Domain', 'Security function'],
		body: ['name', 'description', 'eta', 'folder', 'security_function']
	},
	'security-functions': {
		head: ['Ref', 'Name', 'Description', 'Category', 'Provider', 'Domain'],
		body: ['ref_id', 'name', 'description', 'category', 'provider', 'folder'],
		meta: ['id', 'urn']
	},
	assets: {
		head: ['Name', 'Description', 'Business value', 'Domain'],
		body: ['name', 'description', 'business_value', 'folder']
	},
	users: {
		head: ['Email', 'First name', 'Last name'],
		body: ['email', 'first_name', 'last_name']
	},
	'user-groups': {
		head: ['Name'],
		body: ['name'],
		meta: ['id', 'builtin']
	},
	roles: {
		head: ['Name', 'Description'],
		body: ['name', 'description']
	},
	'role-assignments': {
		head: ['User', 'User group', 'Role', 'Perimeter'],
		body: ['user', 'user_group', 'role', 'perimeter_folders']
	},
	frameworks: {
		head: ['Name', 'Description', 'Provider', 'Compliance assessments', 'Domain'],
		body: ['name', 'description', 'provider', 'compliance_assessments', 'folder'],
		meta: ['id', 'urn']
	},
	'compliance-assessments': {
		head: ['Name', 'Framework', 'Description', 'Project'],
		body: ['name', 'framework', 'description', 'project']
	},
	'requirement-assessments': {
		head: ['Name', 'Description', 'Compliance Assessment'],
		body: ['name', 'description', 'compliance_assessment']
	},
	evidences: {
		head: ['Name', 'File', 'Description'],
		body: ['name', 'attachment', 'description']
	},
	requirements: {
		head: ['Ref', 'Name', 'Description', 'Framework'],
		body: ['ref_id', 'name', 'description', 'framework'],
		meta: ['id', 'urn']
	},
	libraries: {
		head: ['Ref', 'Name', 'Description', 'Language', 'Overview'],
		body: ['ref_id', 'name', 'description', 'locale', 'overview']
	}
};
