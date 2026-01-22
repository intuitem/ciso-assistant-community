<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import {
    ArrowLeft,
    Download,
    FileSpreadsheet,
    Upload,
    Trash2,
    Edit,
    RefreshCw,
    ChevronUp,
    Save,
    X,
    AlertTriangle,
    CheckCircle,
    XCircle,
    Clock,
    Info
  } from 'lucide-svelte';
  import DonutChart from '$lib/components/Chart/DonutChart.svelte';
  import BarChart from '$lib/components/Chart/BarChart.svelte';
  import {
    stigChecklistApi,
    vulnerabilityFindingApi,
    checklistScoreApi,
    exportApi,
    cciApi
  } from '$lib/services/rmf/api';
  import type {
    StigChecklist,
    VulnerabilityFinding,
    ChecklistScore,
    CCIItem
  } from '$lib/services/rmf/api';

  // State
  let checklist: StigChecklist | null = null;
  let findings: VulnerabilityFinding[] = [];
  let score: ChecklistScore | null = null;
  let loading = true;
  let saving = false;
  let showEditModal = false;
  let upgradeAvailable: { version: string; release: string } | null = null;

  // Filtering state
  let statusFilters = {
    open: true,
    notAFinding: true,
    notApplicable: true,
    notReviewed: true
  };
  let severityFilters = {
    cat1: true,
    cat2: true,
    cat3: true
  };

  // Selected vulnerability state
  let selectedVuln: VulnerabilityFinding | null = null;
  let cciInfo: CCIItem[] = [];
  let vulnFormData = {
    status: '',
    comments: '',
    findingDetails: '',
    severityOverride: '',
    severityJustification: ''
  };
  let bulkUpdateEnabled = false;

  // Computed filtered findings
  $: filteredFindings = findings.filter((f) => {
    const statusMatch =
      (statusFilters.open && f.vulnerability_status.status === 'open') ||
      (statusFilters.notAFinding && f.vulnerability_status.status === 'not_a_finding') ||
      (statusFilters.notApplicable && f.vulnerability_status.status === 'not_applicable') ||
      (statusFilters.notReviewed && f.vulnerability_status.status === 'not_reviewed');

    const severityMatch =
      (severityFilters.cat1 && f.severity.category === 'cat1') ||
      (severityFilters.cat2 && f.severity.category === 'cat2') ||
      (severityFilters.cat3 && f.severity.category === 'cat3');

    return statusMatch && severityMatch;
  });

  // Chart data
  $: severityChartData = score
    ? [
        { name: 'Open', value: score.totalOpen },
        { name: 'Not a Finding', value: score.totalNotAFinding },
        { name: 'Not Applicable', value: score.totalNotApplicable },
        { name: 'Not Reviewed', value: score.totalNotReviewed }
      ]
    : [];

  $: categoryChartData = score
    ? [
        { name: 'CAT I', value: score.totalCat1Open + score.totalCat1NotAFinding + score.totalCat1NotApplicable + score.totalCat1NotReviewed },
        { name: 'CAT II', value: score.totalCat2Open + score.totalCat2NotAFinding + score.totalCat2NotApplicable + score.totalCat2NotReviewed },
        { name: 'CAT III', value: score.totalCat3Open + score.totalCat3NotAFinding + score.totalCat3NotApplicable + score.totalCat3NotReviewed }
      ]
    : [];

  $: barChartLabels = ['Open', 'Not a Finding', 'Not Applicable', 'Not Reviewed'];
  $: barChartValues = score
    ? [
        { value: score.totalOpen, itemStyle: { color: '#dc2626' } },
        { value: score.totalNotAFinding, itemStyle: { color: '#22c55e' } },
        { value: score.totalNotApplicable, itemStyle: { color: '#9ca3af' } },
        { value: score.totalNotReviewed, itemStyle: { color: '#3b82f6' } }
      ]
    : [];

  async function loadData() {
    const id = $page.params.id;
    loading = true;

    try {
      const [checklistRes, findingsRes, scoreRes] = await Promise.all([
        stigChecklistApi.retrieve(id),
        stigChecklistApi.getFindings(id),
        stigChecklistApi.getScore(id)
      ]);

      if (checklistRes.success) checklist = checklistRes.data;
      if (findingsRes.success) findings = findingsRes.results || [];
      if (scoreRes.success) score = scoreRes.data;

      // Check for upgrade
      const upgradeRes = await fetch(`/api/v1/rmf/checklists/${id}/check-upgrade/`);
      if (upgradeRes.ok) {
        const data = await upgradeRes.json();
        if (data.available) upgradeAvailable = data;
      }
    } catch (error) {
      console.error('Error loading checklist:', error);
    } finally {
      loading = false;
    }
  }

  function getVulnButtonClass(finding: VulnerabilityFinding): string {
    const status = finding.vulnerability_status.status;
    const severity = finding.severity.category;

    if (status === 'not_reviewed') return 'bg-blue-100 text-blue-800 hover:bg-blue-200';
    if (status === 'not_applicable') return 'bg-gray-100 text-gray-800 hover:bg-gray-200';
    if (status === 'not_a_finding') return 'bg-green-100 text-green-800 hover:bg-green-200';
    if (status === 'open') {
      if (severity === 'cat1') return 'bg-red-500 text-white hover:bg-red-600';
      if (severity === 'cat2') return 'bg-orange-400 text-white hover:bg-orange-500';
      return 'bg-yellow-400 text-yellow-900 hover:bg-yellow-500';
    }
    return 'bg-gray-100 text-gray-800 hover:bg-gray-200';
  }

  async function selectVulnerability(finding: VulnerabilityFinding) {
    selectedVuln = finding;
    vulnFormData = {
      status: finding.vulnerability_status.status,
      comments: finding.vulnerability_status.comments || '',
      findingDetails: finding.vulnerability_status.finding_details || '',
      severityOverride: finding.vulnerability_status.severity_override || '',
      severityJustification: finding.vulnerability_status.severity_justification || ''
    };

    // Load CCI info
    if (finding.cciIds && finding.cciIds.length > 0) {
      cciInfo = [];
      for (const cciId of finding.cciIds) {
        try {
          const res = await cciApi.get(cciId);
          if (res.success) cciInfo = [...cciInfo, res.data];
        } catch (e) {
          console.error('Error loading CCI:', e);
        }
      }
    }
  }

  async function saveVulnerability() {
    if (!selectedVuln) return;
    saving = true;

    try {
      const res = await vulnerabilityFindingApi.updateStatus(
        selectedVuln.id,
        vulnFormData.status,
        vulnFormData.findingDetails,
        vulnFormData.comments
      );

      if (res.success) {
        // Update local state
        const idx = findings.findIndex((f) => f.id === selectedVuln!.id);
        if (idx !== -1) {
          findings[idx] = {
            ...findings[idx],
            vulnerability_status: {
              ...findings[idx].vulnerability_status,
              status: vulnFormData.status as any,
              comments: vulnFormData.comments,
              finding_details: vulnFormData.findingDetails
            }
          };
          findings = [...findings]; // Trigger reactivity
        }

        // Refresh score
        const scoreRes = await stigChecklistApi.getScore($page.params.id);
        if (scoreRes.success) score = scoreRes.data;
      }
    } catch (error) {
      console.error('Error saving vulnerability:', error);
    } finally {
      saving = false;
    }
  }

  function setScoreFilter(status: string, severity: string) {
    // Reset all filters
    statusFilters = { open: false, notAFinding: false, notApplicable: false, notReviewed: false };
    severityFilters = { cat1: false, cat2: false, cat3: false };

    // Set status filter
    if (status === 'open') statusFilters.open = true;
    else if (status === 'naf') statusFilters.notAFinding = true;
    else if (status === 'na') statusFilters.notApplicable = true;
    else if (status === 'nr') statusFilters.notReviewed = true;

    // Set severity filter
    if (severity === 'all' || severity === 'cat1') severityFilters.cat1 = true;
    if (severity === 'all' || severity === 'cat2') severityFilters.cat2 = true;
    if (severity === 'all' || severity === 'cat3') severityFilters.cat3 = true;

    // Scroll to vulnerabilities section
    document.getElementById('vulnerabilities-section')?.scrollIntoView({ behavior: 'smooth' });
  }

  async function downloadCkl() {
    await exportApi.downloadChecklistCkl($page.params.id);
  }

  async function downloadXlsx() {
    await exportApi.downloadChecklistXlsx($page.params.id);
  }

  async function upgradeChecklist() {
    try {
      const res = await fetch(`/api/v1/rmf/checklists/${$page.params.id}/upgrade/`, {
        method: 'POST'
      });
      if (res.ok) {
        await loadData();
        upgradeAvailable = null;
      }
    } catch (error) {
      console.error('Error upgrading checklist:', error);
    }
  }

  onMount(() => {
    loadData();
  });
</script>

<svelte:head>
  <title>{checklist?.hostName || 'Checklist'} - RMF - CISO Assistant</title>
</svelte:head>

<div class="single-checklist min-h-screen bg-gray-50">
  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
    </div>
  {:else if checklist}
    <!-- Header -->
    <div class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <button
              onclick={() => goto('/rmf/checklists')}
              class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <h1 class="text-xl font-bold text-gray-900">{checklist.stigType}</h1>
              <p class="text-sm text-gray-500">{checklist.hostName}</p>
            </div>
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
              onclick={downloadCkl}
              class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <Download size={16} class="mr-2" />
              CKL
            </button>
            <button
              onclick={downloadXlsx}
              class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <FileSpreadsheet size={16} class="mr-2" />
              Excel
            </button>
            <button
              onclick={() => goto(`/rmf/checklists/${$page.params.id}/upload`)}
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

        {#if upgradeAvailable}
          <div class="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
            <div class="flex items-center gap-2 text-blue-800">
              <ChevronUp size={20} />
              <span>Updated checklist available: V{upgradeAvailable.version} {upgradeAvailable.release}</span>
            </div>
            <button
              onclick={upgradeChecklist}
              class="px-3 py-1 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
            >
              Upgrade
            </button>
          </div>
        {/if}
      </div>
    </div>

    <div class="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <!-- Asset Information Card -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Asset Information</h2>
        </div>
        <div class="p-6 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 text-sm">
          <div>
            <span class="font-medium text-gray-500">System:</span>
            <p class="text-gray-900">{checklist.systemGroupId || 'Unassigned'}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">Host:</span>
            <p class="text-gray-900">{checklist.hostName}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">STIG Title:</span>
            <p class="text-gray-900">{checklist.stigType}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">Version:</span>
            <p class="text-gray-900">{checklist.version}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">Release:</span>
            <p class="text-gray-900">{checklist.stigRelease}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">FQDN:</span>
            <p class="text-gray-900">{checklist.assetInfo?.fqdn || '-'}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">Marking:</span>
            <p class="text-gray-900">{checklist.assetInfo?.marking || '-'}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">IP:</span>
            <p class="text-gray-900">{checklist.assetIpAddresses?.join(', ') || '-'}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">MAC:</span>
            <p class="text-gray-900">{checklist.assetMacAddresses?.join(', ') || '-'}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">Tech Area:</span>
            <p class="text-gray-900">{checklist.assetInfo?.techArea || '-'}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">Asset Type:</span>
            <p class="text-gray-900">{checklist.assetInfo?.assetType || '-'}</p>
          </div>
          <div>
            <span class="font-medium text-gray-500">Role:</span>
            <p class="text-gray-900">{checklist.assetInfo?.role || '-'}</p>
          </div>
          {#if checklist.isWebDatabase}
            <div>
              <span class="font-medium text-gray-500">Web/DB:</span>
              <p class="text-gray-900">Yes</p>
            </div>
            <div>
              <span class="font-medium text-gray-500">Site:</span>
              <p class="text-gray-900">{checklist.webDatabaseSite || '-'}</p>
            </div>
            <div>
              <span class="font-medium text-gray-500">Instance:</span>
              <p class="text-gray-900">{checklist.webDatabaseInstance || '-'}</p>
            </div>
          {/if}
          <div>
            <span class="font-medium text-gray-500">Tags:</span>
            <p class="text-gray-900">{checklist.tags?.join(', ') || '-'}</p>
          </div>
        </div>
      </div>

      <!-- Score Summary Table - Clickable -->
      {#if score}
        <div class="bg-white rounded-lg shadow-sm border border-gray-200">
          <div class="px-6 py-4 border-b border-gray-200">
            <h2 class="text-lg font-semibold text-gray-900">Score Summary</h2>
            <p class="text-xs text-gray-500">Click any cell to filter vulnerabilities</p>
          </div>
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Open</th>
                  <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Not a Finding</th>
                  <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">N/A</th>
                  <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Not Reviewed</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr>
                  <td class="px-4 py-3 font-medium text-gray-900">Total</td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('open', 'all')} class="px-3 py-1 bg-red-100 text-red-800 rounded-full hover:bg-red-200 font-medium">
                      {score.totalOpen}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('naf', 'all')} class="px-3 py-1 bg-green-100 text-green-800 rounded-full hover:bg-green-200 font-medium">
                      {score.totalNotAFinding}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('na', 'all')} class="px-3 py-1 bg-gray-100 text-gray-800 rounded-full hover:bg-gray-200 font-medium">
                      {score.totalNotApplicable}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('nr', 'all')} class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full hover:bg-blue-200 font-medium">
                      {score.totalNotReviewed}
                    </button>
                  </td>
                </tr>
                <tr class="bg-red-50">
                  <td class="px-4 py-3 font-medium text-red-900">CAT I</td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('open', 'cat1')} class="px-3 py-1 bg-red-200 text-red-900 rounded-full hover:bg-red-300 font-medium">
                      {score.totalCat1Open}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('naf', 'cat1')} class="px-3 py-1 bg-green-100 text-green-800 rounded-full hover:bg-green-200">
                      {score.totalCat1NotAFinding}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('na', 'cat1')} class="px-3 py-1 bg-gray-100 text-gray-800 rounded-full hover:bg-gray-200">
                      {score.totalCat1NotApplicable}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('nr', 'cat1')} class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full hover:bg-blue-200">
                      {score.totalCat1NotReviewed}
                    </button>
                  </td>
                </tr>
                <tr class="bg-orange-50">
                  <td class="px-4 py-3 font-medium text-orange-900">CAT II</td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('open', 'cat2')} class="px-3 py-1 bg-orange-200 text-orange-900 rounded-full hover:bg-orange-300 font-medium">
                      {score.totalCat2Open}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('naf', 'cat2')} class="px-3 py-1 bg-green-100 text-green-800 rounded-full hover:bg-green-200">
                      {score.totalCat2NotAFinding}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('na', 'cat2')} class="px-3 py-1 bg-gray-100 text-gray-800 rounded-full hover:bg-gray-200">
                      {score.totalCat2NotApplicable}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('nr', 'cat2')} class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full hover:bg-blue-200">
                      {score.totalCat2NotReviewed}
                    </button>
                  </td>
                </tr>
                <tr class="bg-yellow-50">
                  <td class="px-4 py-3 font-medium text-yellow-900">CAT III</td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('open', 'cat3')} class="px-3 py-1 bg-yellow-200 text-yellow-900 rounded-full hover:bg-yellow-300 font-medium">
                      {score.totalCat3Open}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('naf', 'cat3')} class="px-3 py-1 bg-green-100 text-green-800 rounded-full hover:bg-green-200">
                      {score.totalCat3NotAFinding}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('na', 'cat3')} class="px-3 py-1 bg-gray-100 text-gray-800 rounded-full hover:bg-gray-200">
                      {score.totalCat3NotApplicable}
                    </button>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button onclick={() => setScoreFilter('nr', 'cat3')} class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full hover:bg-blue-200">
                      {score.totalCat3NotReviewed}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      {/if}

      <!-- Vulnerability Filter -->
      <div id="vulnerabilities-section" class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div class="flex flex-wrap items-center gap-4">
          <span class="text-sm font-medium text-gray-700">Filter:</span>
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-500">Status:</span>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={statusFilters.notAFinding} class="rounded border-gray-300 text-green-600" />
              <span class="ml-1 text-sm text-green-700">NaF</span>
            </label>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={statusFilters.open} class="rounded border-gray-300 text-red-600" />
              <span class="ml-1 text-sm text-red-700">Open</span>
            </label>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={statusFilters.notApplicable} class="rounded border-gray-300 text-gray-600" />
              <span class="ml-1 text-sm text-gray-700">N/A</span>
            </label>
            <label class="inline-flex items-center">
              <input type="checkbox" bind:checked={statusFilters.notReviewed} class="rounded border-gray-300 text-blue-600" />
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
          <span class="text-sm text-gray-500">({filteredFindings.length} of {findings.length})</span>
        </div>
      </div>

      <!-- 3-Column Vulnerability Layout -->
      <div class="grid grid-cols-12 gap-4">
        <!-- Column 1: Vulnerability IDs Tree -->
        <div class="col-span-12 md:col-span-2 bg-white rounded-lg shadow-sm border border-gray-200 p-4 max-h-[600px] overflow-y-auto">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">Vulnerabilities</h3>
          <div class="space-y-1">
            {#each filteredFindings as finding}
              <button
                onclick={() => selectVulnerability(finding)}
                class="w-full text-left px-2 py-1 rounded text-xs font-mono transition-colors {getVulnButtonClass(finding)} {selectedVuln?.id === finding.id ? 'ring-2 ring-indigo-500' : ''}"
                title={finding.ruleTitle}
              >
                {finding.vulnId}
              </button>
            {/each}
          </div>
        </div>

        <!-- Column 2: Vulnerability Details -->
        <div class="col-span-12 md:col-span-5 bg-white rounded-lg shadow-sm border border-gray-200 p-4 max-h-[600px] overflow-y-auto">
          {#if selectedVuln}
            <div class="space-y-4">
              <div>
                <h3 class="text-sm font-semibold text-gray-500">VULN ID</h3>
                <p class="text-lg font-bold text-gray-900">{selectedVuln.vulnId}</p>
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-500">STIG ID</h3>
                <p class="text-sm text-gray-900">{selectedVuln.stigId}</p>
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-500">Rule ID</h3>
                <p class="text-sm text-gray-900">{selectedVuln.ruleId}</p>
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-500">Rule Title</h3>
                <p class="text-sm text-gray-900">{selectedVuln.ruleTitle}</p>
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-500">Severity</h3>
                <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium {selectedVuln.severity.category === 'cat1' ? 'bg-red-100 text-red-800' : selectedVuln.severity.category === 'cat2' ? 'bg-orange-100 text-orange-800' : 'bg-yellow-100 text-yellow-800'}">
                  {selectedVuln.severity.name}
                </span>
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-500">Discussion</h3>
                <p class="text-sm text-gray-700 whitespace-pre-wrap max-h-32 overflow-y-auto bg-gray-50 p-2 rounded">{selectedVuln.ruleDiscussion || '-'}</p>
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-500">Check Content</h3>
                <p class="text-sm text-gray-700 whitespace-pre-wrap max-h-32 overflow-y-auto bg-gray-50 p-2 rounded">{selectedVuln.checkContent || '-'}</p>
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-500">Fix Text</h3>
                <p class="text-sm text-gray-700 whitespace-pre-wrap max-h-32 overflow-y-auto bg-gray-50 p-2 rounded">{selectedVuln.fixText || '-'}</p>
              </div>
              {#if cciInfo.length > 0}
                <div>
                  <h3 class="text-sm font-semibold text-gray-500">CCI References</h3>
                  <div class="space-y-2 mt-1">
                    {#each cciInfo as cci}
                      <div class="bg-gray-50 p-2 rounded text-sm">
                        <p class="font-medium">{cci.cciId}</p>
                        <p class="text-gray-600 text-xs">{cci.definition}</p>
                        {#if cci.references?.length > 0}
                          <ul class="mt-1 text-xs text-gray-500">
                            {#each cci.references as ref}
                              <li>{ref.title}: {ref.index}</li>
                            {/each}
                          </ul>
                        {/if}
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>
          {:else}
            <div class="flex items-center justify-center h-full text-gray-500">
              <p>Select a vulnerability to view details</p>
            </div>
          {/if}
        </div>

        <!-- Column 3: Status & Comments Form -->
        <div class="col-span-12 md:col-span-5 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          {#if selectedVuln}
            <div class="space-y-4">
              <h3 class="text-lg font-semibold text-gray-900">Update Status</h3>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select
                  bind:value={vulnFormData.status}
                  class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="open">Open</option>
                  <option value="not_a_finding">Not a Finding</option>
                  <option value="not_applicable">Not Applicable</option>
                  <option value="not_reviewed">Not Reviewed</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Finding Details</label>
                <textarea
                  bind:value={vulnFormData.findingDetails}
                  rows="4"
                  class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Enter finding details..."
                ></textarea>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Comments</label>
                <textarea
                  bind:value={vulnFormData.comments}
                  rows="4"
                  class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Enter comments..."
                ></textarea>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Severity Override</label>
                <select
                  bind:value={vulnFormData.severityOverride}
                  class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="">No Override</option>
                  <option value="high">High (CAT I)</option>
                  <option value="medium">Medium (CAT II)</option>
                  <option value="low">Low (CAT III)</option>
                </select>
              </div>

              {#if vulnFormData.severityOverride}
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">Severity Override Justification</label>
                  <textarea
                    bind:value={vulnFormData.severityJustification}
                    rows="3"
                    class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Justification required for override..."
                  ></textarea>
                </div>
              {/if}

              <div class="flex items-center gap-2">
                <input
                  type="checkbox"
                  bind:checked={bulkUpdateEnabled}
                  id="bulkUpdate"
                  class="rounded border-gray-300 text-indigo-600"
                />
                <label for="bulkUpdate" class="text-sm text-gray-700">
                  Apply to all matching vulnerabilities
                </label>
              </div>

              <button
                onclick={saveVulnerability}
                disabled={saving}
                class="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
              >
                {#if saving}
                  <RefreshCw size={16} class="mr-2 animate-spin" />
                  Saving...
                {:else}
                  <Save size={16} class="mr-2" />
                  Save Changes
                {/if}
              </button>
            </div>
          {:else}
            <div class="flex items-center justify-center h-full text-gray-500">
              <p>Select a vulnerability to update status</p>
            </div>
          {/if}
        </div>
      </div>

      <!-- Charts Row -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <h3 class="text-sm font-semibold text-gray-700 mb-2">Severity Breakdown</h3>
          {#if severityChartData.length > 0}
            <div class="h-48">
              <DonutChart
                name="checklist-severity"
                values={severityChartData}
                colors={['#dc2626', '#22c55e', '#9ca3af', '#3b82f6']}
                height="h-48"
              />
            </div>
          {/if}
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <h3 class="text-sm font-semibold text-gray-700 mb-2">Category Breakdown</h3>
          {#if categoryChartData.length > 0}
            <div class="h-48">
              <DonutChart
                name="checklist-category"
                values={categoryChartData}
                colors={['#dc2626', '#f97316', '#facc15']}
                height="h-48"
              />
            </div>
          {/if}
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <h3 class="text-sm font-semibold text-gray-700 mb-2">Score Breakdown</h3>
          {#if barChartValues.length > 0}
            <div class="h-48">
              <BarChart
                name="checklist-score-bar"
                values={barChartValues}
                labels={barChartLabels}
                height="h-48"
              />
            </div>
          {/if}
        </div>
      </div>
    </div>
  {:else}
    <div class="text-center py-24">
      <AlertTriangle size={48} class="mx-auto text-gray-400 mb-4" />
      <p class="text-gray-600">Checklist not found</p>
    </div>
  {/if}
</div>
