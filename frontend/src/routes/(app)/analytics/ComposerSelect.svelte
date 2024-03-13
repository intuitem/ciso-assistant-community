<script lang="ts">
	import { composerSchema } from '$lib/utils/schemas';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import type { AnyZodObject } from 'zod';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import { getOptions } from '$lib/utils/crud';
	import * as m from '$paraglide/messages';

	export let composerForm: SuperValidated<AnyZodObject>;

	let options: { label: string; value: string }[];

	onMount(async () => {
		const riskAssessments = await fetch('/risk-assessments').then((res) => res.json());
		options = getOptions({ objects: riskAssessments });
	});
</script>

<p>{m.selectTargets()}</p>
<SuperForm dataType="json" data={composerForm} let:form validators={composerSchema} let:data>
	{#if options}
		<AutocompleteSelect multiple={true} {form} field="risk_assessment" {options} />
	{/if}
	<a href={`/analytics/composer/?risk_assessment=${data.risk_assessment}`} class="btn btn-primary"
		>{m.submit()}</a
	>
</SuperForm>
