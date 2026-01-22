<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import {
    PieChart,
    Download,
    RefreshCw,
    ArrowLeft
  } from 'lucide-svelte';
  import DonutChart from '$lib/components/Chart/DonutChart.svelte';
  import BarChart from '$lib/components/Chart/BarChart.svelte';
  import { systemGroupApi, reportsApi } from '$lib/services/rmf/api';
  import type { SystemGroup } from '$lib/services/rmf/api';

  let systemGroups: SystemGroup[] = [];
  let selectedSystemId = '';
  let loading = false;
  let chartData: {
    severityBreakdown: { name: string; value: number }[];
    statusBreakdown: { name: string; value: number }[];
    categoryBreakdown: { name: string; value: number }[];
  } | null = null;

  const statusColors = ['#dc2626', '#22c55e', '#9ca3af', '#3b82f6'];
  const categoryColors = ['#dc2626', '#f97316', '#facc15'];

  async function loadSystemGroups() {
    try {
      const res = await systemGroupApi.list({ lifecycle_state: 'active' });
      if (res.success) {
        systemGroups = res.results || [];

        // Check URL params for pre-selected system
        const urlParams = new URLSearchParams(window.location.search);
        const systemParam = urlParams.get('system');
        if (systemParam) {
          selectedSystemId = systemParam;
          await loadChartData();
        }
      }
    } catch (error) {
      console.error('Error loading systems:', error);
    }
  }

  async function loadChartData() {
    if (!selectedSystemId) {
      chartData = null;
      return;
    }

    loading = true;
    try {
      const res = await reportsApi.getSystemCharts(selectedSystemId);
      if (res.success) {
        chartData = res.data;
      }
    } catch (error) {
      console.error('Error loading chart data:', error);
    } finally {
      loading = false;
    }
  }

  function downloadChart(chartId: string) {
    const canvas = document.querySelector(`#${chartId} canvas`) as HTMLCanvasElement;
    if (canvas) {
      const link = document.createElement('a');
      link.download = `${chartId}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  }

  $: if (selectedSystemId) {
    loadChartData();
  }

  onMount(() => {
    loadSystemGroups();
  });
</script>

<svelte:head>
  <title>System Charts - RMF Reports - CISO Assistant</title>
</svelte:head>

<div class="system-charts min-h-screen bg-gray-50">
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
            <PieChart class="text-indigo-600" size={28} />
            System Package Pie Charts
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Visual breakdown of vulnerabilities by status and category
          </p>
        </div>
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
    <!-- Filter Card -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex items-center gap-4">
        <div class="flex-1 max-w-md">
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
        <div class="flex items-end">
          <button
            onclick={loadChartData}
            disabled={!selectedSystemId || loading}
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
          >
            {#if loading}
              <RefreshCw size={16} class="mr-2 animate-spin" />
              Loading...
            {:else}
              Run Report
            {/if}
          </button>
        </div>
      </div>
    </div>

    {#if chartData}
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Status Breakdown Chart -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200">
          <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900">Status Breakdown</h2>
            <button
              onclick={() => downloadChart('status-chart')}
              class="text-gray-500 hover:text-gray-700"
              title="Download Chart"
            >
              <Download size={18} />
            </button>
          </div>
          <div class="p-6" id="status-chart">
            {#if chartData.statusBreakdown && chartData.statusBreakdown.some((d) => d.value > 0)}
              <div class="h-80">
                <DonutChart
                  name="status-breakdown"
                  s_label="Status"
                  values={chartData.statusBreakdown}
                  colors={statusColors}
                  height="h-80"
                  showPercentage={true}
                />
              </div>
            {:else}
              <div class="h-80 flex items-center justify-center text-gray-500">
                No data available
              </div>
            {/if}
          </div>
        </div>

        <!-- Category Breakdown Chart -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200">
          <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900">Category Breakdown</h2>
            <button
              onclick={() => downloadChart('category-chart')}
              class="text-gray-500 hover:text-gray-700"
              title="Download Chart"
            >
              <Download size={18} />
            </button>
          </div>
          <div class="p-6" id="category-chart">
            {#if chartData.categoryBreakdown && chartData.categoryBreakdown.some((d) => d.value > 0)}
              <div class="h-80">
                <DonutChart
                  name="category-breakdown"
                  s_label="Category"
                  values={chartData.categoryBreakdown}
                  colors={categoryColors}
                  height="h-80"
                  showPercentage={true}
                />
              </div>
            {:else}
              <div class="h-80 flex items-center justify-center text-gray-500">
                No data available
              </div>
            {/if}
          </div>
        </div>

        <!-- Severity Breakdown Bar Chart -->
        <div class="lg:col-span-2 bg-white rounded-lg shadow-sm border border-gray-200">
          <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900">Severity by Status</h2>
            <button
              onclick={() => downloadChart('severity-chart')}
              class="text-gray-500 hover:text-gray-700"
              title="Download Chart"
            >
              <Download size={18} />
            </button>
          </div>
          <div class="p-6" id="severity-chart">
            {#if chartData.severityBreakdown && chartData.severityBreakdown.some((d) => d.value > 0)}
              <div class="h-64">
                <BarChart
                  name="severity-breakdown"
                  values={chartData.severityBreakdown.map((d) => ({ value: d.value, itemStyle: { color: '#4f46e5' } }))}
                  labels={chartData.severityBreakdown.map((d) => d.name)}
                  height="h-64"
                />
              </div>
            {:else}
              <div class="h-64 flex items-center justify-center text-gray-500">
                No data available
              </div>
            {/if}
          </div>
        </div>
      </div>

      <!-- Summary Statistics -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Summary Statistics</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          {#each chartData.statusBreakdown || [] as item}
            <div class="text-center p-4 bg-gray-50 rounded-lg">
              <p class="text-2xl font-bold text-gray-900">{item.value}</p>
              <p class="text-sm text-gray-600">{item.name}</p>
            </div>
          {/each}
        </div>
      </div>
    {:else if selectedSystemId && !loading}
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <PieChart size={48} class="mx-auto text-gray-400 mb-4" />
        <p class="text-gray-600">Click "Run Report" to generate charts</p>
      </div>
    {:else if !selectedSystemId}
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <PieChart size={48} class="mx-auto text-gray-400 mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">Select a System Package</h3>
        <p class="text-gray-600">Choose a system package to view chart breakdowns</p>
      </div>
    {/if}
  </div>
</div>
