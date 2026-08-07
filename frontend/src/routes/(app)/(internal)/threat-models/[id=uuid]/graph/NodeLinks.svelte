<script lang="ts">
	import { m } from '$paraglide/messages';
	import { z } from 'zod';
	import { superForm, defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';

	interface Props {
		assets: string[];
		appliedControls: string[];
		vulnerabilities: string[];
		readonly?: boolean;
		onUpdate: (patch: Record<string, unknown>) => void;
	}

	let { assets, appliedControls, vulnerabilities, readonly = false, onUpdate }: Props = $props();

	// one form per node: the parent keys this component on the node id, so the
	// pickers are constructed with the right values instead of being reseeded after mount
	const schema = z.object({
		assets: z.string().uuid().array().optional(),
		applied_controls: z.string().uuid().array().optional(),
		vulnerabilities: z.string().uuid().array().optional()
	});
	const _form = superForm(
		defaults({ assets, applied_controls: appliedControls, vulnerabilities }, zod(schema)),
		{ dataType: 'json', taintedMessage: false, SPA: true, validators: zod(schema) }
	);
</script>

<AutocompleteSelect
	form={_form}
	multiple
	lazy
	optionsEndpoint="assets"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="assets"
	label={m.assets()}
	disabled={readonly}
	onChange={(v) => onUpdate({ assets: v ?? [] })}
/>
<AutocompleteSelect
	form={_form}
	multiple
	lazy
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="applied_controls"
	label={m.appliedControls()}
	disabled={readonly}
	onChange={(v) => onUpdate({ appliedControls: v ?? [] })}
/>
<AutocompleteSelect
	form={_form}
	multiple
	lazy
	optionsEndpoint="vulnerabilities"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="vulnerabilities"
	label={m.vulnerabilities()}
	disabled={readonly}
	onChange={(v) => onUpdate({ vulnerabilities: v ?? [] })}
/>
