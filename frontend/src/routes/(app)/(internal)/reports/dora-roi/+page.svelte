<script lang="ts">
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const { lintResults } = data;

	// Group results by severity
	const errors = lintResults.results.filter((r: any) => r.severity === 'error');
	const warnings = lintResults.results.filter((r: any) => r.severity === 'warning');
	const infos = lintResults.results.filter((r: any) => r.severity === 'info');
	const oks = lintResults.results.filter((r: any) => r.severity === 'ok');

	// Determine if we can generate the report (no errors)
	const canGenerate = errors.length === 0;

	// Available identifiers from the linter response
	const availableIdentifiers: Array<{ type: string; value: string }> =
		lintResults.available_identifiers || [];
	const entityCountry: string = lintResults.entity_country || '';
	const competentAuthority: string = lintResults.competent_authority || '';

	// Export options state
	let selectedIdentifierType = $state(
		availableIdentifiers.length > 0 ? availableIdentifiers[0].type : ''
	);
	let selectedLevel = $state('IND');
	let selectedNamingConvention = $state(entityCountry === 'BE' ? 'nbb' : 'eba');

	// Live filename preview
	let filenamePreview = $derived.by(() => {
		const id = availableIdentifiers.find((i) => i.type === selectedIdentifierType);
		if (!id) return '';
		const code = id.value;
		const key = id.type;
		const level = selectedLevel;
		if (selectedNamingConvention === 'eba') {
			const country = entityCountry ? entityCountry.substring(0, 2).toUpperCase() : 'XX';
			const refDate = `${new Date().getFullYear() - 1}-12-31`;
			const now = new Date();
			const pad = (n: number) => n.toString().padStart(2, '0');
			const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}T${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}z`;
			return `${key}_${code}.${level}_${country}_DORA010100_DORA_${refDate}_${timestamp}.zip`;
		}
		const authority = competentAuthority || 'UNKNOWN';
		return `${key}_${code}.${level}_${authority}_DOR_DORA_ROI.zip`;
	});

	function handleGenerateReport() {
		const params = new URLSearchParams();
		if (selectedIdentifierType) params.set('identifier_type', selectedIdentifierType);
		params.set('level', selectedLevel);
		params.set('naming_convention', selectedNamingConvention);
		window.location.href = `/reports/dora-roi/download?${params.toString()}`;
	}

	function getSeverityColor(severity: string): string {
		switch (severity) {
			case 'error':
				return 'text-red-600 dark:text-red-400 bg-surface-50-950 border-red-200 dark:border-red-800';
			case 'warning':
				return 'text-yellow-600 dark:text-yellow-400 bg-surface-50-950 border-yellow-200 dark:border-yellow-800';
			case 'info':
				return 'text-blue-600 dark:text-blue-400 bg-surface-50-950 border-blue-200 dark:border-blue-800';
			case 'ok':
				return 'text-green-600 dark:text-green-400 bg-surface-50-950 border-green-200 dark:border-green-800';
			default:
				return 'text-surface-600-400 bg-surface-50-950 border-surface-200-800';
		}
	}

	function getSeverityIcon(severity: string): string {
		switch (severity) {
			case 'error':
				return 'fa-circle-xmark';
			case 'warning':
				return 'fa-triangle-exclamation';
			case 'ok':
				return 'fa-circle-check';
			default:
				return 'fa-circle-info';
		}
	}

	function getEditUrl(result: any): string | null {
		if (!result.object_type || !result.object_id) {
			return null;
		}
		return `/${result.object_type}/${result.object_id}/edit?next=/reports/dora-roi`;
	}
</script>

<div class="px-4 py-6 space-y-6 max-w-5xl mx-auto">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold text-surface-950-50">DORA Register of Information</h1>
			<p class="mt-2 text-surface-600-400">Validation check before generating the report</p>
		</div>
		<a href="/reports" class="text-blue-600 hover:text-blue-800 flex items-center gap-2">
			<i class="fa-solid fa-arrow-left"></i>
			Back to Reports
		</a>
	</div>

	<!-- Summary Card -->
	<div class="bg-surface-50-950 rounded-xl shadow-sm border border-surface-200-800 p-6">
		<h2 class="text-xl font-semibold text-surface-950-50 mb-4">Validation Summary</h2>
		<div class="grid grid-cols-4 gap-4">
			<div
				class="text-center p-4 rounded-lg bg-surface-50-950 border border-red-300 dark:border-red-800"
			>
				<div class="text-3xl font-bold text-red-600 dark:text-red-400">
					{lintResults.summary.errors}
				</div>
				<div class="text-sm text-red-600 dark:text-red-400 mt-1">Errors</div>
			</div>
			<div
				class="text-center p-4 rounded-lg bg-surface-50-950 border border-yellow-300 dark:border-yellow-800"
			>
				<div class="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
					{lintResults.summary.warnings}
				</div>
				<div class="text-sm text-yellow-600 dark:text-yellow-400 mt-1">Warnings</div>
			</div>
			<div
				class="text-center p-4 rounded-lg bg-surface-50-950 border border-blue-300 dark:border-blue-800"
			>
				<div class="text-3xl font-bold text-blue-600 dark:text-blue-400">
					{lintResults.summary.info}
				</div>
				<div class="text-sm text-blue-600 dark:text-blue-400 mt-1">Info</div>
			</div>
			<div
				class="text-center p-4 rounded-lg bg-surface-50-950 border border-green-300 dark:border-green-800"
			>
				<div class="text-3xl font-bold text-green-600 dark:text-green-400">
					{lintResults.summary.ok}
				</div>
				<div class="text-sm text-green-600 dark:text-green-400 mt-1">Passed</div>
			</div>
		</div>
	</div>

	<!-- Validation Results -->
	<div class="bg-surface-50-950 rounded-xl shadow-sm border border-surface-200-800 p-6">
		<h2 class="text-xl font-semibold text-surface-950-50 mb-4">Validation Details</h2>

		<div class="space-y-3">
			{#if errors.length > 0}
				<div class="space-y-2">
					<h3 class="text-sm font-semibold text-red-600 uppercase tracking-wide">Errors</h3>
					{#each errors as result}
						{@const editUrl = getEditUrl(result)}
						<div
							class="flex items-start gap-3 p-4 rounded-lg border {getSeverityColor(
								result.severity
							)}"
						>
							<i class="fa-solid {getSeverityIcon(result.severity)} mt-0.5"></i>
							<div class="flex-1">
								<div class="font-medium text-sm">{result.category}</div>
								<div class="text-sm mt-1">{result.message}</div>
								{#if result.field}
									<div class="text-xs mt-1 opacity-75">Field: {result.field}</div>
								{/if}
							</div>
							{#if editUrl}
								<a
									href={editUrl}
									class="flex-shrink-0 px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 bg-surface-100-900 hover:bg-surface-200-800 rounded-md transition-colors flex items-center gap-2"
								>
									<i class="fa-solid fa-pencil"></i>
									Fix
								</a>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			{#if warnings.length > 0}
				<div class="space-y-2">
					<h3 class="text-sm font-semibold text-yellow-600 uppercase tracking-wide">Warnings</h3>
					{#each warnings as result}
						{@const editUrl = getEditUrl(result)}
						<div
							class="flex items-start gap-3 p-4 rounded-lg border {getSeverityColor(
								result.severity
							)}"
						>
							<i class="fa-solid {getSeverityIcon(result.severity)} mt-0.5"></i>
							<div class="flex-1">
								<div class="font-medium text-sm">{result.category}</div>
								<div class="text-sm mt-1">{result.message}</div>
								{#if result.field}
									<div class="text-xs mt-1 opacity-75">Field: {result.field}</div>
								{/if}
							</div>
							{#if editUrl}
								<a
									href={editUrl}
									class="flex-shrink-0 px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 bg-surface-100-900 hover:bg-surface-200-800 rounded-md transition-colors flex items-center gap-2"
								>
									<i class="fa-solid fa-pencil"></i>
									Review
								</a>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			{#if infos.length > 0}
				<div class="space-y-2">
					<h3 class="text-sm font-semibold text-blue-600 uppercase tracking-wide">Info</h3>
					{#each infos as result}
						{@const editUrl = getEditUrl(result)}
						<div
							class="flex items-start gap-3 p-4 rounded-lg border {getSeverityColor(
								result.severity
							)}"
						>
							<i class="fa-solid {getSeverityIcon(result.severity)} mt-0.5"></i>
							<div class="flex-1">
								<div class="font-medium text-sm">{result.category}</div>
								<div class="text-sm mt-1">{result.message}</div>
								{#if result.field}
									<div class="text-xs mt-1 opacity-75">Field: {result.field}</div>
								{/if}
							</div>
							{#if editUrl}
								<a
									href={editUrl}
									class="flex-shrink-0 px-3 py-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors flex items-center gap-2"
								>
									<i class="fa-solid fa-eye"></i>
									View
								</a>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			{#if oks.length > 0}
				<div class="space-y-2">
					<h3 class="text-sm font-semibold text-green-600 uppercase tracking-wide">
						Passed Checks
					</h3>
					{#each oks as result}
						{@const editUrl = getEditUrl(result)}
						<div
							class="flex items-start gap-3 p-4 rounded-lg border {getSeverityColor(
								result.severity
							)}"
						>
							<i class="fa-solid {getSeverityIcon(result.severity)} mt-0.5"></i>
							<div class="flex-1">
								<div class="font-medium text-sm">{result.category}</div>
								<div class="text-sm mt-1">{result.message}</div>
								{#if result.field}
									<div class="text-xs mt-1 opacity-75">Field: {result.field}</div>
								{/if}
							</div>
							{#if editUrl}
								<a
									href={editUrl}
									class="flex-shrink-0 px-3 py-1.5 text-xs font-medium text-surface-600-400 hover:text-surface-950-50 bg-surface-50-950 hover:bg-surface-100-900 rounded-md transition-colors flex items-center gap-2"
								>
									<i class="fa-solid fa-eye"></i>
									View
								</a>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>

	<!-- Export Options -->
	{#if availableIdentifiers.length > 0}
		<div class="bg-surface-50-950 rounded-xl shadow-sm border border-surface-200-800 p-6">
			<h2 class="text-xl font-semibold text-surface-900-100 mb-4">Export Options</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<!-- Identifier selector -->
				<div>
					<label for="identifier-type" class="block text-sm font-medium text-surface-700-300 mb-2">
						Entity Identifier
					</label>
					<select
						id="identifier-type"
						bind:value={selectedIdentifierType}
						class="w-full rounded-lg border border-surface-300-700 bg-surface-50-950 px-4 py-2.5 text-sm text-surface-900-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
					>
						{#each availableIdentifiers as identifier}
							<option value={identifier.type}>
								{identifier.type} — {identifier.value}
							</option>
						{/each}
					</select>
					<p class="mt-1 text-xs text-surface-600-400">
						Used for ZIP file naming and entity identification in the report.
					</p>
				</div>

				<!-- Level selector -->
				<div>
					<label class="block text-sm font-medium text-surface-700-300 mb-2">
						Reporting Level
					</label>
					<div class="flex gap-4">
						<label class="flex items-center gap-2 cursor-pointer">
							<input
								type="radio"
								name="level"
								value="IND"
								bind:group={selectedLevel}
								class="h-4 w-4 text-blue-600 border-surface-300-700 focus:ring-blue-500"
							/>
							<span class="text-sm text-surface-700-300">Individual (IND)</span>
						</label>
						<label class="flex items-center gap-2 cursor-pointer">
							<input
								type="radio"
								name="level"
								value="CON"
								bind:group={selectedLevel}
								class="h-4 w-4 text-blue-600 border-surface-300-700 focus:ring-blue-500"
							/>
							<span class="text-sm text-surface-700-300">Consolidated (CON)</span>
						</label>
					</div>
					<p class="mt-1 text-xs text-surface-600-400">
						Individual or consolidated reporting scope.
					</p>
				</div>

				<!-- Naming Convention selector -->
				<div>
					<label class="block text-sm font-medium text-surface-700-300 mb-2">
						Naming Convention
					</label>
					<div class="flex gap-4">
						<label class="flex items-center gap-2 cursor-pointer">
							<input
								type="radio"
								name="naming_convention"
								value="nbb"
								bind:group={selectedNamingConvention}
								class="h-4 w-4 text-blue-600 border-surface-300-700 focus:ring-blue-500"
							/>
							<span class="text-sm text-surface-700-300">NBB format</span>
						</label>
						<label class="flex items-center gap-2 cursor-pointer">
							<input
								type="radio"
								name="naming_convention"
								value="eba"
								bind:group={selectedNamingConvention}
								class="h-4 w-4 text-blue-600 border-surface-300-700 focus:ring-blue-500"
							/>
							<span class="text-sm text-surface-700-300">EBA standard</span>
						</label>
					</div>
					<p class="mt-1 text-xs text-surface-600-400">
						ZIP file naming format expected by your competent authority.
					</p>
				</div>
			</div>

			<!-- Filename preview -->
			{#if filenamePreview}
				<div class="mt-4 p-3 bg-surface-50-950 rounded-lg border border-surface-200-800">
					<div class="text-xs font-medium text-surface-600-400 mb-1">Filename preview</div>
					<code class="text-sm text-surface-800-200 break-all">{filenamePreview}</code>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Action Buttons -->
	<div class="bg-surface-50-950 rounded-xl shadow-sm border border-surface-200-800 p-6">
		<div class="flex items-center justify-between">
			<div>
				{#if canGenerate}
					<p class="text-sm text-surface-600-400">
						All validation checks passed. You can now generate the DORA ROI report.
					</p>
				{:else}
					<p class="text-sm text-red-600">Please fix all errors before generating the report.</p>
				{/if}
			</div>
			<button
				onclick={handleGenerateReport}
				disabled={!canGenerate}
				class="px-6 py-3 rounded-lg font-medium transition-colors {canGenerate
					? 'bg-blue-600 text-white hover:bg-blue-700'
					: 'bg-surface-300-700 text-surface-600-400 cursor-not-allowed'}"
			>
				<i class="fa-solid fa-download mr-2"></i>
				Generate Report
			</button>
		</div>
	</div>
</div>
