<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    Server,
    FileCheck,
    FileText,
    AlertTriangle,
    Shield,
    Upload,
    BarChart3,
    RefreshCw,
    ChevronRight,
    Activity
  } from 'lucide-svelte';
  import DonutChart from '$lib/components/Chart/DonutChart.svelte';
  import BarChart from '$lib/components/Chart/BarChart.svelte';
  import { dashboardApi, systemGroupApi, nessusApi } from '$lib/services/rmf/api';
  import type { DashboardMetrics, SystemGroup, AuditEntry } from '$lib/services/rmf/api';

  let metrics: DashboardMetrics | null = null;
  let systemGroups: SystemGroup[] = [];
  let selectedSystemId = '';
  let nessusData: { critical: number; high: number; medium: number; low: number } | null = null;
  let scapData: { cat1: number; cat2: number; cat3: number } | null = null;
  let loading = true;
  let refreshing = false;

  // Chart colors following OpenRMF conventions
  const severityColors = ['#dc2626', '#ea580c', '#eab308', '#22c55e'];
  const statusColors = ['#dc2626', '#22c55e', '#9ca3af', '#3b82f6'];
  const categoryColors = ['#dc2626', '#f97316', '#facc15'];

  async function loadDashboardData() {
    loading = true;
    try {
      const [metricsRes, systemsRes] = await Promise.all([
        dashboardApi.getMetrics(),
        systemGroupApi.list({ lifecycle_state: 'active' })
      ]);

      if (metricsRes.success) {
        metrics = metricsRes.data;
      }
      if (systemsRes.success) {
        systemGroups = systemsRes.results || [];
        if (systemGroups.length > 0 && !selectedSystemId) {
          selectedSystemId = systemGroups[0].id;
          await loadSystemSpecificData(selectedSystemId);
        }
      }
    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      loading = false;
    }
  }

  async function loadSystemSpecificData(systemId: string) {
    if (!systemId) return;

    try {
      const [nessusRes, scoreRes] = await Promise.all([
        nessusApi.getSummary(systemId),
        systemGroupApi.getScore(systemId)
      ]);

      if (nessusRes.success) {
        nessusData = nessusRes.data;
      }
      if (scoreRes.success) {
        scapData = {
          cat1: scoreRes.data.totalCat1Open || 0,
          cat2: scoreRes.data.totalCat2Open || 0,
          cat3: scoreRes.data.totalCat3Open || 0
        };
      }
    } catch (error) {
      console.error('Error loading system data:', error);
    }
  }

  async function handleSystemChange(event: Event) {
    const target = event.target as HTMLSelectElement;
    selectedSystemId = target.value;
    await loadSystemSpecificData(selectedSystemId);
  }

  async function refresh() {
    refreshing = true;
    await loadDashboardData();
    refreshing = false;
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleString();
  }

  onMount(async () => {
    await loadDashboardData();
  });
</script>

<svelte:head>
  <title>RMF Dashboard - CISO Assistant</title>
</svelte:head>

<div class="rmf-dashboard">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="py-6">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Shield class="text-indigo-600" size={28} />
              RMF Dashboard
            </h1>
            <p class="mt-1 text-sm text-gray-600">
              Risk Management Framework - System Security Overview
            </p>
          </div>
          <div class="flex items-center gap-3">
            <button
              onclick={refresh}
              disabled={refreshing}
              class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw size={16} class="mr-2 {refreshing ? 'animate-spin' : ''}" />
              Refresh
            </button>
            <button
              onclick={() => goto('/rmf/upload')}
              class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
            >
              <Upload size={16} class="mr-2" />
              Upload
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      <span class="ml-3 text-gray-600">Loading dashboard...</span>
    </div>
  {:else}
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <!-- Metric Cards Row -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- System Packages Card -->
        <button
          onclick={() => goto('/rmf/system-groups')}
          class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md hover:border-indigo-300 transition-all cursor-pointer text-left"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500 uppercase tracking-wide">System Packages</p>
              <p class="mt-2 text-4xl font-bold text-gray-900">{metrics?.totalSystems || 0}</p>
            </div>
            <div class="p-3 bg-indigo-100 rounded-full">
              <Server class="text-indigo-600" size={24} />
            </div>
          </div>
          <div class="mt-4 flex items-center text-sm text-indigo-600">
            <span>View all systems</span>
            <ChevronRight size={16} class="ml-1" />
          </div>
        </button>

        <!-- Checklists Card -->
        <button
          onclick={() => goto('/rmf/checklists')}
          class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md hover:border-indigo-300 transition-all cursor-pointer text-left"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500 uppercase tracking-wide">Checklists</p>
              <p class="mt-2 text-4xl font-bold text-gray-900">{metrics?.totalChecklists || 0}</p>
            </div>
            <div class="p-3 bg-green-100 rounded-full">
              <FileCheck class="text-green-600" size={24} />
            </div>
          </div>
          <div class="mt-4 flex items-center text-sm text-green-600">
            <span>View all checklists</span>
            <ChevronRight size={16} class="ml-1" />
          </div>
        </button>

        <!-- Templates Card -->
        <button
          onclick={() => goto('/rmf/templates')}
          class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md hover:border-indigo-300 transition-all cursor-pointer text-left"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500 uppercase tracking-wide">Templates</p>
              <p class="mt-2 text-4xl font-bold text-gray-900">{metrics?.totalTemplates || 0}</p>
            </div>
            <div class="p-3 bg-purple-100 rounded-full">
              <FileText class="text-purple-600" size={24} />
            </div>
          </div>
          <div class="mt-4 flex items-center text-sm text-purple-600">
            <span>View templates</span>
            <ChevronRight size={16} class="ml-1" />
          </div>
        </button>
      </div>

      <!-- Nessus/ACAS and SCAP Sections -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Nessus/ACAS Patch Scans -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200">
          <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex items-center justify-between">
              <h2 class="text-lg font-semibold text-gray-900">Nessus / ACAS Patch Scans</h2>
              <select
                value={selectedSystemId}
                onchange={handleSystemChange}
                class="text-sm border border-gray-300 rounded-md px-3 py-1.5 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Select System</option>
                {#each systemGroups as system}
                  <option value={system.id}>{system.name}</option>
                {/each}
              </select>
            </div>
          </div>
          <div class="p-6">
            {#if nessusData}
              <div class="grid grid-cols-4 gap-4">
                <div class="text-center p-4 bg-red-50 rounded-lg border border-red-200 cursor-pointer hover:bg-red-100 transition-colors">
                  <p class="text-3xl font-bold text-red-600">{nessusData.critical}</p>
                  <p class="text-sm text-red-700 font-medium">Critical</p>
                </div>
                <div class="text-center p-4 bg-orange-50 rounded-lg border border-orange-200 cursor-pointer hover:bg-orange-100 transition-colors">
                  <p class="text-3xl font-bold text-orange-600">{nessusData.high}</p>
                  <p class="text-sm text-orange-700 font-medium">High</p>
                </div>
                <div class="text-center p-4 bg-yellow-50 rounded-lg border border-yellow-200 cursor-pointer hover:bg-yellow-100 transition-colors">
                  <p class="text-3xl font-bold text-yellow-600">{nessusData.medium}</p>
                  <p class="text-sm text-yellow-700 font-medium">Medium</p>
                </div>
                <div class="text-center p-4 bg-green-50 rounded-lg border border-green-200 cursor-pointer hover:bg-green-100 transition-colors">
                  <p class="text-3xl font-bold text-green-600">{nessusData.low}</p>
                  <p class="text-sm text-green-700 font-medium">Low</p>
                </div>
              </div>
            {:else}
              <div class="text-center py-8 text-gray-500">
                <AlertTriangle size={32} class="mx-auto mb-2 text-gray-400" />
                <p>No Nessus scan data available</p>
                <p class="text-sm">Select a system or upload a Nessus scan</p>
              </div>
            {/if}
          </div>
        </div>

        <!-- SCAP Scans & Checklists -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200">
          <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex items-center justify-between">
              <h2 class="text-lg font-semibold text-gray-900">SCAP Scans & Checklists</h2>
              <select
                value={selectedSystemId}
                onchange={handleSystemChange}
                class="text-sm border border-gray-300 rounded-md px-3 py-1.5 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Select System</option>
                {#each systemGroups as system}
                  <option value={system.id}>{system.name}</option>
                {/each}
              </select>
            </div>
          </div>
          <div class="p-6">
            {#if scapData}
              <div class="grid grid-cols-3 gap-4">
                <div class="text-center p-4 bg-red-50 rounded-lg border border-red-200 cursor-pointer hover:bg-red-100 transition-colors">
                  <p class="text-3xl font-bold text-red-600">{scapData.cat1}</p>
                  <p class="text-sm text-red-700 font-medium">CAT I</p>
                </div>
                <div class="text-center p-4 bg-orange-50 rounded-lg border border-orange-200 cursor-pointer hover:bg-orange-100 transition-colors">
                  <p class="text-3xl font-bold text-orange-600">{scapData.cat2}</p>
                  <p class="text-sm text-orange-700 font-medium">CAT II</p>
                </div>
                <div class="text-center p-4 bg-yellow-50 rounded-lg border border-yellow-200 cursor-pointer hover:bg-yellow-100 transition-colors">
                  <p class="text-3xl font-bold text-yellow-600">{scapData.cat3}</p>
                  <p class="text-sm text-yellow-700 font-medium">CAT III</p>
                </div>
              </div>
            {:else}
              <div class="text-center py-8 text-gray-500">
                <FileCheck size={32} class="mx-auto mb-2 text-gray-400" />
                <p>No SCAP data available</p>
                <p class="text-sm">Select a system with uploaded checklists</p>
              </div>
            {/if}
          </div>
        </div>
      </div>

      <!-- Charts Row -->
      {#if metrics}
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Vulnerability Severity Chart -->
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Vulnerabilities by Severity</h3>
            {#if metrics.vulnerabilitiesBySeverity && metrics.vulnerabilitiesBySeverity.length > 0}
              <div class="h-64">
                <DonutChart
                  name="severity-chart"
                  s_label="Severity"
                  values={metrics.vulnerabilitiesBySeverity}
                  colors={categoryColors}
                  height="h-64"
                />
              </div>
            {:else}
              <div class="h-64 flex items-center justify-center text-gray-500">
                No vulnerability data
              </div>
            {/if}
          </div>

          <!-- Vulnerability Status Chart -->
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Vulnerabilities by Status</h3>
            {#if metrics.vulnerabilitiesByStatus && metrics.vulnerabilitiesByStatus.length > 0}
              <div class="h-64">
                <DonutChart
                  name="status-chart"
                  s_label="Status"
                  values={metrics.vulnerabilitiesByStatus}
                  colors={statusColors}
                  height="h-64"
                />
              </div>
            {:else}
              <div class="h-64 flex items-center justify-center text-gray-500">
                No status data
              </div>
            {/if}
          </div>
        </div>
      {/if}

      <!-- Recent Activity -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200">
        <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Activity size={20} class="text-indigo-600" />
            Recent Activity
          </h2>
          <button
            onclick={() => goto('/rmf/audit')}
            class="text-sm text-indigo-600 hover:text-indigo-800"
          >
            View all
          </button>
        </div>
        <div class="divide-y divide-gray-200">
          {#if metrics?.recentActivity && metrics.recentActivity.length > 0}
            {#each metrics.recentActivity.slice(0, 5) as activity}
              <div class="px-6 py-4 hover:bg-gray-50">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-sm font-medium text-gray-900">{activity.action}</p>
                    <p class="text-xs text-gray-500">
                      {activity.program} - {activity.username}
                    </p>
                  </div>
                  <span class="text-xs text-gray-400">{formatDate(activity.created_at)}</span>
                </div>
              </div>
            {/each}
          {:else}
            <div class="px-6 py-8 text-center text-gray-500">
              No recent activity
            </div>
          {/if}
        </div>
      </div>

      <!-- Quick Links -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <button
          onclick={() => goto('/rmf/compliance')}
          class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md hover:border-indigo-300 transition-all text-left"
        >
          <Shield size={20} class="text-indigo-600 mb-2" />
          <p class="font-medium text-gray-900">Compliance</p>
          <p class="text-xs text-gray-500">Generate reports</p>
        </button>
        <button
          onclick={() => goto('/rmf/reports')}
          class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md hover:border-indigo-300 transition-all text-left"
        >
          <BarChart3 size={20} class="text-green-600 mb-2" />
          <p class="font-medium text-gray-900">Reports</p>
          <p class="text-xs text-gray-500">View all reports</p>
        </button>
        <button
          onclick={() => goto('/rmf/upload')}
          class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md hover:border-indigo-300 transition-all text-left"
        >
          <Upload size={20} class="text-purple-600 mb-2" />
          <p class="font-medium text-gray-900">Upload</p>
          <p class="text-xs text-gray-500">Import CKL/SCAP</p>
        </button>
        <button
          onclick={() => goto('/rmf/audit')}
          class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md hover:border-indigo-300 transition-all text-left"
        >
          <Activity size={20} class="text-orange-600 mb-2" />
          <p class="font-medium text-gray-900">Audit Log</p>
          <p class="text-xs text-gray-500">View activity</p>
        </button>
      </div>
    </div>
  {/if}
</div>
