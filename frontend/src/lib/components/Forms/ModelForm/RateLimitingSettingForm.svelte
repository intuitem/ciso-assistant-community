<script lang="ts">
	import NumberField from '../NumberField.svelte';
	import { m } from '$paraglide/messages';
	import {
		MIN_MAX_FAILED_LOGIN_ATTEMPTS,
		MAX_MAX_FAILED_LOGIN_ATTEMPTS,
		MAX_TIME_WINDOW_SIZE,
		MAX_BAN_TIME,
		MAX_ABSOLUTE_BAN_TIME
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
		label={m.timeWindowSize()}
		helpText={m.timeWindowSizeHelpText()}
		min={1}
		max={MAX_TIME_WINDOW_SIZE}
		step={1}
	/>
	<NumberField
		{form}
		field="ban_time"
		label={m.banTime()}
		helpText={m.banTimeHelpText({ max: MAX_ABSOLUTE_BAN_TIME })}
		min={1}
		max={MAX_BAN_TIME}
		step={1}
	/>
</div>
