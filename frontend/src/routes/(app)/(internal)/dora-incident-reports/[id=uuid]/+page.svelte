<script lang="ts">
	import DoraReportForm from '../DoraReportForm.svelte';
	import { page } from '$app/state';
	import { invalidateAll } from '$app/navigation';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Force full reload when markSubmitted action completes
	$effect(() => {
		if (page.form?.submitted) {
			window.location.reload();
		}
	});
</script>

<DoraReportForm
	form={data.form}
	selectOptions={data.selectOptions}
	allChoices={data.allChoices}
	mode={data.mode}
	formAction={data.formAction}
	incidentRef={data.incidentRef}
	reportId={data.reportId}
	validation={data.validation}
	userOptions={data.userOptions}
/>
