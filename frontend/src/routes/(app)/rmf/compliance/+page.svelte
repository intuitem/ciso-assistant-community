<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    Shield,
    Play,
    Download,
    FileSpreadsheet,
    RefreshCw,
    CheckCircle,
    XCircle,
    AlertTriangle,
    MinusCircle,
    ChevronDown,
    ChevronRight
  } from 'lucide-svelte';
  import { systemGroupApi, complianceApi } from '$lib/services/rmf/api';
  import type { SystemGroup, ComplianceResult } from '$lib/services/rmf/api';

  let systemGroups: SystemGroup[] = [];
  let selectedSystemId = '';
  let impactLevel = 'moderate';
  let includePrivacy = false;
  let loading = false;
  let generating = false;
  let results: ComplianceResult[] = [];
  let expandedFamilies: Set<string> = new Set();

  // Group results by family
  $: groupedResults = results.reduce((acc, result) => {
    if (!acc[result.controlFamily]) {
      acc[result.controlFamily] = [];
    }
    acc[result.controlFamily].push(result);
    return acc;
  }, {} as Record<string, ComplianceResult[]>);

  // Summary stats
  $: summaryStats = {
    compliant: results.filter((r) => r.status === 'compliant').length,
    nonCompliant: results.filter((r) => r.status === 'non_compliant').length,
    partiallyCompliant: results.filter((r) => r.status === 'partially_compliant').length,
    notApplicable: results.filter((r) => r.status === 'not_applicable').length,
    total: results.length
  };

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

  async function loadExistingResults() {
    if (!selectedSystemId) return;
    loading = true;
    try {
      const res = await complianceApi.getResults(selectedSystemId);
      if (res.success) {
        results = res.results || [];
      }
    } catch (error) {
      console.error('Error loading results:', error);
    } finally {
      loading = false;
    }
  }

  async function generateCompliance() {
    if (!selectedSystemId) return;
    generating = true;

    try {
      const res = await complianceApi.generate(selectedSystemId, impactLevel, includePrivacy);
      if (res.success && res.data.job_id) {
        // Poll for completion
        let attempts = 0;
        const maxAttempts = 60;
        const pollInterval = setInterval(async () => {
          attempts++;
          const statusRes = await complianceApi.getStatus(res.data.job_id);
          if (statusRes.success) {
            if (statusRes.data.status === 'completed' && statusRes.data.results) {
              results = statusRes.data.results;
              clearInterval(pollInterval);
              generating = false;
            } else if (statusRes.data.status === 'failed' || attempts >= maxAttempts) {
              clearInterval(pollInterval);
              generating = false;
              console.error('Compliance generation failed');
            }
          }
        }, 2000);
      }
    } catch (error) {
      console.error('Error generating compliance:', error);
      generating = false;
    }
  }

  async function exportXlsx() {
    if (!selectedSystemId) return;
    const blob = await complianceApi.exportXlsx(selectedSystemId);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'compliance-report.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  function toggleFamily(family: string) {
    if (expandedFamilies.has(family)) {
      expandedFamilies.delete(family);
    } else {
      expandedFamilies.add(family);
    }
    expandedFamilies = new Set(expandedFamilies);
  }

  function getStatusIcon(status: string) {
    switch (status) {
      case 'compliant':
        return CheckCircle;
      case 'non_compliant':
        return XCircle;
      case 'partially_compliant':
        return AlertTriangle;
      case 'not_applicable':
        return MinusCircle;
      default:
        return MinusCircle;
    }
  }

  function getStatusColor(status: string) {
    switch (status) {
      case 'compliant':
        return 'text-green-600 bg-green-50';
      case 'non_compliant':
        return 'text-red-600 bg-red-50';
      case 'partially_compliant':
        return 'text-yellow-600 bg-yellow-50';
      case 'not_applicable':
        return 'text-gray-600 bg-gray-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  }

  $: if (selectedSystemId) {
    loadExistingResults();
  }

  onMount(() => {
    loadSystemGroups();
  });
</script>

<svelte:head>
  <title>RMF Compliance - CISO Assistant</title>
</svelte:head>

<div class="rmf-compliance min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Shield class="text-indigo-600" size={28} />
            RMF Compliance
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Generate and view compliance reports based on NIST 800-53 controls
          </p>
        </div>
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
    <!-- Configuration Card -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Compliance Configuration</h2>
      </div>
      <div class="p-6">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">System Package</label>
            <select
              bind:value={selectedSystemId}
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">Select a System Package</option>
              {#each systemGroups as system}
                <option value={system.id}>{system.name}</option>
              {/each}
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Impact Level</label>
            <select
              bind:value={impactLevel}
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="low">Low</option>
              <option value="moderate">Moderate</option>
              <option value="high">High</option>
            </select>
          </div>

          <div class="flex items-end">
            <label class="inline-flex items-center">
              <input
                type="checkbox"
                bind:checked={includePrivacy}
                class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span class="ml-2 text-sm text-gray-700">Include Privacy Controls</span>
            </label>
          </div>

          <div class="flex items-end gap-2">
            <button
              onclick={generateCompliance}
              disabled={!selectedSystemId || generating}
              class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
            >
              {#if generating}
                <RefreshCw size={16} class="mr-2 animate-spin" />
                Generating...
              {:else}
                <Play size={16} class="mr-2" />
                Generate
              {/if}
            </button>
            <button
              onclick={exportXlsx}
              disabled={results.length === 0}
              class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              <FileSpreadsheet size={16} class="mr-2" />
              Export
            </button>
          </div>
        </div>
      </div>
    </div>

    {#if results.length > 0}
      <!-- Summary Cards -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-center">
          <p class="text-3xl font-bold text-gray-900">{summaryStats.total}</p>
          <p class="text-sm text-gray-600">Total Controls</p>
        </div>
        <div class="bg-green-50 rounded-lg border border-green-200 p-4 text-center">
          <p class="text-3xl font-bold text-green-600">{summaryStats.compliant}</p>
          <p class="text-sm text-green-700">Compliant</p>
        </div>
        <div class="bg-red-50 rounded-lg border border-red-200 p-4 text-center">
          <p class="text-3xl font-bold text-red-600">{summaryStats.nonCompliant}</p>
          <p class="text-sm text-red-700">Non-Compliant</p>
        </div>
        <div class="bg-yellow-50 rounded-lg border border-yellow-200 p-4 text-center">
          <p class="text-3xl font-bold text-yellow-600">{summaryStats.partiallyCompliant}</p>
          <p class="text-sm text-yellow-700">Partial</p>
        </div>
        <div class="bg-gray-50 rounded-lg border border-gray-200 p-4 text-center">
          <p class="text-3xl font-bold text-gray-600">{summaryStats.notApplicable}</p>
          <p class="text-sm text-gray-700">N/A</p>
        </div>
      </div>

      <!-- Results Table -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Compliance Details</h2>
        </div>
        <div class="divide-y divide-gray-200">
          {#each Object.entries(groupedResults) as [family, controls]}
            <div>
              <button
                onclick={() => toggleFamily(family)}
                class="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
              >
                <div class="flex items-center gap-3">
                  {#if expandedFamilies.has(family)}
                    <ChevronDown size={20} class="text-gray-400" />
                  {:else}
                    <ChevronRight size={20} class="text-gray-400" />
                  {/if}
                  <span class="font-semibold text-gray-900">{family}</span>
                  <span class="text-sm text-gray-500">({controls.length} controls)</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                    {controls.filter((c) => c.status === 'compliant').length} compliant
                  </span>
                  <span class="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">
                    {controls.filter((c) => c.status === 'non_compliant').length} non-compliant
                  </span>
                </div>
              </button>

              {#if expandedFamilies.has(family)}
                <div class="bg-gray-50 px-6 py-4">
                  <table class="min-w-full">
                    <thead>
                      <tr class="text-xs text-gray-500 uppercase">
                        <th class="text-left py-2">Control</th>
                        <th class="text-left py-2">Title</th>
                        <th class="text-center py-2">Checklists</th>
                        <th class="text-center py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                      {#each controls as control}
                        <tr class="hover:bg-white">
                          <td class="py-3 font-mono text-sm">{control.controlNumber}</td>
                          <td class="py-3 text-sm text-gray-900">{control.controlTitle}</td>
                          <td class="py-3 text-center text-sm text-gray-600">{control.checklistCount}</td>
                          <td class="py-3 text-center">
                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {getStatusColor(control.status)}">
                              <svelte:component this={getStatusIcon(control.status)} size={12} class="mr-1" />
                              {control.status.replace('_', ' ')}
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
      </div>
    {:else if loading}
      <div class="flex items-center justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <span class="ml-3 text-gray-600">Loading compliance data...</span>
      </div>
    {:else if selectedSystemId}
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <Shield size={48} class="mx-auto text-gray-400 mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">No Compliance Data</h3>
        <p class="text-gray-600 mb-4">
          Click "Generate" to create a compliance report for this system package.
        </p>
      </div>
    {:else}
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <Shield size={48} class="mx-auto text-gray-400 mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">Select a System Package</h3>
        <p class="text-gray-600">
          Choose a system package to view or generate compliance reports.
        </p>
      </div>
    {/if}
  </div>
</div>
