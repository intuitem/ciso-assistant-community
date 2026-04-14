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
</div>
