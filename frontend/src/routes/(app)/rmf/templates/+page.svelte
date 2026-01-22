<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    FileText,
    Plus,
    Search,
    Upload,
    Eye,
    Trash2,
    Copy,
    RefreshCw
  } from 'lucide-svelte';
  import { templateApi, systemGroupApi } from '$lib/services/rmf/api';
  import type { StigTemplate, SystemGroup } from '$lib/services/rmf/api';

  let templates: StigTemplate[] = [];
  let systemGroups: SystemGroup[] = [];
  let loading = true;
  let searchQuery = '';
  let showUploadModal = false;
  let showCreateChecklistModal = false;
  let selectedTemplate: StigTemplate | null = null;

  // Upload form state
  let uploadFile: File | null = null;
  let uploadTitle = '';
  let uploadDescription = '';
  let uploading = false;

  // Create checklist form state
  let createSystemId = '';
  let createHostname = '';
  let creating = false;

  $: filteredTemplates = templates.filter((t) =>
    t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.stigType.toLowerCase().includes(searchQuery.toLowerCase())
  );

  async function loadData() {
    loading = true;
    try {
      const [templatesRes, systemsRes] = await Promise.all([
        templateApi.list(),
        systemGroupApi.list({ lifecycle_state: 'active' })
      ]);

      if (templatesRes.success) templates = templatesRes.results || [];
      if (systemsRes.success) systemGroups = systemsRes.results || [];
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      loading = false;
    }
  }

  async function uploadTemplate() {
    if (!uploadFile || !uploadTitle) return;
    uploading = true;

    try {
      const res = await templateApi.upload(uploadFile, uploadTitle, uploadDescription);
      if (res.success) {
        templates = [res.data, ...templates];
        showUploadModal = false;
        uploadFile = null;
        uploadTitle = '';
        uploadDescription = '';
      }
    } catch (error) {
      console.error('Error uploading template:', error);
    } finally {
      uploading = false;
    }
  }

  async function createChecklist() {
    if (!selectedTemplate || !createSystemId || !createHostname) return;
    creating = true;

    try {
      const res = await templateApi.createChecklistFromTemplate(
        selectedTemplate.id,
        createSystemId,
        createHostname
      );
      if (res.success) {
        goto(`/rmf/checklists/${res.data.id}`);
      }
    } catch (error) {
      console.error('Error creating checklist:', error);
    } finally {
      creating = false;
    }
  }

  async function deleteTemplate(id: string) {
    if (!confirm('Are you sure you want to delete this template?')) return;

    try {
      const res = await templateApi.destroy(id);
      if (res.success) {
        templates = templates.filter((t) => t.id !== id);
      }
    } catch (error) {
      console.error('Error deleting template:', error);
    }
  }

  function openCreateModal(template: StigTemplate) {
    selectedTemplate = template;
    createSystemId = '';
    createHostname = '';
    showCreateChecklistModal = true;
  }

  function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      uploadFile = input.files[0];
      if (!uploadTitle) {
        uploadTitle = uploadFile.name.replace('.ckl', '');
      }
    }
  }

  onMount(() => {
    loadData();
  });
</script>

<svelte:head>
  <title>RMF Templates - CISO Assistant</title>
</svelte:head>

<div class="rmf-templates min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileText class="text-purple-600" size={28} />
            STIG Templates
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            Manage STIG checklist templates for quick deployment
          </p>
        </div>
        <button
          onclick={() => { showUploadModal = true; }}
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700"
        >
          <Upload size={16} class="mr-2" />
          Upload Template
        </button>
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <!-- Search -->
    <div class="mb-6">
      <div class="relative max-w-md">
        <Search size={16} class="absolute left-3 top-3 text-gray-400" />
        <input
          type="text"
          bind:value={searchQuery}
          placeholder="Search templates..."
          class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-purple-500 focus:border-purple-500"
        />
      </div>
    </div>

    <!-- Templates Table -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      {#if loading}
        <div class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
          <span class="ml-3 text-gray-600">Loading templates...</span>
        </div>
      {:else if filteredTemplates.length === 0}
        <div class="text-center py-12">
          <FileText size={48} class="mx-auto text-gray-400 mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">No Templates Found</h3>
          <p class="text-gray-600 mb-4">
            {searchQuery ? 'Try a different search term.' : 'Upload a CKL file to create a template.'}
          </p>
          {#if !searchQuery}
            <button
              onclick={() => { showUploadModal = true; }}
              class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700"
            >
              <Upload size={16} class="mr-2" />
              Upload Template
            </button>
          {/if}
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Version
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Release
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {#each filteredTemplates as template}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4">
                    <div class="text-sm font-medium text-gray-900">{template.title}</div>
                    {#if template.description}
                      <div class="text-xs text-gray-500 truncate max-w-xs">{template.description}</div>
                    {/if}
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-600">{template.version}</td>
                  <td class="px-6 py-4 text-sm text-gray-600">{template.release}</td>
                  <td class="px-6 py-4 text-sm text-gray-600">
                    {new Date(template.created_at).toLocaleDateString()}
                  </td>
                  <td class="px-6 py-4 text-right">
                    <div class="flex items-center justify-end gap-2">
                      <button
                        onclick={() => goto(`/rmf/templates/${template.id}`)}
                        class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded"
                        title="View"
                      >
                        <Eye size={16} />
                      </button>
                      <button
                        onclick={() => openCreateModal(template)}
                        class="p-2 text-purple-600 hover:text-purple-900 hover:bg-purple-50 rounded"
                        title="Create Checklist"
                      >
                        <Copy size={16} />
                      </button>
                      <button
                        onclick={() => deleteTemplate(template.id)}
                        class="p-2 text-red-600 hover:text-red-900 hover:bg-red-50 rounded"
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </div>
</div>

<!-- Upload Modal -->
{#if showUploadModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-semibold text-gray-900">Upload Template</h3>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">CKL File</label>
          <input
            type="file"
            accept=".ckl,.xml"
            onchange={handleFileSelect}
            class="w-full border border-gray-300 rounded-md px-3 py-2"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Title</label>
          <input
            type="text"
            bind:value={uploadTitle}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-purple-500 focus:border-purple-500"
            placeholder="Template title"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Description (optional)</label>
          <textarea
            bind:value={uploadDescription}
            rows="3"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-purple-500 focus:border-purple-500"
            placeholder="Template description..."
          ></textarea>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
        <button
          onclick={() => { showUploadModal = false; }}
          class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          onclick={uploadTemplate}
          disabled={!uploadFile || !uploadTitle || uploading}
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50"
        >
          {#if uploading}
            <RefreshCw size={16} class="mr-2 animate-spin" />
            Uploading...
          {:else}
            <Upload size={16} class="mr-2" />
            Upload
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Create Checklist Modal -->
{#if showCreateChecklistModal && selectedTemplate}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-semibold text-gray-900">Create Checklist from Template</h3>
        <p class="text-sm text-gray-500">{selectedTemplate.title}</p>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">System Package</label>
          <select
            bind:value={createSystemId}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-purple-500 focus:border-purple-500"
          >
            <option value="">Select a System Package</option>
            {#each systemGroups as system}
              <option value={system.id}>{system.name}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Hostname</label>
          <input
            type="text"
            bind:value={createHostname}
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-purple-500 focus:border-purple-500"
            placeholder="Enter hostname"
          />
        </div>
      </div>
      <div class="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
        <button
          onclick={() => { showCreateChecklistModal = false; selectedTemplate = null; }}
          class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          onclick={createChecklist}
          disabled={!createSystemId || !createHostname || creating}
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50"
        >
          {#if creating}
            <RefreshCw size={16} class="mr-2 animate-spin" />
            Creating...
          {:else}
            <Plus size={16} class="mr-2" />
            Create
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}
