<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    Plus,
    Search,
    Filter,
    Upload,
    FileText,
    Eye,
    Edit,
    Archive,
    BarChart3,
    CheckCircle,
    AlertTriangle,
    Clock
  } from 'lucide-svelte';

  import type { StigChecklist } from '$lib/services/rmf/api';
  import { stigChecklistApi } from '$lib/services/rmf/api';
  import CklUploadModal from '$lib/components/rmf/CklUploadModal.svelte';

  let checklists: StigChecklist[] = [];
  let loading = true;
  let searchQuery = '';
  let lifecycleFilter = '';
  let stigTypeFilter = '';

  let showUploadModal = false;
  let selectedSystemId: string | null = null;

  async function loadChecklists() {
    loading = true;
    try {
      const response = await stigChecklistApi.list({
        search: searchQuery || undefined,
        lifecycle_state: lifecycleFilter || undefined,
        stig_type: stigTypeFilter || undefined
      });

      if (response.success) {
        checklists = response.data.results || [];
      }
    } catch (error) {
      console.error('Error loading checklists:', error);
    } finally {
      loading = false;
    }
  }

  async function handleActivateChecklist(checklistId: string) {
    try {
      const response = await stigChecklistApi.activate(checklistId);
      if (response.success) {
        await loadChecklists(); // Reload the list
      }
    } catch (error) {
      console.error('Error activating checklist:', error);
    }
  }

  async function handleArchiveChecklist(checklistId: string) {
    try {
      const response = await stigChecklistApi.archive(checklistId);
      if (response.success) {
        await loadChecklists(); // Reload the list
      }
    } catch (error) {
      console.error('Error archiving checklist:', error);
    }
  }

  function handleUploadComplete(event: CustomEvent<{ checklist: StigChecklist }>) {
    // Add the new checklist to the list
    checklists = [event.detail.checklist, ...checklists];
    showUploadModal = false;
  }

  function getStatusIcon(status: string) {
    switch (status) {
      case 'active':
        return CheckCircle;
      case 'draft':
        return Clock;
      case 'archived':
        return Archive;
      default:
        return Clock;
    }
  }

  function getStatusColor(status: string) {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-50';
      case 'draft':
        return 'text-yellow-600 bg-yellow-50';
      case 'archived':
        return 'text-gray-600 bg-gray-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  }

  onMount(async () => {
    await loadChecklists();
  });

  // Reactive search and filter
  $: if (searchQuery !== undefined || lifecycleFilter !== undefined || stigTypeFilter !== undefined) {
    loadChecklists();
  }
</script>

<svelte:head>
  <title>RMF STIG Checklists - CISO Assistant</title>
</svelte:head>

<div class="rmf-checklists">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="py-6">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">RMF STIG Checklists</h1>
            <p class="mt-1 text-sm text-gray-600">
              Import, manage, and analyze STIG checklists from your SCAP tools
            </p>
          </div>
          <div class="flex items-center space-x-3">
            <button
              on:click={() => { selectedSystemId = null; showUploadModal = true; }}
              class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <Upload size={16} class="mr-2" />
              Upload CKL
            </button>
            <button
              on:click={() => goto('/rmf/checklists/new')}
              class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <Plus size={16} class="mr-2" />
              New Checklist
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Filters -->
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-medium text-gray-900">STIG Checklists</h2>
          <div class="flex items-center space-x-4">
            <div class="relative">
              <Search size={16} class="absolute left-3 top-3 text-gray-400" />
              <input
                type="text"
                bind:value={searchQuery}
                placeholder="Search checklists..."
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
            <select
              bind:value={stigTypeFilter}
              class="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All STIG Types</option>
              <option value="Windows Server 2019">Windows Server 2019</option>
              <option value="Windows Server 2022">Windows Server 2022</option>
              <option value="RHEL 8">RHEL 8</option>
              <option value="RHEL 9">RHEL 9</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Checklists Table -->
      <div class="overflow-x-auto">
        {#if loading}
          <div class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span class="ml-2 text-gray-600">Loading checklists...</span>
          </div>
        {:else if checklists.length === 0}
          <div class="text-center py-12">
            <FileText size={48} class="mx-auto mb-4 text-gray-400" />
            <h3 class="text-lg font-medium text-gray-900 mb-2">No checklists found</h3>
            <p class="text-gray-600 mb-4">
              Get started by uploading a CKL file from your SCAP compliance tool.
            </p>
            <button
              on:click={() => { showUploadModal = true; }}
              class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <Upload size={16} class="mr-2" />
              Upload CKL File
            </button>
          </div>
        {:else}
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Hostname
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  STIG Type
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Version
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  System Group
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Updated
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {#each checklists as checklist}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">
                      {checklist.assetHostname || checklist.hostName}
                    </div>
                    {#if checklist.assetIpAddresses && checklist.assetIpAddresses.length > 0}
                      <div class="text-xs text-gray-500">
                        {checklist.assetIpAddresses.slice(0, 2).join(', ')}
                        {#if checklist.assetIpAddresses.length > 2}
                          +{checklist.assetIpAddresses.length - 2} more
                        {/if}
                      </div>
                    {/if}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">{checklist.stigType}</div>
                    <div class="text-xs text-gray-500">{checklist.stigRelease}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {checklist.version}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusColor(checklist.lifecycle_state)}">
                      <svelte:component this={getStatusIcon(checklist.lifecycle_state)} size={12} class="mr-1" />
                      {checklist.lifecycle_state}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {checklist.systemGroupId ? 'Assigned' : 'Unassigned'}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(checklist.updated_at).toLocaleDateString()}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div class="flex items-center justify-end space-x-2">
                      <button
                        on:click={() => goto(`/rmf/checklists/${checklist.id}`)}
                        class="text-blue-600 hover:text-blue-900"
                        title="View Details"
                      >
                        <Eye size={16} />
                      </button>
                      <button
                        on:click={() => goto(`/rmf/checklists/${checklist.id}/edit`)}
                        class="text-gray-600 hover:text-gray-900"
                        title="Edit"
                      >
                        <Edit size={16} />
                      </button>
                      {#if checklist.lifecycle_state === 'draft'}
                        <button
                          on:click={() => handleActivateChecklist(checklist.id)}
                          class="text-green-600 hover:text-green-900"
                          title="Activate"
                        >
                          <CheckCircle size={16} />
                        </button>
                      {:else if checklist.lifecycle_state === 'active'}
                        <button
                          on:click={() => handleArchiveChecklist(checklist.id)}
                          class="text-orange-600 hover:text-orange-900"
                          title="Archive"
                        >
                          <Archive size={16} />
                        </button>
                      {/if}
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </div>
  </div>
</div>

<!-- Upload Modal -->
<CklUploadModal
  bind:show={showUploadModal}
  systemGroupId={selectedSystemId}
  on:uploadComplete={handleUploadComplete}
  on:close={() => { showUploadModal = false; selectedSystemId = null; }}
/>
