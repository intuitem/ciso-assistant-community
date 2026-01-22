<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import {
    ArrowLeft,
    Server,
    FileCheck,
    Upload,
    Download,
    FileSpreadsheet,
    Trash2,
    Edit,
    RefreshCw,
    Play,
    FileText,
    Shield,
    AlertTriangle,
    CheckCircle,
    Clock,
    Archive,
    ChevronDown,
    ChevronRight,
    Eye
  } from 'lucide-svelte';
  import DonutChart from '$lib/components/Chart/DonutChart.svelte';
  import {
    systemGroupApi,
    stigChecklistApi,
    exportApi,
    checklistScoreApi
  } from '$lib/services/rmf/api';
  import type { SystemGroup, StigChecklist, ChecklistScore } from '$lib/services/rmf/api';

  // State
  let system: SystemGroup | null = null;
  let checklists: StigChecklist[] = [];
  let systemScore: ChecklistScore | null = null;
  let loading = true;
  let showEditModal = false;
  let deleting = false;

  // Filter state (like OpenRMF)
  let statusFilters = {
    naf: true,
    open: true,
    na: true,
    nr: true
  };
  let severityFilters = {
    cat1: true,
    cat2: true,
    cat3: true
  };
  let hostnameFilter = '';

  // Selection state for bulk operations
  let selectedChecklistIds: Set<string> = new Set();
  let selectAll = false;

  // Expanded rows for detail view
  let expandedRows: Set<string> = new Set();

  // Chart data
  $: statusChartData = systemScore
    ? [
        { name: 'Open', value: systemScore.totalOpen },
        { name: 'Not a Finding', value: systemScore.totalNotAFinding },
        { name: 'Not Applicable', value: systemScore.totalNotApplicable },
        { name: 'Not Reviewed', value: systemScore.totalNotReviewed }
      ]
    : [];

  // Filtered checklists
  $: filteredChecklists = checklists.filter((c) => {
    if (hostnameFilter && !c.hostName.toLowerCase().includes(hostnameFilter.toLowerCase())) {
      return false;
    }
    return true;
  });

  async function loadData() {
    const id = $page.params.id;
    loading = true;

    try {
      const [systemRes, checklistsRes, scoreRes] = await Promise.all([
        systemGroupApi.retrieve(id),
        systemGroupApi.getChecklists(id, {}),
        systemGroupApi.getScore(id)
      ]);

      if (systemRes.success) system = systemRes.data;
      if (checklistsRes.success) checklists = checklistsRes.results || [];
      if (scoreRes.success) systemScore = scoreRes.data;
    } catch (error) {
      console.error('Error loading system:', error);
    } finally {
      loading = false;
    }
  }

  function toggleSelectAll() {
    if (selectAll) {
      selectedChecklistIds = new Set();
    } else {
      selectedChecklistIds = new Set(filteredChecklists.map((c) => c.id));
    }
    selectAll = !selectAll;
  }

  function toggleChecklistSelection(id: string) {
    if (selectedChecklistIds.has(id)) {
      selectedChecklistIds.delete(id);
    } else {
      selectedChecklistIds.add(id);
    }
    selectedChecklistIds = new Set(selectedChecklistIds);
    selectAll = selectedChecklistIds.size === filteredChecklists.length;
  }

  function toggleExpandRow(id: string) {
    if (expandedRows.has(id)) {
      expandedRows.delete(id);
    } else {
      expandedRows.add(id);
    }
    expandedRows = new Set(expandedRows);
  }

  async function downloadAllCkl() {
    await exportApi.downloadSystemCkl($page.params.id, {
      naf: statusFilters.naf,
      open: statusFilters.open,
      na: statusFilters.na,
      nr: statusFilters.nr,
      cat1: severityFilters.cat1,
      cat2: severityFilters.cat2,
      cat3: severityFilters.cat3
    });
  }

  async function exportXlsx() {
    await exportApi.downloadSystemXlsx($page.params.id, {
      naf: statusFilters.naf,
      open: statusFilters.open,
      na: statusFilters.na,
      nr: statusFilters.nr,
      cat1: severityFilters.cat1,
      cat2: severityFilters.cat2,
      cat3: severityFilters.cat3
    });
  }

  async function exportTestPlan() {
    await exportApi.downloadTestPlan($page.params.id);
  }

  async function exportPoam() {
    await exportApi.downloadPoam($page.params.id);
  }

  async function deleteSelected() {
    if (selectedChecklistIds.size === 0) return;
    if (!confirm(`Delete ${selectedChecklistIds.size} selected checklist(s)?`)) return;

    deleting = true;
    try {
      for (const id of selectedChecklistIds) {
        await stigChecklistApi.destroy(id);
      }
      checklists = checklists.filter((c) => !selectedChecklistIds.has(c.id));
      selectedChecklistIds = new Set();
      selectAll = false;

      // Refresh score
      const scoreRes = await systemGroupApi.getScore($page.params.id);
      if (scoreRes.success) systemScore = scoreRes.data;
    } catch (error) {
      console.error('Error deleting checklists:', error);
    } finally {
      deleting = false;
    }
  }

  async function deleteAllChecklists() {
    if (!confirm('Are you sure you want to delete ALL checklists from this system?')) return;

    deleting = true;
    try {
      await systemGroupApi.deleteAllChecklists($page.params.id);
      checklists = [];
      selectedChecklistIds = new Set();
      selectAll = false;

      // Refresh score
      const scoreRes = await systemGroupApi.getScore($page.params.id);
      if (scoreRes.success) systemScore = scoreRes.data;
    } catch (error) {
      console.error('Error deleting all checklists:', error);
    } finally {
      deleting = false;
    }
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString() + ' ' + new Date(dateStr).toLocaleTimeString();
  }

  onMount(() => {
    loadData();
  });
</script>

<svelte:head>
  <title>{system?.name || 'System'} - RMF - CISO Assistant</title>
</svelte:head>

<div class="system-detail min-h-screen bg-gray-50">
  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
    </div>
  {:else if system}
    <!-- Header -->
    <div class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <button
              onclick={() => goto('/rmf/system-groups')}
              class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <h1 class="text-xl font-bold text-gray-900 flex items-center gap-2">
                <Server class="text-indigo-600" size={24} />
                {system.name}
              </h1>
              <p class="text-sm text-gray-500">{system.description || 'No description'}</p>
            </div>
            <span class="px-2 py-1 text-xs rounded-full {system.lifecycle_state === 'active' ? 'bg-green-100 text-green-800' : system.lifecycle_state === 'draft' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'}">
              {system.lifecycle_state}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <button
              onclick={() => { showEditModal = true; }}
              class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <Edit size={16} class="mr-2" />
              Edit
            </button>
            <button
              onclick={() => goto('/rmf/compliance?system=' + system?.id)}
              class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <Shield size={16} class="mr-2" />
              Compliance
            </button>
            <button
              onclick={() => goto('/rmf/upload?system=' + system?.id)}
              class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <Upload size={16} class="mr-2" />
              Upload
            </button>
            <button
              class="inline-flex items-center px-3 py-2 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50"
            >
              <Trash2 size={16} class="mr-2" />
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <!-- System Info Card -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">System Package Information</h2>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span class="text-gray-500">Title:</span>
              <p class="font-medium text-gray-900">{system.name}</p>
            </div>
            <div>
              <span class="text-gray-500">Description:</span>
              <p class="font-medium text-gray-900">{system.description || '-'}</p>
            </div>
            <div>
              <span class="text-gray-500">Checklists:</span>
              <p class="font-medium text-gray-900">{system.totalChecklists}</p>
            </div>
            <div>
              <span class="text-gray-500">Nessus Scans:</span>
              <p class="font-medium text-gray-900">{system.nessusScanIds?.length || 0}</p>
            </div>
            <div>
              <span class="text-gray-500">Created:</span>
              <p class="font-medium text-gray-900">{formatDate(system.created_at)}</p>
            </div>
            <div>
              <span class="text-gray-500">Updated:</span>
              <p class="font-medium text-gray-900">{formatDate(system.updated_at)}</p>
            </div>
            <div>
              <span class="text-gray-500">Last Compliance:</span>
              <p class="font-medium text-gray-900">{system.last_compliance_check ? formatDate(system.last_compliance_check) : 'Never'}</p>
            </div>
          </div>

          <div class="mt-6 flex flex-wrap gap-2">
            <button
              onclick={exportTestPlan}
              class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <FileText size={16} class="mr-2" />
              Generate Test Plan
            </button>
            <button
              onclick={exportPoam}
              class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <FileText size={16} class="mr-2" />
              Generate POA&M
            </button>
          </div>
        </div>

        <!-- System Status Pie Chart -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">Status Breakdown</h2>
          {#if statusChartData.length > 0 && statusChartData.some((d) => d.value > 0)}
            <div class="h-48">
              <DonutChart
                name="system-status"
                values={statusChartData}
                colors={['#dc2626', '#22c55e', '#9ca3af', '#3b82f6']}
                height="h-48"
              />
            </div>
          {:else}
            <div class="h-48 flex items-center justify-center text-gray-500">
              No data available
            </div>
          {/if}
        </div>
      </div>

      <!-- Filters -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div class="flex flex-wrap items-center gap-4">
          <span class="text-sm font-medium text-gray-700">Filter:</span>
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-500">Status:</span>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={statusFilters.naf} class="rounded border-gray-300 text-green-600" />
              <span class="ml-1 text-sm text-green-700">NaF</span>
            </label>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={statusFilters.open} class="rounded border-gray-300 text-red-600" />
              <span class="ml-1 text-sm text-red-700">Open</span>
            </label>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={statusFilters.na} class="rounded border-gray-300 text-gray-600" />
              <span class="ml-1 text-sm text-gray-700">N/A</span>
            </label>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={statusFilters.nr} class="rounded border-gray-300 text-blue-600" />
              <span class="ml-1 text-sm text-blue-700">NR</span>
            </label>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-500">Severity:</span>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={severityFilters.cat1} class="rounded border-gray-300 text-red-600" />
              <span class="ml-1 text-sm text-red-700">CAT1</span>
            </label>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={severityFilters.cat2} class="rounded border-gray-300 text-orange-600" />
              <span class="ml-1 text-sm text-orange-700">CAT2</span>
            </label>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={severityFilters.cat3} class="rounded border-gray-300 text-yellow-600" />
              <span class="ml-1 text-sm text-yellow-700">CAT3</span>
            </label>
          </div>
          <div class="flex-1 max-w-xs">
            <input
              type="text"
              bind:value={hostnameFilter}
              placeholder="Filter by hostname..."
              class="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        </div>
      </div>

      <!-- Checklists Table -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200">
        <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-gray-900">
            Checklists ({filteredChecklists.length})
          </h2>
          <div class="flex items-center gap-2">
            {#if selectedChecklistIds.size > 0}
              <span class="text-sm text-gray-600">{selectedChecklistIds.size} selected</span>
              <button
                onclick={deleteSelected}
                disabled={deleting}
                class="inline-flex items-center px-3 py-1.5 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50"
              >
                <Trash2 size={14} class="mr-1" />
                Delete Selected
              </button>
            {/if}
            <button
              onclick={deleteAllChecklists}
              disabled={deleting || checklists.length === 0}
              class="inline-flex items-center px-3 py-1.5 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50"
            >
              <Trash2 size={14} class="mr-1" />
              Delete All
            </button>
            <button
              onclick={exportXlsx}
              disabled={checklists.length === 0}
              class="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <FileSpreadsheet size={14} class="mr-1" />
              Export Excel
            </button>
            <button
              onclick={downloadAllCkl}
              disabled={checklists.length === 0}
              class="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <Download size={14} class="mr-1" />
              Download ZIP
            </button>
          </div>
        </div>

        {#if filteredChecklists.length === 0}
          <div class="text-center py-12">
            <FileCheck size={48} class="mx-auto text-gray-400 mb-4" />
            <h3 class="text-lg font-medium text-gray-900 mb-2">No Checklists</h3>
            <p class="text-gray-600 mb-4">
              {hostnameFilter ? 'No checklists match your filter.' : 'Upload CKL files to get started.'}
            </p>
            <button
              onclick={() => goto('/rmf/upload?system=' + system?.id)}
              class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
            >
              <Upload size={16} class="mr-2" />
              Upload CKL
            </button>
          </div>
        {:else}
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="w-8 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectAll}
                      onchange={toggleSelectAll}
                      class="rounded border-gray-300 text-indigo-600"
                    />
                  </th>
                  <th class="w-8 px-4 py-3"></th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                  <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Tags</th>
                  <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Open</th>
                  <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">NaF</th>
                  <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">N/A</th>
                  <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">NR</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                {#each filteredChecklists as checklist}
                  <tr class="hover:bg-gray-50">
                    <td class="px-4 py-4">
                      <input
                        type="checkbox"
                        checked={selectedChecklistIds.has(checklist.id)}
                        onchange={() => toggleChecklistSelection(checklist.id)}
                        class="rounded border-gray-300 text-indigo-600"
                      />
                    </td>
                    <td class="px-4 py-4">
                      <button
                        onclick={() => toggleExpandRow(checklist.id)}
                        class="text-gray-400 hover:text-gray-600"
                      >
                        {#if expandedRows.has(checklist.id)}
                          <ChevronDown size={16} />
                        {:else}
                          <ChevronRight size={16} />
                        {/if}
                      </button>
                    </td>
                    <td class="px-6 py-4">
                      <button
                        onclick={() => goto(`/rmf/checklists/${checklist.id}`)}
                        class="text-indigo-600 hover:text-indigo-800 font-medium"
                      >
                        {checklist.stigType}
                      </button>
                      <p class="text-xs text-gray-500">
                        {checklist.hostName} - last updated {formatDate(checklist.updated_at)}
                      </p>
                    </td>
                    <td class="px-4 py-4 text-center text-sm text-gray-600">
                      {checklist.tags?.join(', ') || '-'}
                    </td>
                    <td class="px-4 py-4 text-center">
                      <span class="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">
                        {checklist.vulnerabilityFindingIds?.length || 0}
                      </span>
                    </td>
                    <td class="px-4 py-4 text-center">
                      <span class="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">0</span>
                    </td>
                    <td class="px-4 py-4 text-center">
                      <span class="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">0</span>
                    </td>
                    <td class="px-4 py-4 text-center">
                      <span class="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">0</span>
                    </td>
                  </tr>
                  {#if expandedRows.has(checklist.id)}
                    <tr>
                      <td colspan="8" class="px-6 py-4 bg-gray-50">
                        <div class="grid grid-cols-4 gap-4 text-sm">
                          <div>
                            <span class="text-gray-500">Hostname:</span>
                            <span class="ml-2 font-medium">{checklist.hostName}</span>
                          </div>
                          <div>
                            <span class="text-gray-500">STIG Type:</span>
                            <span class="ml-2 font-medium">{checklist.stigType}</span>
                          </div>
                          <div>
                            <span class="text-gray-500">Version:</span>
                            <span class="ml-2 font-medium">{checklist.version}</span>
                          </div>
                          <div>
                            <span class="text-gray-500">Release:</span>
                            <span class="ml-2 font-medium">{checklist.stigRelease}</span>
                          </div>
                        </div>
                        <div class="mt-4">
                          <button
                            onclick={() => goto(`/rmf/checklists/${checklist.id}`)}
                            class="inline-flex items-center px-3 py-1.5 border border-indigo-300 rounded-md text-sm font-medium text-indigo-700 bg-white hover:bg-indigo-50"
                          >
                            <Eye size={14} class="mr-1" />
                            View Details
                          </button>
                        </div>
                      </td>
                    </tr>
                  {/if}
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <div class="text-center py-24">
      <Server size={48} class="mx-auto text-gray-400 mb-4" />
      <p class="text-gray-600">System not found</p>
    </div>
  {/if}
</div>
