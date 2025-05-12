<script lang="ts">
	import RecursiveLogEntryChanges from "./components/RecursiveLogEntryChanges.svelte";

  export let data;
</script>

<main class="card shadow-lg bg-white p-4">
  <div class="flex w-full">
    <div class="w-full rounded-lg border border-gray-100 py-3 shadow-sm">
      <RecursiveLogEntryChanges log={data.log} />
    </div>
  </div>
</main>

