<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    FileText,
    ArrowLeft,
    Download,
    RefreshCw,
    ExternalLink
  } from 'lucide-svelte';
  import { systemGroupApi, reportsApi } from '$lib/services/rmf/api';
  import type { SystemGroup } from '$lib/services/rmf/api';

  let systemGroups: SystemGroup[] = [];
  let selectedSystemId = '';
  let loading = false;
  let results: any[] = [];

  async function loadSystemGroups() {
    try {
      const res = await systemGroupApi.list({ lifecycle_state: 'active' });
      if (res.success) {
        systemGroups = res.results || [];
      }
    } catch (error) {
      console.error('Error loading systems:', error);
    }
  }

  async function runReport() {
    if (!selectedSystemId) return;

    loading = true;
    try {
      const res = await reportsApi.getChecklistListing({ systemGroupId: selectedSystemId });
      if (res.success) {
        results = res.data.results || [];
      }
    } catch (error) {
      console.error('Error running report:', error);
    } finally {
      loading = false;
    }
  }

  async function exportReport() {
    const blob = await reportsApi.exportReport('checklist-listing', {
      systemGroupId: selectedSystemId
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'checklist-listing-report.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  function getStatusColor(status: string): string {
    switch (status?.toLowerCase()) {
      case 'complete':
        return 'bg-green-100 text-green-800';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      case 'not_started':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  onMount(() => {
    loadSystemGroups();
  });
</script>

<svelte:head>
  <title>Checklist Listing - RMF Reports - CISO Assistant</title>
</svelte:head>

<div class="checklist-listing min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex items-center gap-4">
        <button
          onclick={() => goto('/rmf/reports')}
          class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 class="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileText class="text-blue-600" size={28} />
            Checklist Listing Report
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Complete listing of all checklists in a system package
          </p>
        </div>
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
    <!-- Filters -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex items-center gap-4">
        <div class="flex-1 max-w-md">
          <label class="block text-sm font-medium text-gray-700 mb-2">System Package</label>
          <select
            bind:value={selectedSystemId}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Select a System Package</option>
            {#each systemGroups as system}
              <option value={system.id}>{system.name}</option>
            {/each}
          </select>
        </div>
        <div class="flex items-end gap-2">
          <button
            onclick={runReport}
            disabled={!selectedSystemId || loading}
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {#if loading}
              <RefreshCw size={16} class="mr-2 animate-spin" />
              Loading...
            {:else}
              Run Report
            {/if}
          </button>
          {#if results.length > 0}
            <button
              onclick={exportReport}
              class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <Download size={16} class="mr-2" />
              Export
            </button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Results Table -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">Checklists</h2>
        {#if results.length > 0}
          <span class="text-sm text-gray-500">{results.length} checklists</span>
        {/if}
      </div>

      {#if loading}
        <div class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span class="ml-3 text-gray-600">Loading report...</span>
        </div>
      {:else if results.length === 0}
        <div class="text-center py-12">
          <FileText size={48} class="mx-auto text-gray-400 mb-4" />
          <p class="text-gray-600">
            {selectedSystemId ? 'No checklists found in this system package.' : 'Select a system package and run the report.'}
          </p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Host Name</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">STIG Title</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Version</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Release</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Open</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">NaF</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">N/A</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">NR</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              {#each results as checklist}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4 text-sm font-medium text-gray-900">{checklist.hostname || '-'}</td>
                  <td class="px-6 py-4 text-sm text-gray-600">{checklist.stigTitle || '-'}</td>
                  <td class="px-6 py-4 text-sm text-gray-600">{checklist.version || '-'}</td>
                  <td class="px-6 py-4 text-sm text-gray-600">{checklist.release || '-'}</td>
                  <td class="px-6 py-4">
                    <span class="px-2 py-1 text-xs rounded-full {getStatusColor(checklist.status)}">
                      {checklist.status || 'Unknown'}
                    </span>
                  </td>
                  <td class="px-6 py-4 text-sm text-red-600 font-medium">{checklist.openCount || 0}</td>
                  <td class="px-6 py-4 text-sm text-green-600">{checklist.nafCount || 0}</td>
                  <td class="px-6 py-4 text-sm text-gray-600">{checklist.naCount || 0}</td>
                  <td class="px-6 py-4 text-sm text-blue-600">{checklist.nrCount || 0}</td>
                  <td class="px-6 py-4">
                    <button
                      onclick={() => goto(`/rmf/checklists/${checklist.id}`)}
                      class="text-blue-600 hover:text-blue-800"
                      title="View Checklist"
                    >
                      <ExternalLink size={16} />
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </div>
</div>
