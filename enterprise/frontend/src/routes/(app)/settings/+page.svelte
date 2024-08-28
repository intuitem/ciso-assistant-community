<script lang="ts">
  import { page } from "$app/stores";
  import ModelForm from "$lib/components/Forms/ModelForm.svelte";
  import { SSOSettingsSchema } from "$lib/utils/schemas";
  import * as m from "$paraglide/messages";
  import { Tab, TabGroup } from "@skeletonlabs/skeleton";
  import ClientSettings from "./client-settings/+page.svelte";
  import { goto, preloadData, pushState } from "$app/navigation";

  let tabSet = 0;

  export let data;
</script>

<TabGroup active="bg-primary-100 text-primary-800 border-b border-primary-800">
  <Tab bind:group={tabSet} name="ssoSettings" value={0}
    ><i class="fa-solid fa-key" /> {m.sso()}</Tab
  >
  {#if data.featureFlags.whiteLabel === true}
    <Tab
      bind:group={tabSet}
      name="clientSettings"
      value={1}
      on:change={async (e) => {
        e.preventDefault();
        const href = "/settings/client-settings";
        const result = await preloadData(href);
        if (result.type === "loaded" && result.status === 200) {
          pushState(href, { clientSettings: result.data });
        } else {
          // Something went wrong, try navigating
          goto(href);
        }
      }}><i class="fa-solid fa-key" /> _clientsettings</Tab
    >
  {/if}
</TabGroup>
{#if tabSet === 0}
  <div>
    <span class="text-gray-500">{m.ssoSettingsDescription()}</span>
    <ModelForm
      form={data.form}
      schema={SSOSettingsSchema}
      model={data.model}
      cancelButton={false}
    />
  </div>
{:else if tabSet === 1}
  <ClientSettings data={$page.state.clientSettings} />
{/if}
