<script lang="ts">
	import DoraReportForm from '../../DoraReportForm.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DoraReportForm
	form={data.form}
	selectOptions={data.selectOptions}
	allChoices={data.allChoices}
	mode={data.mode}
	formAction={data.formAction}
	incidentRef={data.incidentRef}
/>
