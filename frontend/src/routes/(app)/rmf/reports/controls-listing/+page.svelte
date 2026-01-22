<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    ClipboardList,
    ArrowLeft,
    Download,
    RefreshCw,
    Filter
  } from 'lucide-svelte';
  import { systemGroupApi, reportsApi } from '$lib/services/rmf/api';
  import type { SystemGroup } from '$lib/services/rmf/api';

  let systemGroups: SystemGroup[] = [];
  let selectedSystemId = '';
  let controlFamily = '';
  let statusFilter = '';
  let loading = false;
  let results: any[] = [];

  const controlFamilies = [
    { value: '', label: 'All Families' },
    { value: 'AC', label: 'AC - Access Control' },
    { value: 'AT', label: 'AT - Awareness and Training' },
    { value: 'AU', label: 'AU - Audit and Accountability' },
    { value: 'CA', label: 'CA - Assessment, Authorization, and Monitoring' },
    { value: 'CM', label: 'CM - Configuration Management' },
    { value: 'CP', label: 'CP - Contingency Planning' },
    { value: 'IA', label: 'IA - Identification and Authentication' },
    { value: 'IR', label: 'IR - Incident Response' },
    { value: 'MA', label: 'MA - Maintenance' },
    { value: 'MP', label: 'MP - Media Protection' },
    { value: 'PE', label: 'PE - Physical and Environmental Protection' },
    { value: 'PL', label: 'PL - Planning' },
    { value: 'PM', label: 'PM - Program Management' },
    { value: 'PS', label: 'PS - Personnel Security' },
    { value: 'PT', label: 'PT - PII Processing and Transparency' },
    { value: 'RA', label: 'RA - Risk Assessment' },
    { value: 'SA', label: 'SA - System and Services Acquisition' },
    { value: 'SC', label: 'SC - System and Communications Protection' },
    { value: 'SI', label: 'SI - System and Information Integrity' },
    { value: 'SR', label: 'SR - Supply Chain Risk Management' }
  ];

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
      if (controlFamily) params.family = controlFamily;
      if (statusFilter) params.status = statusFilter;

      const res = await reportsApi.getControlsListing(params);
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
    const blob = await reportsApi.exportReport('controls-listing', {
      systemGroupId: selectedSystemId,
      family: controlFamily || undefined,
      status: statusFilter || undefined
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'controls-listing-report.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  function getStatusColor(status: string): string {
    switch (status?.toLowerCase()) {
      case 'implemented':
        return 'bg-green-100 text-green-800';
      case 'partially_implemented':
        return 'bg-yellow-100 text-yellow-800';
      case 'planned':
        return 'bg-blue-100 text-blue-800';
      case 'not_implemented':
        return 'bg-red-100 text-red-800';
      case 'not_applicable':
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
  <title>Controls Listing - RMF Reports - CISO Assistant</title>
</svelte:head>

<div class="controls-listing min-h-screen bg-gray-50">
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
            <ClipboardList class="text-teal-600" size={28} />
            Controls Listing Report
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Complete listing of NIST 800-53 controls and their implementation status
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
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-teal-500 focus:border-teal-500"
          >
            <option value="">Select a System Package</option>
            {#each systemGroups as system}
              <option value={system.id}>{system.name}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Control Family</label>
          <select
            bind:value={controlFamily}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-teal-500 focus:border-teal-500"
          >
            {#each controlFamilies as family}
              <option value={family.value}>{family.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Status</label>
          <select
            bind:value={statusFilter}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-teal-500 focus:border-teal-500"
          >
            <option value="">All Statuses</option>
            <option value="implemented">Implemented</option>
            <option value="partially_implemented">Partially Implemented</option>
            <option value="planned">Planned</option>
            <option value="not_implemented">Not Implemented</option>
            <option value="not_applicable">Not Applicable</option>
          </select>
        </div>
        <div class="flex items-end gap-2">
          <button
            onclick={runReport}
            disabled={!selectedSystemId || loading}
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50"
          >
            {#if loading}
              <RefreshCw size={16} class="mr-2 animate-spin" />
              Loading...
            {:else}
              <Filter size={16} class="mr-2" />
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

    <!-- Summary Cards -->
    {#if results.length > 0}
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div class="bg-green-50 rounded-lg border border-green-200 p-4 text-center">
          <p class="text-2xl font-bold text-green-600">
            {results.filter(r => r.status === 'implemented').length}
          </p>
          <p class="text-xs text-green-700">Implemented</p>
        </div>
        <div class="bg-yellow-50 rounded-lg border border-yellow-200 p-4 text-center">
          <p class="text-2xl font-bold text-yellow-600">
            {results.filter(r => r.status === 'partially_implemented').length}
          </p>
          <p class="text-xs text-yellow-700">Partial</p>
        </div>
        <div class="bg-blue-50 rounded-lg border border-blue-200 p-4 text-center">
          <p class="text-2xl font-bold text-blue-600">
            {results.filter(r => r.status === 'planned').length}
          </p>
          <p class="text-xs text-blue-700">Planned</p>
        </div>
        <div class="bg-red-50 rounded-lg border border-red-200 p-4 text-center">
          <p class="text-2xl font-bold text-red-600">
            {results.filter(r => r.status === 'not_implemented').length}
          </p>
          <p class="text-xs text-red-700">Not Implemented</p>
        </div>
        <div class="bg-gray-50 rounded-lg border border-gray-200 p-4 text-center">
          <p class="text-2xl font-bold text-gray-600">
            {results.filter(r => r.status === 'not_applicable').length}
          </p>
          <p class="text-xs text-gray-700">N/A</p>
        </div>
      </div>
    {/if}

    <!-- Results Table -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">Controls</h2>
        {#if results.length > 0}
          <span class="text-sm text-gray-500">{results.length} controls</span>
        {/if}
      </div>

      {#if loading}
        <div class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
          <span class="ml-3 text-gray-600">Loading controls...</span>
        </div>
      {:else if results.length === 0}
        <div class="text-center py-12">
          <ClipboardList size={48} class="mx-auto text-gray-400 mb-4" />
          <p class="text-gray-600">
            {selectedSystemId ? 'No controls found matching your filters.' : 'Select a system package to view controls.'}
          </p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Control ID</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Family</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Related Vulns</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Responsible</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              {#each results as control}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4 text-sm font-mono font-medium text-gray-900">{control.controlId}</td>
                  <td class="px-6 py-4 text-sm text-gray-600">{control.family}</td>
                  <td class="px-6 py-4 text-sm text-gray-600 max-w-md truncate" title={control.title}>
                    {control.title}
                  </td>
                  <td class="px-6 py-4">
                    <span class="px-2 py-1 text-xs rounded-full {getStatusColor(control.status)}">
                      {control.status?.replace('_', ' ') || 'Unknown'}
                    </span>
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-600">
                    {#if control.vulnCount > 0}
                      <span class="text-red-600 font-medium">{control.vulnCount}</span>
                    {:else}
                      <span class="text-gray-400">0</span>
                    {/if}
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-600">{control.responsible || '-'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </div>
</div>
