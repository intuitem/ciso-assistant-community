<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    Activity,
    ArrowLeft,
    Download,
    RefreshCw,
    Calendar,
    User
  } from 'lucide-svelte';
  import { systemGroupApi, reportsApi } from '$lib/services/rmf/api';
  import type { SystemGroup } from '$lib/services/rmf/api';

  let systemGroups: SystemGroup[] = [];
  let selectedSystemId = '';
  let dateFrom = '';
  let dateTo = '';
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
      const params: any = { systemGroupId: selectedSystemId };
      if (dateFrom) params.dateFrom = dateFrom;
      if (dateTo) params.dateTo = dateTo;

      const res = await reportsApi.getChecklistActivity(params);
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
    const blob = await reportsApi.exportReport('checklist-activity', {
      systemGroupId: selectedSystemId,
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'checklist-activity-report.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  function formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  }

  function getActionColor(action: string): string {
    switch (action?.toLowerCase()) {
      case 'create':
        return 'bg-green-100 text-green-800';
      case 'update':
        return 'bg-blue-100 text-blue-800';
      case 'delete':
        return 'bg-red-100 text-red-800';
      case 'status_change':
        return 'bg-purple-100 text-purple-800';
      case 'upload':
        return 'bg-indigo-100 text-indigo-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  onMount(() => {
    loadSystemGroups();
    // Set default date range to last 30 days
    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
    dateTo = today.toISOString().split('T')[0];
    dateFrom = thirtyDaysAgo.toISOString().split('T')[0];
  });
</script>

<svelte:head>
  <title>Checklist Activity - RMF Reports - CISO Assistant</title>
</svelte:head>

<div class="checklist-activity min-h-screen bg-gray-50">
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
            <Activity class="text-green-600" size={28} />
            Checklist Activity Report
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Track changes and updates to checklists over time
          </p>
        </div>
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
    <!-- Filters -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">System Package</label>
          <select
            bind:value={selectedSystemId}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-green-500 focus:border-green-500"
          >
            <option value="">Select a System Package</option>
            {#each systemGroups as system}
              <option value={system.id}>{system.name}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">From Date</label>
          <input
            type="date"
            bind:value={dateFrom}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-green-500 focus:border-green-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">To Date</label>
          <input
            type="date"
            bind:value={dateTo}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-green-500 focus:border-green-500"
          />
        </div>
        <div class="flex items-end gap-2">
          <button
            onclick={runReport}
            disabled={!selectedSystemId || loading}
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
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

    <!-- Activity Timeline -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">Activity Timeline</h2>
        {#if results.length > 0}
          <span class="text-sm text-gray-500">{results.length} activities</span>
        {/if}
      </div>

      {#if loading}
        <div class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
          <span class="ml-3 text-gray-600">Loading activity...</span>
        </div>
      {:else if results.length === 0}
        <div class="text-center py-12">
          <Activity size={48} class="mx-auto text-gray-400 mb-4" />
          <p class="text-gray-600">
            {selectedSystemId ? 'No activity found in the selected date range.' : 'Select a system package and date range to view activity.'}
          </p>
        </div>
      {:else}
        <div class="divide-y divide-gray-200">
          {#each results as activity}
            <div class="px-6 py-4 hover:bg-gray-50">
              <div class="flex items-start gap-4">
                <div class="flex-shrink-0 mt-1">
                  <span class="px-2 py-1 text-xs rounded-full {getActionColor(activity.action)}">
                    {activity.action}
                  </span>
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 text-sm">
                    <span class="font-medium text-gray-900">{activity.checklistName || activity.hostname}</span>
                    {#if activity.vulnId}
                      <span class="text-gray-500">-</span>
                      <span class="font-mono text-gray-600">{activity.vulnId}</span>
                    {/if}
                  </div>
                  {#if activity.description}
                    <p class="text-sm text-gray-600 mt-1">{activity.description}</p>
                  {/if}
                  {#if activity.oldValue && activity.newValue}
                    <p class="text-xs text-gray-500 mt-1">
                      Changed from <span class="font-medium">{activity.oldValue}</span> to <span class="font-medium">{activity.newValue}</span>
                    </p>
                  {/if}
                </div>
                <div class="flex-shrink-0 text-right">
                  <div class="flex items-center gap-1 text-xs text-gray-500">
                    <Calendar size={12} />
                    {formatDate(activity.timestamp)}
                  </div>
                  <div class="flex items-center gap-1 text-xs text-gray-500 mt-1">
                    <User size={12} />
                    {activity.username || 'System'}
                  </div>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>
