<script lang="ts">
  import ciso from "$lib/assets/ciso.svg";

  import { onMount } from "svelte";
  import { page } from "$app/stores";

  export let height = 200;
  export let width = 200;

  interface Attachment {
    type: string;
    url: string;
  }

  let clientSettings: Record<string, any>;
  let logo: Attachment;

  onMount(async () => {
    clientSettings = await fetch("/settings/client-settings")
      .then((res) => res.json())
      .catch((res) => console.error("Failed to fetch client settings", res));
    const fetchLogo = async () => {
      const res = await fetch(
        `/settings/client-settings/${clientSettings.id}/logo`,
      );
      const blob = await res.blob();
      return { type: blob.type, url: URL.createObjectURL(blob) };
    };
    logo = clientSettings.logo ? await fetchLogo() : undefined;
  });
</script>

{#if logo}
  <div class="flex flex-col">
    <img src={logo.url} alt="Ciso-assistant icon" />
    {#if clientSettings}
      <p class="font-semibold text-center">{clientSettings.name}</p>
    {/if}
  </div>
{:else}
  <img width={200} height={200} src={ciso} alt="Ciso-assistant icon" />
{/if}
