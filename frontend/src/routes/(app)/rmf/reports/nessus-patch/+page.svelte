<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    Shield,
    ArrowLeft,
    Download,
    RefreshCw,
    AlertTriangle,
    ExternalLink
  } from 'lucide-svelte';
  import { systemGroupApi, reportsApi } from '$lib/services/rmf/api';
  import type { SystemGroup } from '$lib/services/rmf/api';

  let systemGroups: SystemGroup[] = [];
  let selectedSystemId = '';
  let severityFilter = '';
  let loading = false;
  let results: any[] = [];
  let summary: any = null;

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
      if (severityFilter) params.severity = severityFilter;

      const res = await reportsApi.getNessusPatch(params);
      if (res.success) {
        results = res.data.results || [];
        summary = res.data.summary || null;
      }
    } catch (error) {
      console.error('Error running report:', error);
    } finally {
      loading = false;
    }
  }

  async function exportReport() {
    const blob = await reportsApi.exportReport('nessus-patch', {
      systemGroupId: selectedSystemId,
      severity: severityFilter || undefined
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'nessus-patch-report.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  function getSeverityColor(severity: string): string {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'bg-purple-100 text-purple-800';
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-orange-100 text-orange-800';
      case 'low':
        return 'bg-yellow-100 text-yellow-800';
      case 'info':
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
  <title>Nessus Patch Report - RMF Reports - CISO Assistant</title>
</svelte:head>

<div class="nessus-patch min-h-screen bg-gray-50">
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
            <Shield class="text-pink-600" size={28} />
            Nessus/ACAS Patch Report
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Missing patches and vulnerabilities from Nessus scans
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
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-pink-500 focus:border-pink-500"
          >
            <option value="">Select a System Package</option>
            {#each systemGroups as system}
              <option value={system.id}>{system.name}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Severity</label>
          <select
            bind:value={severityFilter}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-pink-500 focus:border-pink-500"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>
        </div>
        <div class="flex items-end gap-2">
          <button
            onclick={runReport}
            disabled={!selectedSystemId || loading}
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-pink-600 hover:bg-pink-700 disabled:opacity-50"
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

    <!-- Summary Cards -->
    {#if summary}
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div class="bg-purple-50 rounded-lg border border-purple-200 p-4 text-center">
          <p class="text-2xl font-bold text-purple-600">{summary.critical || 0}</p>
          <p class="text-xs text-purple-700">Critical</p>
        </div>
        <div class="bg-red-50 rounded-lg border border-red-200 p-4 text-center">
          <p class="text-2xl font-bold text-red-600">{summary.high || 0}</p>
          <p class="text-xs text-red-700">High</p>
        </div>
        <div class="bg-orange-50 rounded-lg border border-orange-200 p-4 text-center">
          <p class="text-2xl font-bold text-orange-600">{summary.medium || 0}</p>
          <p class="text-xs text-orange-700">Medium</p>
        </div>
        <div class="bg-yellow-50 rounded-lg border border-yellow-200 p-4 text-center">
          <p class="text-2xl font-bold text-yellow-600">{summary.low || 0}</p>
          <p class="text-xs text-yellow-700">Low</p>
        </div>
        <div class="bg-blue-50 rounded-lg border border-blue-200 p-4 text-center">
          <p class="text-2xl font-bold text-blue-600">{summary.info || 0}</p>
          <p class="text-xs text-blue-700">Info</p>
        </div>
      </div>
    {/if}

    <!-- Results Table -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">Vulnerability Findings</h2>
        {#if results.length > 0}
          <span class="text-sm text-gray-500">{results.length} findings</span>
        {/if}
      </div>

      {#if loading}
        <div class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-600"></div>
          <span class="ml-3 text-gray-600">Loading patch report...</span>
        </div>
      {:else if results.length === 0}
        <div class="text-center py-12">
          <Shield size={48} class="mx-auto text-gray-400 mb-4" />
          <p class="text-gray-600">
            {selectedSystemId ? 'No Nessus findings found for this system.' : 'Select a system package to view Nessus patch findings.'}
          </p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plugin ID</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plugin Name</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">CVSS</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Host</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Port</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">CVE</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              {#each results as finding}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4 text-sm font-mono text-gray-900">{finding.pluginId}</td>
                  <td class="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" title={finding.pluginName}>
                    {finding.pluginName}
                  </td>
                  <td class="px-6 py-4">
                    <span class="px-2 py-1 text-xs rounded-full {getSeverityColor(finding.severity)}">
                      {finding.severity}
                    </span>
                  </td>
                  <td class="px-6 py-4 text-sm">
                    {#if finding.cvssScore}
                      <span class="font-medium" class:text-purple-600={finding.cvssScore >= 9} class:text-red-600={finding.cvssScore >= 7 && finding.cvssScore < 9} class:text-orange-600={finding.cvssScore >= 4 && finding.cvssScore < 7} class:text-yellow-600={finding.cvssScore < 4}>
                        {finding.cvssScore.toFixed(1)}
                      </span>
                    {:else}
                      <span class="text-gray-400">-</span>
                    {/if}
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-600">{finding.hostname || finding.ipAddress}</td>
                  <td class="px-6 py-4 text-sm text-gray-600">{finding.port || '-'}</td>
                  <td class="px-6 py-4 text-sm">
                    {#if finding.cve}
                      <a
                        href="https://nvd.nist.gov/vuln/detail/{finding.cve}"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                      >
                        {finding.cve}
                        <ExternalLink size={12} />
                      </a>
                    {:else}
                      <span class="text-gray-400">-</span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>

    <!-- Alert for Critical/High -->
    {#if summary && (summary.critical > 0 || summary.high > 0)}
      <div class="bg-red-50 border border-red-200 rounded-lg p-4">
        <div class="flex items-start gap-3">
          <AlertTriangle class="text-red-600 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <h3 class="font-medium text-red-900">Action Required</h3>
            <p class="text-sm text-red-700 mt-1">
              There are {summary.critical || 0} critical and {summary.high || 0} high severity findings that require immediate attention.
              These vulnerabilities pose significant risk and should be prioritized for remediation.
            </p>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>
