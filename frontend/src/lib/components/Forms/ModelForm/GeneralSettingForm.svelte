<script lang="ts">
    import Select from "../Select.svelte";
    import * as m from "$paraglide/messages";

    export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let data: any = {};
</script>

<Select
    form={form}
    field="security_objective_standard"
    cacheLock={cacheLocks['security_objective_standard']}
    bind:cachedValue={formDataCache['security_objective_standard']}
    options={model.selectOptions['security_objective_standard']}
    label={m.securityObjectiveStandard()}
/>