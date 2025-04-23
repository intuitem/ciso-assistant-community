<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	import { ffNav } from '$lib/components/SideBar/ffNav';
	export let data: any = {};
</script>

<Checkbox {form} field="xrays" label={m.xRays()} />

<Checkbox {form} field="incidents" label={m.incidents()} />
<Checkbox {form} field="tasks" label={m.tasks()} />
<Checkbox {form} field="risk_acceptances" label={m.riskAcceptances()} />
<Checkbox {form} field="exceptions" label={m.securityExceptions()} />
<Checkbox {form} field="follow_up" label={m.followUp()} />
<Checkbox {form} field="ebiosrm" label={m.ebiosRM()} />
<Checkbox {form} field="scoring_assistant" label={m.scoringAssistant()} />
<Checkbox {form} field="vulnerabilities" label={m.vulnerabilities()} />
<Checkbox {form} field="compliance" label={m.compliance()} />
<Checkbox {form} field="tprm" label={m.thirdParty()} />
<Checkbox {form} field="privacy" label={m.privacy()} />
<Checkbox {form} field="experimental" label={m.experimental()} />
