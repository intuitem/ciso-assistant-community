<script lang="ts">
	import { Switch } from '@skeletonlabs/skeleton-svelte';
	import { m } from '#paraglide/messages.js';

	// Applicability of a requirement in a score-only audit (compliance hidden),
	// on by default. Off marks it not applicable: it writes `result`, the only
	// place N/A lives, as not_applicable; back on, as not_assessed.
	interface Props {
		applicable: boolean;
		disabled?: boolean;
		onChange: (result: 'not_assessed' | 'not_applicable') => void;
	}

	let { applicable, disabled = false, onChange }: Props = $props();
</script>

<div class="flex items-center gap-3" data-testid="applicability-toggle">
	<Switch
		name="applicable"
		checked={applicable}
		{disabled}
		onCheckedChange={(e) => onChange(e.checked ? 'not_assessed' : 'not_applicable')}
	>
		<Switch.Control>
			<Switch.Thumb />
		</Switch.Control>
		<Switch.HiddenInput />
	</Switch>
	<span class="text-sm font-medium">{m.applicable()}</span>
</div>
