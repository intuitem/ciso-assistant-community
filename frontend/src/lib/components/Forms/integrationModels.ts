import { m } from '$paraglide/messages';

// Local field definitions for the FieldMapper, per syncable model. Kept in sync
// with the backend registry in integrations/syncable.py. AppliedControl fields
// live in FieldMapper.svelte (its default); add new models here.
export const ASSET_LOCAL_FIELDS = [
	{ key: 'name', label: m.name(), type: 'string', required: true },
	{ key: 'description', label: m.description(), type: 'text', required: false },
	{ key: 'ref_id', label: m.refId(), type: 'string', required: false },
	{ key: 'reference_link', label: m.referenceLink(), type: 'string', required: false },
	{ key: 'observation', label: m.observation(), type: 'text', required: false },
	{
		key: 'type',
		label: m.type(),
		type: 'choice',
		choices: [
			{ value: 'PR', label: m.primary() },
			{ value: 'SP', label: m.support() }
		]
	}
];
