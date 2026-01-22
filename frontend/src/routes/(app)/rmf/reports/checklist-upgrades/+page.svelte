<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    ArrowUpCircle,
    ArrowLeft,
    Download,
    RefreshCw,
    AlertCircle
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
      const res = await reportsApi.getChecklistUpgrades({ systemGroupId: selectedSystemId });
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
    const blob = await reportsApi.exportReport('checklist-upgrades', {
      systemGroupId: selectedSystemId
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'checklist-upgrades-report.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  function getUpgradeStatusColor(status: string): string {
    switch (status?.toLowerCase()) {
      case 'upgrade_available':
        return 'bg-yellow-100 text-yellow-800';
      case 'current':
        return 'bg-green-100 text-green-800';
      case 'deprecated':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  onMount(() => {
    loadSystemGroups();
  });
</script>

<svelte:head>
  <title>Checklist Upgrades - RMF Reports - CISO Assistant</title>
</svelte:head>

<div class="checklist-upgrades min-h-screen bg-gray-50">
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
            <ArrowUpCircle class="text-yellow-600" size={28} />
            Checklist Upgrades Report
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Identify checklists that have newer STIG versions available
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
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-yellow-500 focus:border-yellow-500"
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
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50"
          >
            {#if loading}
              <RefreshCw size={16} class="mr-2 animate-spin" />
              Loading...
            {:else}
              Check for Upgrades
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

    <!-- Summary Cards -->
    {#if results.length > 0}
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-green-50 rounded-lg border border-green-200 p-4 text-center">
          <p class="text-3xl font-bold text-green-600">
            {results.filter(r => r.upgradeStatus === 'current').length}
          </p>
          <p class="text-sm text-green-700">Up to Date</p>
        </div>
        <div class="bg-yellow-50 rounded-lg border border-yellow-200 p-4 text-center">
          <p class="text-3xl font-bold text-yellow-600">
            {results.filter(r => r.upgradeStatus === 'upgrade_available').length}
          </p>
          <p class="text-sm text-yellow-700">Upgrades Available</p>
        </div>
        <div class="bg-red-50 rounded-lg border border-red-200 p-4 text-center">
          <p class="text-3xl font-bold text-red-600">
            {results.filter(r => r.upgradeStatus === 'deprecated').length}
          </p>
          <p class="text-sm text-red-700">Deprecated</p>
        </div>
      </div>
    {/if}

    <!-- Results Table -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Upgrade Status</h2>
      </div>

      {#if loading}
        <div class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-600"></div>
          <span class="ml-3 text-gray-600">Checking for upgrades...</span>
        </div>
      {:else if results.length === 0}
        <div class="text-center py-12">
          <ArrowUpCircle size={48} class="mx-auto text-gray-400 mb-4" />
          <p class="text-gray-600">
            {selectedSystemId ? 'No checklists found.' : 'Select a system package to check for available upgrades.'}
          </p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Host Name</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">STIG Title</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Current Version</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Latest Version</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Notes</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              {#each results as checklist}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4 text-sm font-medium text-gray-900">{checklist.hostname || '-'}</td>
                  <td class="px-6 py-4 text-sm text-gray-600">{checklist.stigTitle || '-'}</td>
                  <td class="px-6 py-4 text-sm text-gray-600">
                    V{checklist.currentVersion}R{checklist.currentRelease}
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-600">
                    {#if checklist.latestVersion}
                      V{checklist.latestVersion}R{checklist.latestRelease}
                    {:else}
                      -
                    {/if}
                  </td>
                  <td class="px-6 py-4">
                    <span class="px-2 py-1 text-xs rounded-full {getUpgradeStatusColor(checklist.upgradeStatus)}">
                      {#if checklist.upgradeStatus === 'upgrade_available'}
                        Upgrade Available
                      {:else if checklist.upgradeStatus === 'current'}
                        Current
                      {:else if checklist.upgradeStatus === 'deprecated'}
                        Deprecated
                      {:else}
                        Unknown
                      {/if}
                    </span>
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-600">
                    {#if checklist.upgradeStatus === 'upgrade_available'}
                      <span class="flex items-center gap-1 text-yellow-600">
                        <AlertCircle size={14} />
                        {checklist.versionsBehind || 1} version(s) behind
                      </span>
                    {:else if checklist.upgradeStatus === 'deprecated'}
                      <span class="text-red-600">STIG has been retired</span>
                    {:else}
                      -
                    {/if}
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
