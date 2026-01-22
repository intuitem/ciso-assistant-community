<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    BarChart3,
    TrendingUp,
    AlertTriangle,
    CheckCircle,
    RefreshCw,
    Eye
  } from 'lucide-svelte';

  import type { ChecklistScore } from '$lib/services/rmf/api';
  import { checklistScoreApi } from '$lib/services/rmf/api';

  let scores: ChecklistScore[] = [];
  let loading = true;
  let complianceStats: any = null;

  async function loadScores() {
    loading = true;
    try {
      const response = await checklistScoreApi.list();
      if (response.success) {
        scores = response.data.results || [];
      }
    } catch (error) {
      console.error('Error loading scores:', error);
    } finally {
      loading = false;
    }
  }

  async function loadComplianceStats() {
    try {
      const response = await checklistScoreApi.getComplianceDistribution();
      if (response.success) {
        complianceStats = response.data;
      }
    } catch (error) {
      console.error('Error loading compliance stats:', error);
    }
  }

  function getComplianceColor(percentage: number): string {
    if (percentage >= 90) return 'text-green-600';
    if (percentage >= 75) return 'text-yellow-600';
    return 'text-red-600';
  }

  function getComplianceIcon(percentage: number) {
    if (percentage >= 90) return CheckCircle;
    if (percentage >= 75) return TrendingUp;
    return AlertTriangle;
  }

  function formatScoreValue(value: number | null): string {
    return value !== null ? value.toString() : 'N/A';
  }

  onMount(async () => {
    await Promise.all([loadScores(), loadComplianceStats()]);
  });
</script>

<svelte:head>
  <title>RMF Checklist Scores - CISO Assistant</title>
</svelte:head>

<div class="rmf-checklist-scores">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="py-6">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">RMF Checklist Scores</h1>
            <p class="mt-1 text-sm text-gray-600">
              Real-time compliance scoring and vulnerability tracking
            </p>
          </div>
          <button
            on:click={() => { loadScores(); loadComplianceStats(); }}
            disabled={loading}
            class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <RefreshCw size={16} class={loading ? 'animate-spin' : ''} class="mr-2" />
            Refresh Scores
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Compliance Overview -->
  {#if complianceStats}
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <CheckCircle class="h-6 w-6 text-green-400" />
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">
                    High Compliance
                  </dt>
                  <dd class="text-lg font-medium text-gray-900">
                    {complianceStats.highCompliance || 0}%
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <TrendingUp class="h-6 w-6 text-yellow-400" />
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">
                    Medium Compliance
                  </dt>
                  <dd class="text-lg font-medium text-gray-900">
                    {complianceStats.mediumCompliance || 0}%
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <AlertTriangle class="h-6 w-6 text-red-400" />
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">
                    Low Compliance
                  </dt>
                  <dd class="text-lg font-medium text-gray-900">
                    {complianceStats.lowCompliance || 0}%
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <BarChart3 class="h-6 w-6 text-blue-400" />
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">
                    Total Checklists
                  </dt>
                  <dd class="text-lg font-medium text-gray-900">
                    {complianceStats.totalChecklists || 0}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Scores Table -->
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-6">
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-medium text-gray-900">Detailed Scores</h2>
      </div>

      <div class="overflow-x-auto">
        {#if loading}
          <div class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span class="ml-2 text-gray-600">Loading checklist scores...</span>
          </div>
        {:else if scores.length === 0}
          <div class="text-center py-12">
            <BarChart3 size={48} class="mx-auto mb-4 text-gray-400" />
            <h3 class="text-lg font-medium text-gray-900 mb-2">No scores available</h3>
            <p class="text-gray-600">
              Scores will appear here once checklists are imported and processed.
            </p>
          </div>
        {:else}
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Hostname
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  STIG Type
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  CAT I
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  CAT II
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  CAT III
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Compliance
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Updated
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {#each scores as score}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">
                      {score.hostName || 'Unknown'}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {score.stigType || 'Unknown'}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">
                      <span class="text-red-600 font-medium">{formatScoreValue(score.totalCat1Open)}</span>
                      <span class="text-gray-500">/{formatScoreValue(score.totalCat1)}</span>
                    </div>
                    <div class="text-xs text-gray-500">
                      Open: {formatScoreValue(score.totalCat1Open)}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">
                      <span class="text-orange-600 font-medium">{formatScoreValue(score.totalCat2Open)}</span>
                      <span class="text-gray-500">/{formatScoreValue(score.totalCat2)}</span>
                    </div>
                    <div class="text-xs text-gray-500">
                      Open: {formatScoreValue(score.totalCat2Open)}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">
                      <span class="text-yellow-600 font-medium">{formatScoreValue(score.totalCat3Open)}</span>
                      <span class="text-gray-500">/{formatScoreValue(score.totalCat3)}</span>
                    </div>
                    <div class="text-xs text-gray-500">
                      Open: {formatScoreValue(score.totalCat3Open)}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                      <svelte:component this={getComplianceIcon(score.compliance_percentage)} size={16} class={getComplianceColor(score.compliance_percentage)} />
                      <span class="ml-2 text-sm font-medium {getComplianceColor(score.compliance_percentage)}">
                        {score.compliance_percentage.toFixed(1)}%
                      </span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
                      <div
                        class="h-2 rounded-full transition-all duration-300"
                        class:bg-green-600={score.compliance_percentage >= 80}
                        class:bg-yellow-600={score.compliance_percentage >= 60 && score.compliance_percentage < 80}
                        class:bg-red-600={score.compliance_percentage < 60}
                        style="width: {Math.min(100, Math.max(0, score.compliance_percentage))}%"
                      ></div>
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(score.lastCalculatedAt).toLocaleDateString()}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      on:click={() => goto(`/rmf/checklist-scores/${score.id}`)}
                      class="text-blue-600 hover:text-blue-900"
                      title="View Details"
                    >
                      <Eye size={16} />
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </div>
  </div>
</div>
