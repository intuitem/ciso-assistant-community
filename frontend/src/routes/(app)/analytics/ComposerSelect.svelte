<script lang="ts">
	import { composerSchema } from '$lib/utils/schemas';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import type { AnyZodObject } from 'zod';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import { getOptions } from '$lib/utils/crud';
	import * as m from '$paraglide/messages';
	import { zod } from 'sveltekit-superforms/adapters';

	export let composerForm: SuperValidated<Record<string, any>>;

	let options: { label: string; value: string }[];

	onMount(async () => {
		const riskAssessments = await fetch('/risk-assessments').then((res) => res.json());
		console.log(riskAssessments)
		options = getOptions({ objects: riskAssessments, extra_fields: [['project', 'str']] });
	});
</script>

<SuperForm
	dataType="json"
	data={composerForm}
	let:form
	validators={zod(composerSchema)}
	taintedMessage={null}
	let:data
>
	<div class="flex flex-col space-y-2 items-center card variant-ghost-surface p-4">
		{#if options}
			<AutocompleteSelect
				multiple={true}
				{form}
				field="risk_assessment"
				placeholder={m.selectTargets()}
				{options}
			/>
			{#if data.risk_assessment && data.risk_assessment.length > 0}
				<a
					href={`/analytics/composer/?risk_assessment=${data.risk_assessment}`}
					class="btn variant-filled-primary">{m.processButton()}</a
				>
			{:else}
				<p class="btn-base rounded-token select-none variant-filled-surface opacity-30">
					{m.processButton()}
				</p>
			{/if}
		{/if}
	</div>
</SuperForm>
