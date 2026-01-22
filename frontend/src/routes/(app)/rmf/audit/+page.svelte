<script lang="ts">
  import { onMount } from 'svelte';
  import {
    Activity,
    Search,
    Filter,
    ChevronDown,
    ChevronRight,
    User,
    Clock,
    Globe,
    FileText,
    RefreshCw
  } from 'lucide-svelte';
  import { auditApi } from '$lib/services/rmf/api';
  import type { AuditEntry } from '$lib/services/rmf/api';

  let auditEntries: AuditEntry[] = [];
  let loading = true;
  let searchQuery = '';
  let programFilter = '';
  let actionFilter = '';
  let expandedEntries: Set<string> = new Set();
  let programs: string[] = [];
  let actions: string[] = [];

  // Pagination
  let currentPage = 1;
  let pageSize = 25;
  let totalCount = 0;

  $: totalPages = Math.ceil(totalCount / pageSize);

  async function loadAuditEntries() {
    loading = true;
    try {
      const params: Record<string, any> = {
        page: currentPage,
        page_size: pageSize
      };
      if (searchQuery) params.search = searchQuery;
      if (programFilter) params.program = programFilter;
      if (actionFilter) params.action = actionFilter;

      const res = await auditApi.list(params);
      if (res.success) {
        auditEntries = res.results || [];
        totalCount = res.count || 0;

        // Extract unique programs and actions for filters
        const uniquePrograms = new Set(auditEntries.map((e) => e.program));
        const uniqueActions = new Set(auditEntries.map((e) => e.action));
        programs = [...uniquePrograms];
        actions = [...uniqueActions];
      }
    } catch (error) {
      console.error('Error loading audit entries:', error);
    } finally {
      loading = false;
    }
  }

  function toggleExpanded(id: string) {
    if (expandedEntries.has(id)) {
      expandedEntries.delete(id);
    } else {
      expandedEntries.add(id);
    }
    expandedEntries = new Set(expandedEntries);
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleString();
  }

  function getActionColor(action: string): string {
    if (action.includes('create') || action.includes('upload')) return 'text-green-600 bg-green-50';
    if (action.includes('update') || action.includes('edit')) return 'text-blue-600 bg-blue-50';
    if (action.includes('delete') || action.includes('remove')) return 'text-red-600 bg-red-50';
    return 'text-gray-600 bg-gray-50';
  }

  function handleSearch() {
    currentPage = 1;
    loadAuditEntries();
  }

  function goToPage(page: number) {
    if (page >= 1 && page <= totalPages) {
      currentPage = page;
      loadAuditEntries();
    }
  }

  onMount(() => {
    loadAuditEntries();
  });
</script>

<svelte:head>
  <title>RMF Audit Log - CISO Assistant</title>
</svelte:head>

<div class="rmf-audit min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Activity class="text-orange-600" size={28} />
            Audit Log
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Track all RMF system activity and user actions
          </p>
        </div>
        <button
          onclick={loadAuditEntries}
          disabled={loading}
          class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw size={16} class="mr-2 {loading ? 'animate-spin' : ''}" />
          Refresh
        </button>
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
    <!-- Filters -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div class="flex flex-wrap items-center gap-4">
        <div class="flex-1 min-w-[200px]">
          <div class="relative">
            <Search size={16} class="absolute left-3 top-3 text-gray-400" />
            <input
              type="text"
              bind:value={searchQuery}
              onkeydown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search by username, message..."
              class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-orange-500 focus:border-orange-500"
            />
          </div>
        </div>
        <div>
          <select
            bind:value={programFilter}
            onchange={handleSearch}
            class="border border-gray-300 rounded-md px-3 py-2 focus:ring-orange-500 focus:border-orange-500"
          >
            <option value="">All Programs</option>
            {#each programs as program}
              <option value={program}>{program}</option>
            {/each}
          </select>
        </div>
        <div>
          <select
            bind:value={actionFilter}
            onchange={handleSearch}
            class="border border-gray-300 rounded-md px-3 py-2 focus:ring-orange-500 focus:border-orange-500"
          >
            <option value="">All Actions</option>
            {#each actions as action}
              <option value={action}>{action}</option>
            {/each}
          </select>
        </div>
        <button
          onclick={handleSearch}
          class="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700"
        >
          <Filter size={16} />
        </button>
      </div>
    </div>

    <!-- Audit Table -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      {#if loading}
        <div class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600"></div>
          <span class="ml-3 text-gray-600">Loading audit log...</span>
        </div>
      {:else if auditEntries.length === 0}
        <div class="text-center py-12">
          <Activity size={48} class="mx-auto text-gray-400 mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">No Audit Entries</h3>
          <p class="text-gray-600">
            {searchQuery || programFilter || actionFilter
              ? 'Try adjusting your filters.'
              : 'No activity has been recorded yet.'}
          </p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="w-8 px-4 py-3"></th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Program
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Username
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User ID
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {#each auditEntries as entry}
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-4">
                    <button
                      onclick={() => toggleExpanded(entry.id)}
                      class="text-gray-400 hover:text-gray-600"
                    >
                      {#if expandedEntries.has(entry.id)}
                        <ChevronDown size={16} />
                      {:else}
                        <ChevronRight size={16} />
                      {/if}
                    </button>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    <div class="flex items-center gap-1">
                      <Clock size={14} class="text-gray-400" />
                      {formatDate(entry.created_at)}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <span class="px-2 py-1 rounded-full bg-gray-100 text-gray-700 text-xs font-medium">
                      {entry.program}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <span class="px-2 py-1 rounded-full text-xs font-medium {getActionColor(entry.action)}">
                      {entry.action}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div class="flex items-center gap-1">
                      <User size={14} class="text-gray-400" />
                      {entry.username}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                    {entry.userId}
                  </td>
                </tr>
                {#if expandedEntries.has(entry.id)}
                  <tr>
                    <td colspan="6" class="px-6 py-4 bg-gray-50">
                      <div class="grid grid-cols-2 gap-4 text-sm">
                        {#if entry.fullName}
                          <div>
                            <span class="font-medium text-gray-500">Full Name:</span>
                            <span class="ml-2 text-gray-900">{entry.fullName}</span>
                          </div>
                        {/if}
                        {#if entry.email}
                          <div>
                            <span class="font-medium text-gray-500">Email:</span>
                            <span class="ml-2 text-gray-900">{entry.email}</span>
                          </div>
                        {/if}
                        {#if entry.message}
                          <div class="col-span-2">
                            <span class="font-medium text-gray-500">Message:</span>
                            <p class="mt-1 text-gray-900 bg-white p-2 rounded border">{entry.message}</p>
                          </div>
                        {/if}
                        {#if entry.url}
                          <div class="col-span-2">
                            <span class="font-medium text-gray-500">URL:</span>
                            <span class="ml-2 text-gray-900 font-mono text-xs">{entry.url}</span>
                          </div>
                        {/if}
                        {#if entry.details}
                          <div class="col-span-2">
                            <span class="font-medium text-gray-500">Details:</span>
                            <pre class="mt-1 text-xs bg-white p-2 rounded border overflow-x-auto">{JSON.stringify(entry.details, null, 2)}</pre>
                          </div>
                        {/if}
                        <div>
                          <span class="font-medium text-gray-500">Audit ID:</span>
                          <span class="ml-2 text-gray-500 font-mono text-xs">{entry.id}</span>
                        </div>
                      </div>
                    </td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        {#if totalPages > 1}
          <div class="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <div class="text-sm text-gray-600">
              Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalCount)} of {totalCount} entries
            </div>
            <div class="flex items-center gap-2">
              <button
                onclick={() => goToPage(currentPage - 1)}
                disabled={currentPage === 1}
                class="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <span class="text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onclick={() => goToPage(currentPage + 1)}
                disabled={currentPage === totalPages}
                class="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>
