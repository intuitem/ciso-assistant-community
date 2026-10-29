<script lang="ts">
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import NumberField from '../NumberField.svelte';
	import { m } from '$paraglide/messages';
	import {
		MIN_MAX_FAILED_LOGIN_ATTEMPTS,
		MAX_MAX_FAILED_LOGIN_ATTEMPTS,
		MAX_TIME_WINDOW_SIZE
	} from '$lib/utils/schemas';
	import type { ModelInfo } from '$lib/utils/types';
	import type { SuperForm } from 'sveltekit-superforms';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
	}

	let { form }: Props = $props();
</script>

<div class="flex flex-col gap-4 max-w-md">
	<Checkbox
		{form}
		field="enabled"
		label={m.rateLimitingEnabled()}
		helpText={m.rateLimitingEnabledHelpText()}
	/>
	<NumberField
		{form}
		field="max_failed_login_attempts"
		label={m.maxFailedLoginAttempts()}
		helpText={m.maxFailedLoginAttemptsHelpText()}
		min={MIN_MAX_FAILED_LOGIN_ATTEMPTS}
		max={MAX_MAX_FAILED_LOGIN_ATTEMPTS}
		step={1}
	/>
	<NumberField
		{form}
		field="time_window_size"
		label={m.observationWindowSize()}
		helpText={m.observationWindowSizeHelpText()}
		min={1}
		max={MAX_TIME_WINDOW_SIZE}
		step={1}
	/>
</div>
