<script lang="ts">
	import * as m from '$paraglide/messages.js';

	export let data;

	const measureStatusColorMap = (treatment: string) => {
		const map: Record<string, string> = {
			open: 'bg-orange-200',
			'in progress': 'bg-blue-200',
			'on hold': 'bg-red-200',
			done: 'bg-success-200'
		};
		if (treatment !== null) {
			return map[treatment.toLowerCase()];
		} else {
			return 'bg-gray-200';
		}
	};
</script>

<div class="bg-white p-2 m-2 shadow rounded-lg space-x-2 flex flex-row justify-center">
	<p class="font-semibold text-lg">
		{m.project()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/projects/{data.compliance_assessment.project.id}/">{data.compliance_assessment.project.str}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		{m.complianceAssessment()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/compliance-assessments/{data.compliance_assessment.id}/"
			>{data.compliance_assessment.name} - {data.compliance_assessment.version}</a
		>
	</p>
</div>

<p class="p-2 m-2 text-lg font-semibold">{m.associatedRiskScenarios()}:</p>