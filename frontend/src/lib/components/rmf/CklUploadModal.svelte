<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { X, Upload, CheckCircle, AlertCircle, Loader } from 'lucide-svelte';
  import { rmfApi, type StigChecklist } from '$lib/services/rmf/api';
  import FileUpload from './FileUpload.svelte';
  import Modal from '$lib/components/Modal/Modal.svelte';

  export let show = false;
  export let systemGroupId: string | null = null;

  const dispatch = createEventDispatcher<{
    uploadComplete: { checklist: StigChecklist };
    close: void;
  }>();

  let uploading = false;
  let uploadProgress = 0;
  let uploadStatus: 'idle' | 'uploading' | 'success' | 'error' = 'idle';
  let uploadMessage = '';
  let selectedFile: File | null = null;

  let fileUpload: FileUpload;

  function handleFileSelected(event: CustomEvent<{ file: File; files: FileList }>) {
    selectedFile = event.detail.file;
    uploadStatus = 'idle';
    uploadMessage = '';
  }

  async function handleUpload() {
    if (!selectedFile) return;

    uploading = true;
    uploadProgress = 0;
    uploadStatus = 'uploading';
    uploadMessage = 'Uploading CKL file...';

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        uploadProgress += Math.random() * 15;
        if (uploadProgress > 90) {
          clearInterval(progressInterval);
        }
      }, 200);

      // Upload the file
      const response = await rmfApi.uploadCklFile(selectedFile, systemGroupId || undefined);

      clearInterval(progressInterval);
      uploadProgress = 100;

      if (response.success && response.data) {
        uploadStatus = 'success';
        uploadMessage = 'CKL file uploaded successfully!';

        // Fetch the created checklist
        const checklistResponse = await rmfApi.stigChecklist.retrieve(response.data.checklist_id);
        if (checklistResponse.success && checklistResponse.data) {
          setTimeout(() => {
            dispatch('uploadComplete', { checklist: checklistResponse.data });
            handleClose();
          }, 1500);
        }
      } else {
        throw new Error(response.message || 'Upload failed');
      }

    } catch (error) {
      uploadStatus = 'error';
      uploadMessage = error instanceof Error ? error.message : 'Upload failed';
      console.error('CKL upload error:', error);
    } finally {
      uploading = false;
    }
  }

  function handleClose() {
    show = false;
    uploading = false;
    uploadProgress = 0;
    uploadStatus = 'idle';
    uploadMessage = '';
    selectedFile = null;
    fileUpload?.reset();
    dispatch('close');
  }

  function getStatusIcon() {
    switch (uploadStatus) {
      case 'success':
        return CheckCircle;
      case 'error':
        return AlertCircle;
      case 'uploading':
        return Loader;
      default:
        return Upload;
    }
  }

  function getStatusColor() {
    switch (uploadStatus) {
      case 'success':
        return 'text-green-600';
      case 'error':
        return 'text-red-600';
      case 'uploading':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  }

  $: statusIcon = getStatusIcon();
  $: statusColor = getStatusColor();
</script>

<Modal {show} on:close={handleClose} size="lg">
  <div slot="header" class="flex items-center justify-between">
    <h3 class="text-lg font-semibold text-gray-900">Upload STIG Checklist (CKL)</h3>
    <button
      on:click={handleClose}
      class="text-gray-400 hover:text-gray-600 transition-colors"
    >
      <X size={20} />
    </button>
  </div>

  <div slot="body" class="space-y-6">
    {#if systemGroupId}
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <CheckCircle class="h-5 w-5 text-blue-400" />
          </div>
          <div class="ml-3">
            <p class="text-sm text-blue-700">
              Checklist will be automatically assigned to the selected system group.
            </p>
          </div>
        </div>
      </div>
    {/if}

    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Select CKL File
        </label>
        <FileUpload
          bind:this={fileUpload}
          accept=".ckl,.xml"
          multiple={false}
          disabled={uploading}
          on:fileSelected={handleFileSelected}
        />
      </div>

      {#if selectedFile}
        <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <FileText size={20} class="text-gray-500" />
              <div>
                <p class="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                <p class="text-xs text-gray-500">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                </p>
              </div>
            </div>
            {#if uploadStatus === 'idle'}
              <button
                on:click={handleUpload}
                disabled={uploading}
                class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {#if uploading}
                  <Loader size={16} class="animate-spin mr-2" />
                  Uploading...
                {:else}
                  <Upload size={16} class="mr-2" />
                  Upload
                {/if}
              </button>
            {/if}
          </div>

          {#if uploading || uploadStatus !== 'idle'}
            <div class="mt-4">
              <div class="flex items-center space-x-2 mb-2">
                <svelte:component this={statusIcon} size={16} class={statusColor} />
                <span class="text-sm font-medium {statusColor}">{uploadMessage}</span>
              </div>

              {#if uploading}
                <div class="w-full bg-gray-200 rounded-full h-2">
                  <div
                    class="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style="width: {uploadProgress}%"
                  ></div>
                </div>
                <p class="text-xs text-gray-500 mt-1">{uploadProgress.toFixed(0)}% complete</p>
              {/if}
            </div>
          {/if}
        </div>
      {/if}

      <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <AlertCircle class="h-5 w-5 text-yellow-400" />
          </div>
          <div class="ml-3">
            <h4 class="text-sm font-medium text-yellow-800">CKL File Requirements</h4>
            <div class="mt-2 text-sm text-yellow-700">
              <ul class="list-disc list-inside space-y-1">
                <li>File must be in CKL format (.ckl or .xml)</li>
                <li>Maximum file size: 30MB</li>
                <li>Supported versions: CKL 1.0 and 2.0</li>
                <li>Exported from SCAP tools (SCC, STIG Viewer, OpenSCAP)</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div slot="footer" class="flex justify-end space-x-3">
    <button
      on:click={handleClose}
      class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
    >
      Cancel
    </button>
  </div>
</Modal>
