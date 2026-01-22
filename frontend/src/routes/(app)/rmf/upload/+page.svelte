<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import {
    Upload,
    FileText,
    Server,
    Plus,
    CheckCircle,
    XCircle,
    AlertTriangle,
    RefreshCw,
    Trash2
  } from 'lucide-svelte';
  import { systemGroupApi, rmfApi, templateApi, nessusApi } from '$lib/services/rmf/api';
  import type { SystemGroup } from '$lib/services/rmf/api';

  let systemGroups: SystemGroup[] = [];
  let loading = true;

  // Checklist Upload State
  let selectedSystemId = '';
  let newSystemName = '';
  let checklistFiles: File[] = [];
  let uploadingChecklists = false;
  let checklistUploadResults: { file: string; success: boolean; message: string }[] = [];

  // Template Upload State (Admin only)
  let templateFile: File | null = null;
  let templateTitle = '';
  let templateDescription = '';
  let uploadingTemplate = false;
  let templateUploadResult: { success: boolean; message: string } | null = null;

  // Nessus Upload State
  let nessusSystemId = '';
  let nessusFile: File | null = null;
  let uploadingNessus = false;
  let nessusUploadResult: { success: boolean; message: string } | null = null;

  async function loadSystemGroups() {
    loading = true;
    try {
      const res = await systemGroupApi.list();
      if (res.success) {
        systemGroups = res.results || [];
      }
    } catch (error) {
      console.error('Error loading systems:', error);
    } finally {
      loading = false;
    }
  }

  function handleChecklistFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      checklistFiles = Array.from(input.files).slice(0, 10); // Max 10 files
    }
  }

  function handleTemplateFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      templateFile = input.files[0];
      if (!templateTitle) {
        templateTitle = templateFile.name.replace('.ckl', '').replace('.xml', '');
      }
    }
  }

  function handleNessusFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      nessusFile = input.files[0];
    }
  }

  function removeChecklistFile(index: number) {
    checklistFiles = checklistFiles.filter((_, i) => i !== index);
  }

  async function uploadChecklists() {
    if (checklistFiles.length === 0) return;

    let systemId = selectedSystemId;

    // Create new system if needed
    if (!systemId && newSystemName) {
      try {
        const res = await systemGroupApi.create({ name: newSystemName, lifecycle_state: 'draft' });
        if (res.success) {
          systemId = res.data.id;
          systemGroups = [...systemGroups, res.data];
        }
      } catch (error) {
        console.error('Error creating system:', error);
        return;
      }
    }

    uploadingChecklists = true;
    checklistUploadResults = [];

    try {
      if (checklistFiles.length === 1) {
        const result = await rmfApi.uploadCklFile(checklistFiles[0], systemId || undefined);
        checklistUploadResults = [{
          file: checklistFiles[0].name,
          success: result.success,
          message: result.success ? 'Uploaded successfully' : result.error || 'Upload failed'
        }];
      } else {
        const result = await rmfApi.uploadMultipleCklFiles(checklistFiles, systemId || undefined);
        if (result.success) {
          checklistUploadResults = checklistFiles.map((f, i) => ({
            file: f.name,
            success: true,
            message: 'Uploaded successfully'
          }));
        } else {
          checklistUploadResults = checklistFiles.map((f) => ({
            file: f.name,
            success: false,
            message: result.error || 'Upload failed'
          }));
        }
      }
    } catch (error) {
      checklistUploadResults = checklistFiles.map((f) => ({
        file: f.name,
        success: false,
        message: 'Upload failed'
      }));
    } finally {
      uploadingChecklists = false;
    }
  }

  async function uploadTemplate() {
    if (!templateFile || !templateTitle) return;

    uploadingTemplate = true;
    templateUploadResult = null;

    try {
      const result = await templateApi.upload(templateFile, templateTitle, templateDescription);
      templateUploadResult = {
        success: result.success,
        message: result.success ? 'Template uploaded successfully' : result.error || 'Upload failed'
      };
      if (result.success) {
        templateFile = null;
        templateTitle = '';
        templateDescription = '';
      }
    } catch (error) {
      templateUploadResult = { success: false, message: 'Upload failed' };
    } finally {
      uploadingTemplate = false;
    }
  }

  async function uploadNessus() {
    if (!nessusFile || !nessusSystemId) return;

    uploadingNessus = true;
    nessusUploadResult = null;

    try {
      const result = await nessusApi.upload(nessusSystemId, nessusFile);
      nessusUploadResult = {
        success: result.success,
        message: result.success ? 'Nessus scan uploaded successfully' : result.error || 'Upload failed'
      };
      if (result.success) {
        nessusFile = null;
      }
    } catch (error) {
      nessusUploadResult = { success: false, message: 'Upload failed' };
    } finally {
      uploadingNessus = false;
    }
  }

  onMount(() => {
    loadSystemGroups();
  });
</script>

<svelte:head>
  <title>RMF Upload - CISO Assistant</title>
</svelte:head>

<div class="rmf-upload min-h-screen bg-gray-50">
  <!-- Header -->
  <div class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Upload class="text-indigo-600" size={28} />
          Upload Files
        </h1>
        <p class="mt-1 text-sm text-gray-600">
          Import CKL checklists, SCAP results, or Nessus scans
        </p>
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
    <!-- Checklist Upload Section -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <FileText class="text-green-600" size={20} />
          Checklist Upload
        </h2>
        <p class="text-sm text-gray-600">Upload CKL or SCAP XML files (up to 10 at once)</p>
      </div>
      <div class="p-6 space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">System Package</label>
            <select
              bind:value={selectedSystemId}
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">Select existing or create new</option>
              {#each systemGroups as system}
                <option value={system.id}>{system.name}</option>
              {/each}
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Or Create New System</label>
            <input
              type="text"
              bind:value={newSystemName}
              disabled={!!selectedSystemId}
              placeholder="New system name"
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
            />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">CKL/XML Files</label>
          <div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-indigo-400 transition-colors">
            <input
              type="file"
              accept=".ckl,.xml"
              multiple
              onchange={handleChecklistFileSelect}
              class="hidden"
              id="checklist-files"
            />
            <label for="checklist-files" class="cursor-pointer">
              <Upload size={32} class="mx-auto text-gray-400 mb-2" />
              <p class="text-gray-600">Click to select files or drag and drop</p>
              <p class="text-xs text-gray-500 mt-1">CKL or SCAP XML files (max 10)</p>
            </label>
          </div>
        </div>

        {#if checklistFiles.length > 0}
          <div class="space-y-2">
            <p class="text-sm font-medium text-gray-700">{checklistFiles.length} file(s) selected:</p>
            {#each checklistFiles as file, i}
              <div class="flex items-center justify-between bg-gray-50 px-3 py-2 rounded">
                <span class="text-sm text-gray-700">{file.name}</span>
                <button onclick={() => removeChecklistFile(i)} class="text-red-600 hover:text-red-800">
                  <Trash2 size={16} />
                </button>
              </div>
            {/each}
          </div>
        {/if}

        {#if checklistUploadResults.length > 0}
          <div class="space-y-2">
            {#each checklistUploadResults as result}
              <div class="flex items-center gap-2 px-3 py-2 rounded {result.success ? 'bg-green-50' : 'bg-red-50'}">
                {#if result.success}
                  <CheckCircle size={16} class="text-green-600" />
                {:else}
                  <XCircle size={16} class="text-red-600" />
                {/if}
                <span class="text-sm {result.success ? 'text-green-700' : 'text-red-700'}">
                  {result.file}: {result.message}
                </span>
              </div>
            {/each}
          </div>
        {/if}

        <button
          onclick={uploadChecklists}
          disabled={checklistFiles.length === 0 || (!selectedSystemId && !newSystemName) || uploadingChecklists}
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
        >
          {#if uploadingChecklists}
            <RefreshCw size={16} class="mr-2 animate-spin" />
            Uploading...
          {:else}
            <Upload size={16} class="mr-2" />
            Upload Checklists
          {/if}
        </button>
      </div>
    </div>

    <!-- Template Upload Section (Admin) -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <FileText class="text-purple-600" size={20} />
          Template Upload
          <span class="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">Admin</span>
        </h2>
        <p class="text-sm text-gray-600">Upload a CKL file as a reusable template</p>
      </div>
      <div class="p-6 space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Template Title</label>
            <input
              type="text"
              bind:value={templateTitle}
              placeholder="e.g., Windows Server 2019 DC STIG"
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-purple-500 focus:border-purple-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">CKL File</label>
            <input
              type="file"
              accept=".ckl,.xml"
              onchange={handleTemplateFileSelect}
              class="w-full border border-gray-300 rounded-md px-3 py-2"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Description (optional)</label>
          <textarea
            bind:value={templateDescription}
            rows="2"
            placeholder="Template description..."
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-purple-500 focus:border-purple-500"
          ></textarea>
        </div>

        {#if templateUploadResult}
          <div class="flex items-center gap-2 px-3 py-2 rounded {templateUploadResult.success ? 'bg-green-50' : 'bg-red-50'}">
            {#if templateUploadResult.success}
              <CheckCircle size={16} class="text-green-600" />
            {:else}
              <XCircle size={16} class="text-red-600" />
            {/if}
            <span class="text-sm {templateUploadResult.success ? 'text-green-700' : 'text-red-700'}">
              {templateUploadResult.message}
            </span>
          </div>
        {/if}

        <button
          onclick={uploadTemplate}
          disabled={!templateFile || !templateTitle || uploadingTemplate}
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50"
        >
          {#if uploadingTemplate}
            <RefreshCw size={16} class="mr-2 animate-spin" />
            Uploading...
          {:else}
            <Upload size={16} class="mr-2" />
            Upload Template
          {/if}
        </button>
      </div>
    </div>

    <!-- Nessus Upload Section -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <AlertTriangle class="text-orange-600" size={20} />
          Nessus / ACAS Upload
        </h2>
        <p class="text-sm text-gray-600">Upload Nessus scan results (XML format)</p>
      </div>
      <div class="p-6 space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">System Package</label>
            <select
              bind:value={nessusSystemId}
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-orange-500 focus:border-orange-500"
            >
              <option value="">Select a System Package</option>
              {#each systemGroups as system}
                <option value={system.id}>{system.name}</option>
              {/each}
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Nessus XML File</label>
            <input
              type="file"
              accept=".nessus,.xml"
              onchange={handleNessusFileSelect}
              class="w-full border border-gray-300 rounded-md px-3 py-2"
            />
          </div>
        </div>

        {#if nessusUploadResult}
          <div class="flex items-center gap-2 px-3 py-2 rounded {nessusUploadResult.success ? 'bg-green-50' : 'bg-red-50'}">
            {#if nessusUploadResult.success}
              <CheckCircle size={16} class="text-green-600" />
            {:else}
              <XCircle size={16} class="text-red-600" />
            {/if}
            <span class="text-sm {nessusUploadResult.success ? 'text-green-700' : 'text-red-700'}">
              {nessusUploadResult.message}
            </span>
          </div>
        {/if}

        <button
          onclick={uploadNessus}
          disabled={!nessusFile || !nessusSystemId || uploadingNessus}
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 disabled:opacity-50"
        >
          {#if uploadingNessus}
            <RefreshCw size={16} class="mr-2 animate-spin" />
            Uploading...
          {:else}
            <Upload size={16} class="mr-2" />
            Upload Nessus Scan
          {/if}
        </button>
      </div>
    </div>
  </div>
</div>
