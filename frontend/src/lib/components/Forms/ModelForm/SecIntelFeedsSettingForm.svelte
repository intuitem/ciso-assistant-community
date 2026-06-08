<script lang="ts">
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import NumberField from '../NumberField.svelte';
	import { m } from '$paraglide/messages';
	import type { ModelInfo } from '$lib/utils/types';
	import type { SuperForm } from 'sveltekit-superforms';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
	}

	let { form }: Props = $props();
</script>

<div class="space-y-4">
	<Checkbox
		{form}
		field="kev_feed_enabled"
		label={m.kevFeedEnabled()}
		helpText={m.kevFeedEnabledHelpText()}
	/>
	<Checkbox
		{form}
		field="epss_feed_enabled"
		label={m.epssFeedEnabled()}
		helpText={m.epssFeedEnabledHelpText()}
	/>
	<Checkbox
		{form}
		field="nvd_enrich_enabled"
		label={m.nvdEnrichEnabled()}
		helpText={m.nvdEnrichEnabledHelpText()}
	/>
	<NumberField
		{form}
		field="network_timeout"
		label={m.networkTimeout()}
		helpText={m.networkTimeoutHelpText()}
		min={5}
		max={120}
		step={1}
	/>

	<div
		class="alert bg-blue-100 border border-blue-300 text-blue-800 px-4 py-3 rounded-lg text-xs mt-6"
	>
		<div class="font-semibold mb-2">
			<i class="fa-solid fa-circle-info mr-1"></i>{m.feedOutboundHostsTitle()}
		</div>
		<p class="mb-2">{m.feedOutboundHostsHelpText()}</p>
		<ul class="list-disc list-inside space-y-1 font-mono">
			<li><span class="font-semibold">www.cisa.gov</span> — KEV</li>
			<li><span class="font-semibold">epss.empiricalsecurity.com</span> — EPSS bulk CSV</li>
			<li><span class="font-semibold">api.first.org</span> — EPSS per-CVE API</li>
			<li><span class="font-semibold">services.nvd.nist.gov</span> — NVD enrichment</li>
			<li><span class="font-semibold">euvdservices.enisa.europa.eu</span> — EUVD</li>
			<li><span class="font-semibold">cwe.mitre.org</span> — CWE catalog</li>
		</ul>
	</div>
</div>
