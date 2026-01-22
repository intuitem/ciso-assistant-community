<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Upload, FileText, AlertCircle, CheckCircle, X } from 'lucide-svelte';

  export let accept = '.ckl,.xml';
  export let multiple = false;
  export let maxSize = 30 * 1024 * 1024; // 30MB
  export let disabled = false;
  export let uploading = false;
  export let dragActive = false;

  const dispatch = createEventDispatcher<{
    fileSelected: { file: File; files: FileList };
    uploadStart: { file: File };
    uploadProgress: { file: File; progress: number };
    uploadComplete: { file: File; result: any };
    uploadError: { file: File; error: string };
  }>();

  let fileInput: HTMLInputElement;
  let dropZone: HTMLElement;

  function handleDragEnter(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    dragActive = true;
  }

  function handleDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    dragActive = false;
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    dragActive = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      handleFiles(files);
    }
  }

  function handleFileInput(event: Event) {
    const target = event.target as HTMLInputElement;
    const files = target.files;
    if (files && files.length > 0) {
      handleFiles(files);
    }
  }

  function handleFiles(files: FileList) {
    // Validate files
    const validFiles: File[] = [];
    const errors: string[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];

      // Check file size
      if (file.size > maxSize) {
        errors.push(`${file.name}: File size exceeds ${maxSize / (1024 * 1024)}MB limit`);
        continue;
      }

      // Check file type
      const allowedExtensions = accept.split(',').map(ext => ext.trim().toLowerCase());
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!allowedExtensions.includes(fileExtension)) {
        errors.push(`${file.name}: Invalid file type. Allowed: ${accept}`);
        continue;
      }

      validFiles.push(file);
    }

    if (errors.length > 0) {
      // Dispatch error for invalid files
      errors.forEach(error => {
        dispatch('uploadError', { file: null as any, error });
      });
    }

    if (validFiles.length > 0) {
      const file = multiple ? null : validFiles[0];
      dispatch('fileSelected', { file: file as File, files });

      // If single file, start upload automatically
      if (!multiple && validFiles.length === 1) {
        dispatch('uploadStart', { file: validFiles[0] });
      }
    }
  }

  function openFileDialog() {
    fileInput?.click();
  }

  function clearSelection() {
    if (fileInput) {
      fileInput.value = '';
    }
  }

  export function triggerFileSelect() {
    openFileDialog();
  }

  export function reset() {
    clearSelection();
    dragActive = false;
  }
</script>

<div class="rmf-file-upload">
  <div
    bind:this={dropZone}
    class="upload-zone"
    class:drag-active={dragActive}
    class:disabled
    on:dragenter={handleDragEnter}
    on:dragleave={handleDragLeave}
    on:dragover={handleDragOver}
    on:drop={handleDrop}
    on:click={openFileDialog}
    role="button"
    tabindex="0"
    on:keydown={(e) => e.key === 'Enter' && openFileDialog()}
  >
    <input
      bind:this={fileInput}
      type="file"
      {accept}
      {multiple}
      {disabled}
      on:change={handleFileInput}
      style="display: none;"
    />

    <div class="upload-content">
      {#if uploading}
        <div class="uploading-indicator">
          <div class="spinner"></div>
          <p>Uploading...</p>
        </div>
      {:else}
        <Upload size={48} class="upload-icon" />
        <div class="upload-text">
          <p class="primary-text">
            {#if multiple}
              Drop CKL files here or click to browse
            {:else}
              Drop a CKL file here or click to browse
            {/if}
          </p>
          <p class="secondary-text">
            Supports: {accept} (max {maxSize / (1024 * 1024)}MB each)
          </p>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .rmf-file-upload {
    width: 100%;
  }

  .upload-zone {
    border: 2px dashed #cbd5e0;
    border-radius: 8px;
    padding: 2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    background-color: #f7fafc;
  }

  .upload-zone:hover:not(.disabled) {
    border-color: #3182ce;
    background-color: #edf2f7;
  }

  .upload-zone.drag-active {
    border-color: #3182ce;
    background-color: #ebf8ff;
    transform: scale(1.02);
  }

  .upload-zone.disabled {
    cursor: not-allowed;
    opacity: 0.6;
    border-color: #a0aec0;
    background-color: #f7fafc;
  }

  .upload-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }

  .upload-icon {
    color: #718096;
    margin-bottom: 0.5rem;
  }

  .upload-zone:hover:not(.disabled) .upload-icon {
    color: #3182ce;
  }

  .upload-text {
    color: #4a5568;
  }

  .primary-text {
    font-weight: 600;
    margin: 0;
    font-size: 1.1rem;
  }

  .secondary-text {
    font-size: 0.9rem;
    margin: 0.25rem 0 0 0;
    color: #718096;
  }

  .uploading-indicator {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #e2e8f0;
    border-top: 4px solid #3182ce;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .uploading-indicator p {
    margin: 0;
    font-weight: 500;
    color: #3182ce;
  }
</style>
