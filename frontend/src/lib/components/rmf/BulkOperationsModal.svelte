<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { X, CheckCircle, AlertCircle, Loader, Clock } from 'lucide-svelte';
  import { rmfApi } from '$lib/services/rmf/api';
  import Modal from '$lib/components/Modal/Modal.svelte';

  export let show = false;
  export let operationType: 'update_status' | 'update_lifecycle' | 'assign_system' = 'update_status';
  export let targetIds: string[] = [];
  export let parameters: Record<string, any> = {};

  const dispatch = createEventDispatcher<{
    operationComplete: { success: boolean; results: any };
    close: void;
  }>();

  let processing = false;
  let progress = 0;
  let status: 'idle' | 'validating' | 'processing' | 'success' | 'error' = 'idle';
  let statusMessage = '';
  let results: any = null;
  let estimatedTime = 0;

  $: operationDisplayName = getOperationDisplayName(operationType);
  $: canExecute = targetIds.length > 0 && Object.keys(parameters).length > 0;

  async function validateOperation() {
    if (!canExecute) return;

    status = 'validating';
    statusMessage = 'Validating operation parameters...';

    try {
      const response = await rmfApi.validateBulkOperation(
        operationType,
        targetIds,
        parameters
      );

      if (response.success && response.data.valid) {
        status = 'idle';
        statusMessage = `Ready to process ${targetIds.length} items`;
        estimatedTime = response.data.estimated_time_seconds || 0;
      } else {
        status = 'error';
        statusMessage = response.data.errors?.join(', ') || 'Validation failed';
      }
    } catch (error) {
      status = 'error';
      statusMessage = 'Validation failed - please check your parameters';
      console.error('Validation error:', error);
    }
  }

  async function executeOperation() {
    if (!canExecute) return;

    processing = true;
    progress = 0;
    status = 'processing';
    statusMessage = `Processing ${targetIds.length} items...`;

    try {
      // Start progress animation
      const progressInterval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress > 90) {
          clearInterval(progressInterval);
        }
      }, 200);

      let response;

      switch (operationType) {
        case 'update_status':
          response = await rmfApi.vulnerabilityFinding.bulkUpdateStatus(
            targetIds,
            parameters.status,
            parameters.finding_details,
            parameters.comments
          );
          break;
        case 'update_lifecycle':
          // This would need to be implemented in the API
          throw new Error('Lifecycle update not yet implemented');
        case 'assign_system':
          // This would need to be implemented in the API
          throw new Error('System assignment not yet implemented');
        default:
          throw new Error('Unknown operation type');
      }

      clearInterval(progressInterval);
      progress = 100;

      if (response.success) {
        status = 'success';
        statusMessage = `Successfully processed ${response.data.updated_count} of ${targetIds.length} items`;
        results = response.data;
      } else {
        throw new Error(response.message || 'Operation failed');
      }

    } catch (error) {
      status = 'error';
      statusMessage = error instanceof Error ? error.message : 'Operation failed';
      console.error('Bulk operation error:', error);
    } finally {
      processing = false;
    }
  }

  function handleClose() {
    if (!processing) {
      show = false;
      status = 'idle';
      statusMessage = '';
      results = null;
      progress = 0;
      dispatch('close');
    }
  }

  function handleComplete() {
    dispatch('operationComplete', {
      success: status === 'success',
      results
    });
    handleClose();
  }

  function getOperationDisplayName(type: string): string {
    switch (type) {
      case 'update_status':
        return 'Bulk Status Update';
      case 'update_lifecycle':
        return 'Bulk Lifecycle Update';
      case 'assign_system':
        return 'Bulk System Assignment';
      default:
        return 'Bulk Operation';
    }
  }

  function getStatusIcon() {
    switch (status) {
      case 'success':
        return CheckCircle;
      case 'error':
        return AlertCircle;
      case 'processing':
      case 'validating':
        return Loader;
      default:
        return Clock;
    }
  }

  function getStatusColor() {
    switch (status) {
      case 'success':
        return 'text-green-600';
      case 'error':
        return 'text-red-600';
      case 'processing':
      case 'validating':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  }

  $: statusIcon = getStatusIcon();
  $: statusColor = getStatusColor();

  // Validate when parameters change
  $: if (targetIds.length > 0 && Object.keys(parameters).length > 0) {
    validateOperation();
  }
</script>

<Modal {show} on:close={handleClose} size="lg">
  <div slot="header" class="flex items-center justify-between">
    <h3 class="text-lg font-semibold text-gray-900">{operationDisplayName}</h3>
    <button
      on:click={handleClose}
      disabled={processing}
      class="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
    >
      <X size={20} />
    </button>
  </div>

  <div slot="body" class="space-y-6">
    <!-- Operation Summary -->
    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <Clock class="h-5 w-5 text-blue-400" />
        </div>
        <div class="ml-3">
          <h4 class="text-sm font-medium text-blue-800">Operation Summary</h4>
          <div class="mt-2 text-sm text-blue-700">
            <ul class="list-disc list-inside space-y-1">
              <li><strong>Operation:</strong> {operationDisplayName}</li>
              <li><strong>Target Items:</strong> {targetIds.length}</li>
              {#if estimatedTime > 0}
                <li><strong>Estimated Time:</strong> {estimatedTime} seconds</li>
              {/if}
              {#each Object.entries(parameters) as [key, value]}
                <li><strong>{key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong> {value}</li>
              {/each}
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Status Display -->
    {#if status !== 'idle'}
      <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div class="flex items-center space-x-3">
          <svelte:component this={statusIcon} size={20} class={statusColor} class:rotate-180={status === 'processing' || status === 'validating'} />
          <div class="flex-1">
            <p class="text-sm font-medium {statusColor}">{statusMessage}</p>
            {#if (status === 'processing' || status === 'validating') && progress > 0}
              <div class="mt-2 w-full bg-gray-200 rounded-full h-2">
                <div
                  class="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style="width: {progress}%"
                ></div>
              </div>
              <p class="text-xs text-gray-500 mt-1">{progress.toFixed(0)}% complete</p>
            {/if}
          </div>
        </div>

        <!-- Results Display -->
        {#if status === 'success' && results}
          <div class="mt-4 p-3 bg-green-50 border border-green-200 rounded">
            <div class="flex">
              <CheckCircle class="h-5 w-5 text-green-400" />
              <div class="ml-3">
                <p class="text-sm font-medium text-green-800">Operation Completed Successfully</p>
                <div class="mt-1 text-sm text-green-700">
                  <ul class="list-disc list-inside space-y-1">
                    <li>Updated: {results.updated_count || 0} items</li>
                    <li>Requested: {results.total_requested || 0} items</li>
                    {#if results.errors && results.errors.length > 0}
                      <li>Errors: {results.errors.length}</li>
                    {/if}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        {/if}

        {#if status === 'error'}
          <div class="mt-4 p-3 bg-red-50 border border-red-200 rounded">
            <div class="flex">
              <AlertCircle class="h-5 w-5 text-red-400" />
              <div class="ml-3">
                <p class="text-sm font-medium text-red-800">Operation Failed</p>
                <p class="mt-1 text-sm text-red-700">{statusMessage}</p>
              </div>
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Warning for Large Operations -->
    {#if targetIds.length > 100}
      <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <AlertCircle class="h-5 w-5 text-yellow-400" />
          </div>
          <div class="ml-3">
            <h4 class="text-sm font-medium text-yellow-800">Large Operation Warning</h4>
            <div class="mt-2 text-sm text-yellow-700">
              <p>
                You're about to process {targetIds.length} items. This may take several minutes.
                Consider breaking this into smaller batches if you experience timeouts.
              </p>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>

  <div slot="footer" class="flex justify-end space-x-3">
    <button
      on:click={handleClose}
      disabled={processing}
      class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
    >
      {status === 'success' ? 'Close' : 'Cancel'}
    </button>

    {#if status === 'success'}
      <button
        on:click={handleComplete}
        class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
      >
        Done
      </button>
    {:else if status === 'idle' && canExecute}
      <button
        on:click={executeOperation}
        disabled={processing}
        class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
      >
        {#if processing}
          <Loader size={16} class="animate-spin mr-2" />
          Processing...
        {:else}
          Execute Operation
        {/if}
      </button>
    {/if}
  </div>
</Modal>
