<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    Plus,
    Search,
    Filter,
    MoreHorizontal,
    Eye,
    Edit,
    Archive,
    BarChart3,
    CheckCircle,
    AlertTriangle
  } from 'lucide-svelte';

  import type { SystemGroup } from '$lib/services/rmf/api';
  import { systemGroupApi } from '$lib/services/rmf/api';

  let systemGroups: SystemGroup[] = [];
  let loading = true;
  let searchQuery = '';
  let lifecycleFilter = '';

  async function loadSystemGroups() {
    loading = true;
    try {
      const response = await systemGroupApi.list({
        search: searchQuery || undefined,
        lifecycle_state: lifecycleFilter || undefined
      });

      if (response.success) {
        systemGroups = response.data.results || [];
      }
    } catch (error) {
      console.error('Error loading system groups:', error);
    } finally {
      loading = false;
    }
  }

  async function handleActivateSystem(systemId: string) {
    try {
      const response = await systemGroupApi.activate(systemId);
      if (response.success) {
        await loadSystemGroups(); // Reload the list
      }
    } catch (error) {
      console.error('Error activating system:', error);
    }
  }

  async function handleArchiveSystem(systemId: string) {
    try {
      const response = await systemGroupApi.archive(systemId);
      if (response.success) {
        await loadSystemGroups(); // Reload the list
      }
    } catch (error) {
      console.error('Error archiving system:', error);
    }
  }

  function getComplianceColor(percentage: number): string {
    if (percentage >= 80) return 'text-green-600';
    if (percentage >= 60) return 'text-yellow-600';
    return 'text-red-600';
  }

  function getComplianceIcon(percentage: number) {
    if (percentage >= 80) return CheckCircle;
    return AlertTriangle;
  }

  onMount(async () => {
    await loadSystemGroups();
  });

  // Reactive search and filter
  $: if (searchQuery !== undefined || lifecycleFilter !== undefined) {
    loadSystemGroups();
  }
</script>

<svelte:head>
  <title>RMF System Groups - CISO Assistant</title>
</svelte:head>

<div class="rmf-system-groups">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="py-6">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">RMF System Groups</h1>
            <p class="mt-1 text-sm text-gray-600">
              Manage system packages and monitor compliance across your RMF environment
            </p>
          </div>
          <button
            on:click={() => goto('/rmf/system-groups/new')}
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <Plus size={16} class="mr-2" />
            New System Group
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Filters -->
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-medium text-gray-900">System Groups</h2>
          <div class="flex items-center space-x-4">
            <div class="relative">
              <Search size={16} class="absolute left-3 top-3 text-gray-400" />
              <input
                type="text"
                bind:value={searchQuery}
                placeholder="Search systems..."
                class="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <select
              bind:value={lifecycleFilter}
              class="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All States</option>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </div>
        </div>
      </div>

      <!-- System Groups Grid -->
      <div class="p-6">
        {#if loading}
          <div class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span class="ml-2 text-gray-600">Loading system groups...</span>
          </div>
        {:else if systemGroups.length === 0}
          <div class="text-center py-12">
            <BarChart3 size={48} class="mx-auto mb-4 text-gray-400" />
            <h3 class="text-lg font-medium text-gray-900 mb-2">No system groups found</h3>
            <p class="text-gray-600 mb-4">
              Get started by creating your first system group to organize your RMF checklists.
            </p>
            <button
              on:click={() => goto('/rmf/system-groups/new')}
              class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <Plus size={16} class="mr-2" />
              Create System Group
            </button>
          </div>
        {:else}
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each systemGroups as system}
              <div class="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                <div class="p-6">
                  <div class="flex items-start justify-between">
                    <div class="flex-1">
                      <h3 class="text-lg font-semibold text-gray-900 mb-1">
                        {system.name}
                      </h3>
                      <p class="text-sm text-gray-600 mb-3 line-clamp-2">
                        {system.description || 'No description provided'}
                      </p>

                      <!-- Status Badge -->
                      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        {system.lifecycle_state === 'active' ? 'bg-green-100 text-green-800' :
                          system.lifecycle_state === 'draft' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'}">
                        {system.lifecycle_state}
                      </span>
                    </div>

                    <!-- Actions Menu -->
                    <div class="relative">
                      <button class="text-gray-400 hover:text-gray-600">
                        <MoreHorizontal size={16} />
                      </button>
                    </div>
                  </div>

                  <!-- Stats -->
                  <div class="mt-4 grid grid-cols-2 gap-4">
                    <div class="text-center">
                      <div class="text-2xl font-bold text-gray-900">
                        {system.totalChecklists}
                      </div>
                      <div class="text-xs text-gray-600 uppercase tracking-wide">
                        Checklists
                      </div>
                    </div>
                    <div class="text-center">
                      <div class="text-2xl font-bold text-red-600">
                        {system.totalOpenVulnerabilities}
                      </div>
                      <div class="text-xs text-gray-600 uppercase tracking-wide">
                        Open Vulns
                      </div>
                    </div>
                  </div>

                  <!-- Compliance Indicator -->
                  {#if system.totalChecklists > 0}
                    <div class="mt-4">
                      <div class="flex items-center justify-between text-sm mb-1">
                        <span class="text-gray-600">Compliance</span>
                        <span class={getComplianceColor(system.totalChecklists > 0 ? Math.round((1 - system.totalOpenVulnerabilities / (system.totalChecklists * 10)) * 100) : 0)}>
                          {system.totalChecklists > 0 ? Math.round((1 - system.totalOpenVulnerabilities / (system.totalChecklists * 10)) * 100) : 0}%
                        </span>
                      </div>
                      <div class="w-full bg-gray-200 rounded-full h-2">
                        <div
                          class="bg-green-600 h-2 rounded-full"
                          style="width: {Math.min(100, Math.max(0, (1 - system.totalOpenVulnerabilities / (system.totalChecklists * 10)) * 100))}%"
                        ></div>
                      </div>
                    </div>
                  {/if}

                  <!-- Actions -->
                  <div class="mt-4 flex items-center justify-between">
                    <div class="flex space-x-2">
                      <button
                        on:click={() => goto(`/rmf/system-groups/${system.id}`)}
                        class="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        View
                      </button>
                      <button
                        on:click={() => goto(`/rmf/system-groups/${system.id}/edit`)}
                        class="text-gray-600 hover:text-gray-800 text-sm font-medium"
                      >
                        Edit
                      </button>
                    </div>

                    {#if system.lifecycle_state === 'draft'}
                      <button
                        on:click={() => handleActivateSystem(system.id)}
                        class="text-green-600 hover:text-green-800 text-sm font-medium"
                      >
                        Activate
                      </button>
                    {:else if system.lifecycle_state === 'active'}
                      <button
                        on:click={() => handleArchiveSystem(system.id)}
                        class="text-orange-600 hover:text-orange-800 text-sm font-medium"
                      >
                        Archive
                      </button>
                    {/if}
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
