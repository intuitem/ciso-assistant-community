<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    BarChart3,
    PieChart,
    FileText,
    AlertTriangle,
    Server,
    Shield,
    Activity,
    RefreshCw,
    ChevronRight,
    FileSpreadsheet,
    Download
  } from 'lucide-svelte';
  import { systemGroupApi, reportsApi } from '$lib/services/rmf/api';
  import type { SystemGroup } from '$lib/services/rmf/api';

  let systemGroups: SystemGroup[] = [];
  let loading = true;

  const reports = [
    {
      id: 'nessus-patch',
      title: 'Nessus Patch Listing',
      description: 'View Nessus/ACAS patch vulnerabilities by system',
      icon: AlertTriangle,
      color: 'text-red-600 bg-red-50',
      href: '/rmf/reports/nessus-patch'
    },
    {
      id: 'system-charts',
      title: 'System Package Pie Charts',
      description: 'Visual breakdown of vulnerabilities by category and status',
      icon: PieChart,
      color: 'text-indigo-600 bg-indigo-50',
      href: '/rmf/reports/system-charts'
    },
    {
      id: 'checklist-listing',
      title: 'System Package Checklist Listing',
      description: 'Complete list of checklists with scores',
      icon: FileText,
      color: 'text-green-600 bg-green-50',
      href: '/rmf/reports/checklist-listing'
    },
    {
      id: 'host-vulnerability',
      title: 'Host Vulnerability Report',
      description: 'Search vulnerabilities by host and Vuln ID',
      icon: AlertTriangle,
      color: 'text-orange-600 bg-orange-50',
      href: '/rmf/reports/host-vulnerability'
    },
    {
      id: 'vulnerability-severity',
      title: 'Vulnerability by Status & Severity',
      description: 'Breakdown of vulnerabilities by status and category',
      icon: BarChart3,
      color: 'text-purple-600 bg-purple-50',
      href: '/rmf/reports/vulnerability-severity'
    },
    {
      id: 'checklist-upgrades',
      title: 'Checklist Upgrades Available',
      description: 'Find checklists with newer STIG versions',
      icon: RefreshCw,
      color: 'text-blue-600 bg-blue-50',
      href: '/rmf/reports/checklist-upgrades'
    },
    {
      id: 'vulnerability-overrides',
      title: 'Vulnerabilities with Override Set',
      description: 'List all vulnerabilities with severity overrides',
      icon: Shield,
      color: 'text-yellow-600 bg-yellow-50',
      href: '/rmf/reports/vulnerability-overrides'
    },
    {
      id: 'checklist-activity',
      title: 'Checklist Activity Report',
      description: 'Track changes and updates to checklists',
      icon: Activity,
      color: 'text-pink-600 bg-pink-50',
      href: '/rmf/reports/checklist-activity'
    },
    {
      id: 'host-by-control',
      title: 'Host by RMF Control Report',
      description: 'View hosts mapped to specific RMF controls',
      icon: Server,
      color: 'text-teal-600 bg-teal-50',
      href: '/rmf/reports/host-by-control'
    },
    {
      id: 'controls-listing',
      title: 'RMF Controls Listing',
      description: 'Complete listing of RMF controls and coverage',
      icon: Shield,
      color: 'text-cyan-600 bg-cyan-50',
      href: '/rmf/reports/controls-listing'
    }
  ];

  async function loadSystemGroups() {
    loading = true;
    try {
      const res = await systemGroupApi.list({ lifecycle_state: 'active' });
      if (res.success) {
        systemGroups = res.results || [];
      }
    } catch (error) {
      console.error('Error loading systems:', error);
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadSystemGroups();
  });
</script>

<svelte:head>
  <title>RMF Reports - CISO Assistant</title>
</svelte:head>

<div class="rmf-reports min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart3 class="text-green-600" size={28} />
            RMF Reports
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Generate and view compliance and vulnerability reports
          </p>
        </div>
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <!-- Reports Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {#each reports as report}
        <button
          onclick={() => goto(report.href)}
          class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md hover:border-indigo-300 transition-all text-left group"
        >
          <div class="flex items-start gap-4">
            <div class="p-3 rounded-lg {report.color}">
              <svelte:component this={report.icon} size={24} />
            </div>
            <div class="flex-1">
              <h3 class="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors">
                {report.title}
              </h3>
              <p class="mt-1 text-sm text-gray-600">{report.description}</p>
            </div>
            <ChevronRight size={20} class="text-gray-400 group-hover:text-indigo-600 transition-colors" />
          </div>
        </button>
      {/each}
    </div>

    <!-- Quick Stats -->
    {#if systemGroups.length > 0}
      <div class="mt-8">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">System Overview</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {#each systemGroups.slice(0, 4) as system}
            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h3 class="font-medium text-gray-900 truncate">{system.name}</h3>
              <div class="mt-2 grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span class="text-gray-500">Checklists:</span>
                  <span class="ml-1 font-medium">{system.totalChecklists}</span>
                </div>
                <div>
                  <span class="text-gray-500">Open:</span>
                  <span class="ml-1 font-medium text-red-600">{system.totalOpenVulnerabilities}</span>
                </div>
                <div>
                  <span class="text-gray-500">CAT I:</span>
                  <span class="ml-1 font-medium text-red-600">{system.totalCat1Open}</span>
                </div>
                <div>
                  <span class="text-gray-500">CAT II:</span>
                  <span class="ml-1 font-medium text-orange-600">{system.totalCat2Open}</span>
                </div>
              </div>
              <button
                onclick={() => goto(`/rmf/reports/system-charts?system=${system.id}`)}
                class="mt-3 w-full text-center text-sm text-indigo-600 hover:text-indigo-800"
              >
                View Charts
              </button>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Export Section -->
    <div class="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Quick Exports</h2>
      <div class="flex flex-wrap gap-4">
        <button
          onclick={() => goto('/rmf/reports/checklist-listing?export=xlsx')}
          class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
        >
          <FileSpreadsheet size={16} class="mr-2 text-green-600" />
          Export All Checklists
        </button>
        <button
          onclick={() => goto('/rmf/reports/vulnerability-severity?export=xlsx')}
          class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
        >
          <Download size={16} class="mr-2 text-blue-600" />
          Export Vulnerabilities
        </button>
        <button
          onclick={() => goto('/rmf/reports/controls-listing?export=xlsx')}
          class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
        >
          <Shield size={16} class="mr-2 text-purple-600" />
          Export Controls
        </button>
      </div>
    </div>
  </div>
</div>
