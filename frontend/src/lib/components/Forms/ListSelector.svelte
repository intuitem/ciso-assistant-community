<script lang="ts">
  import { onMount, getContext, onDestroy } from "svelte";
  import { safeTranslate } from "$lib/utils/i18n";
  import type { CacheLock } from "$lib/utils/types";
  import { formFieldProxy, type SuperForm } from "sveltekit-superforms";

  interface Option {
    label: string;
    value: string | number;
    group?: string;
    translatedLabel?: string;
  }

  interface Props {
    form: SuperForm<Record<string, unknown>, any>;
    field: string;
    label?: string;
    helpText?: string;
    optionsEndpoint: string;
    optionsLabelField?: string;
    groupBy?: { field: string; path: string[]; }[] | string; // can be array of fields with path to add sub-groups or single field
    cacheLock?: CacheLock;
    cachedValue?: (string | number)[] | undefined;
    translateOptions?: boolean;
    disabled?: boolean;
    mandatory?: boolean;
  }

  let {
    form,
    field,
    label,
    helpText,
    optionsEndpoint,
    optionsLabelField = "name",
    groupBy = "",
    cacheLock = {
      promise: new Promise((res) => res(null)),
      resolve: (x: any) => x
    },
    cachedValue = $bindable(),
    translateOptions = true,
    disabled = false,
    mandatory = false
  }: Props = $props();

  const { value, errors, constraints } = formFieldProxy(form, field);

  let options: Option[] = $state([]);
  let selected: (string | number)[] = $state([]);
  let isLoading = $state(false);

  // fetch options
  async function fetchOptions() {
    isLoading = true;
    try {
      let endpoint = `/${optionsEndpoint}`;
      const response = await fetch(endpoint);
      if (response.ok) {
        const data = await response.json().then((res) => res?.results ?? res);

        options = data.map((option: any) => {
          const label = option[optionsLabelField] ?? "--";
          const groupsList = Array.isArray(groupBy)
            ? groupBy
                .map((group) => {
                    let grp = option[group.field];
                    for (const p of group.path) {
                        grp = grp?.[p];
                    }
                    return grp;
                })
            : groupBy
              ? [option[groupBy]]
              : [];
          return {
            label,
            value: option.id,
            groupsList,
            translatedLabel: translateOptions ? safeTranslate(label) : label
          };
        });
      }
      // init selection
      if ($value) {
        selected = Array.isArray($value) ? $value : [$value];
      }
    } catch (err) {
      console.error("Error fetching options", err);
    } finally {
      isLoading = false;
    }
  }

  function toggle(val: string | number) {
    if (selected.includes(val)) {
      selected = selected.filter((v) => v !== val);
    } else {
      selected = [...selected, val];
    }
    $value = selected;
    cacheLock.resolve(selected);
  }

  onMount(async () => {
    await fetchOptions();
    const cacheResult = await cacheLock.promise;
    if (cacheResult?.length) {
      selected = cacheResult;
    }
  });

  onDestroy(() => {
    cacheLock.resolve(selected);
  });

  $inspect(options)
</script>

<div class="space-y-4">
  {#if label}
    <label class="text-sm font-semibold">{label}{mandatory ? " *" : ""}</label>
  {/if}

  {#if $errors && $errors.length > 0}
    <div>
      {#each $errors as error}
        <p class="text-error-500 text-xs">{error}</p>
      {/each}
    </div>
  {/if}

  {#if isLoading}
    <svg
        class="animate-spin h-5 w-5 text-primary-500 loading-spinner"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        data-testid="loading-spinner"
    >
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
        ></circle>
        <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        ></path>
    </svg>
  {:else}
        {#each options as opt}
        <label class="flex items-center gap-2">
            <input
            type="checkbox"
            value={opt.value}
            checked={selected.includes(opt.value)}
            on:change={() => toggle(opt.value)}
            disabled={disabled}
            />
            <span>{opt.translatedLabel ?? opt.label}</span>
        </label>
        {/each}
  {/if}

  {#if helpText}
    <p class="text-sm text-gray-500">{helpText}</p>
  {/if}

  {#each selected as val}
    <input type="hidden" name={field} value={val} />
  {/each}
</div>
