<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    Server,
    ArrowLeft,
    Download,
    RefreshCw,
    ChevronDown,
    ChevronRight
  } from 'lucide-svelte';
  import { systemGroupApi, reportsApi, cciApi } from '$lib/services/rmf/api';
  import type { SystemGroup } from '$lib/services/rmf/api';

  let systemGroups: SystemGroup[] = [];
  let selectedSystemId = '';
  let controlId = '';
  let loading = false;
  let results: any[] = [];
  let expandedRows: Set<number> = new Set();
  let cciSuggestions: string[] = [];

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

  async function searchCci() {
    if (controlId.length < 3) {
      cciSuggestions = [];
      return;
    }
    try {
      const res = await cciApi.search(controlId);
      if (res.success) {
        cciSuggestions = res.data.slice(0, 10).map((c: any) => c.cciId);
      }
    } catch (error) {
      cciSuggestions = [];
    }
  }

  async function runReport() {
    if (!selectedSystemId) return;

    loading = true;
    try {
      const params: any = { systemGroupId: selectedSystemId };
      if (controlId) params.controlId = controlId;

      const res = await reportsApi.getHostByControl(params);
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
    const blob = await reportsApi.exportReport('host-by-control', {
      systemGroupId: selectedSystemId,
      controlId: controlId || undefined
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'host-by-control-report.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  function toggleRow(index: number) {
    if (expandedRows.has(index)) {
      expandedRows.delete(index);
    } else {
      expandedRows.add(index);
    }
    expandedRows = new Set(expandedRows);
  }

  function getStatusColor(status: string): string {
    switch (status?.toLowerCase()) {
      case 'open':
        return 'bg-red-100 text-red-800';
      case 'not_a_finding':
      case 'notafinding':
        return 'bg-green-100 text-green-800';
      case 'not_applicable':
        return 'bg-gray-100 text-gray-800';
      case 'not_reviewed':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  onMount(() => {
    loadSystemGroups();
  });
</script>

<svelte:head>
  <title>Host by Control - RMF Reports - CISO Assistant</title>
</svelte:head>

<div class="host-by-control min-h-screen bg-gray-50">
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
            <Server class="text-cyan-600" size={28} />
            Host by Control Report
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Find all hosts affected by a specific NIST control or CCI
          </p>
        </div>
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
    <!-- Filters -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">System Package</label>
          <select
            bind:value={selectedSystemId}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-cyan-500 focus:border-cyan-500"
          >
            <option value="">Select a System Package</option>
            {#each systemGroups as system}
              <option value={system.id}>{system.name}</option>
            {/each}
          </select>
        </div>
        <div class="relative">
          <label class="block text-sm font-medium text-gray-700 mb-2">Control/CCI ID</label>
          <input
            type="text"
            bind:value={controlId}
            oninput={searchCci}
            placeholder="e.g., CCI-000001 or AC-1"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-cyan-500 focus:border-cyan-500"
          />
          {#if cciSuggestions.length > 0}
            <div class="absolute z-10 w-full bg-white border border-gray-200 rounded-md shadow-lg mt-1 max-h-48 overflow-auto">
              {#each cciSuggestions as suggestion}
                <button
                  onclick={() => { controlId = suggestion; cciSuggestions = []; }}
                  class="w-full text-left px-3 py-2 hover:bg-gray-100 text-sm"
                >
                  {suggestion}
                </button>
              {/each}
            </div>
          {/if}
          <p class="text-xs text-gray-500 mt-1">Search by CCI ID or NIST control</p>
        </div>
        <div class="flex items-end gap-2">
          <button
            onclick={runReport}
            disabled={!selectedSystemId || loading}
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50"
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

    <!-- Results -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">Hosts by Control</h2>
        {#if results.length > 0}
          <span class="text-sm text-gray-500">{results.length} controls with findings</span>
        {/if}
      </div>

      {#if loading}
        <div class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-600"></div>
          <span class="ml-3 text-gray-600">Loading report...</span>
        </div>
      {:else if results.length === 0}
        <div class="text-center py-12">
          <Server size={48} class="mx-auto text-gray-400 mb-4" />
          <p class="text-gray-600">
            {selectedSystemId ? 'No results found for the specified control.' : 'Select a system package and optionally a control to run the report.'}
          </p>
        </div>
      {:else}
        <div class="divide-y divide-gray-200">
          {#each results as control, i}
            <div>
              <button
                onclick={() => toggleRow(i)}
                class="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
              >
                <div class="flex items-center gap-4">
                  {#if expandedRows.has(i)}
                    <ChevronDown size={20} class="text-gray-400" />
                  {:else}
                    <ChevronRight size={20} class="text-gray-400" />
                  {/if}
                  <div class="text-left">
                    <p class="font-medium text-gray-900">{control.controlId}</p>
                    <p class="text-sm text-gray-600">{control.controlTitle || ''}</p>
                  </div>
                </div>
                <div class="flex items-center gap-4">
                  <span class="text-sm text-gray-500">{control.hosts?.length || 0} hosts</span>
                  <span class="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">
                    {control.openCount || 0} Open
                  </span>
                </div>
              </button>
              {#if expandedRows.has(i)}
                <div class="px-6 pb-4 bg-gray-50">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead>
                      <tr class="text-xs text-gray-500 uppercase">
                        <th class="px-4 py-2 text-left">Host Name</th>
                        <th class="px-4 py-2 text-left">Vuln ID</th>
                        <th class="px-4 py-2 text-left">STIG Title</th>
                        <th class="px-4 py-2 text-left">Status</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200 bg-white">
                      {#each control.hosts || [] as host}
                        <tr class="hover:bg-gray-50">
                          <td class="px-4 py-3 text-sm font-medium text-gray-900">{host.hostname}</td>
                          <td class="px-4 py-3 text-sm font-mono text-gray-600">{host.vulnId}</td>
                          <td class="px-4 py-3 text-sm text-gray-600">{host.stigTitle || '-'}</td>
                          <td class="px-4 py-3">
                            <span class="px-2 py-1 text-xs rounded-full {getStatusColor(host.status)}">
                              {host.status}
                            </span>
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>
