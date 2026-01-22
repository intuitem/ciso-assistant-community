<script lang="ts">
	/**
	 * OSCAL Editor Component
	 *
	 * A zone-based OSCAL document editor inspired by OSCAL-GUI patterns.
	 * Supports:
	 * - Zone-based editing (metadata, controls, parameters, back-matter)
	 * - Parameter view switching (Blank/Catalog/Profile/Assigned)
	 * - Rich text editing for prose content
	 * - Real-time validation
	 * - Format conversion (JSON/YAML)
	 */

	import { onMount, onDestroy } from 'svelte';
	import { Tooltip } from '@skeletonlabs/skeleton-svelte';

	// Import shared types from utils
	import type {
		OscalDocument,
		OscalMetadata,
		OscalControl,
		OscalProperty,
		OscalPart,
		OscalParameter
	} from '$lib/utils/types';

	// Local types for editor-specific state
	type ParameterView = 'blank' | 'catalog' | 'profile' | 'assigned';
	type EditorZone = 'metadata' | 'controls' | 'parameters' | 'back-matter' | 'implementation';

	interface ValidationError {
		path: string;
		message: string;
		severity: 'error' | 'warning' | 'info';
	}

	interface Props {
		document?: OscalDocument;
		readonly?: boolean;
		showValidation?: boolean;
		autoSave?: boolean;
		autoSaveInterval?: number;
		onchange?: (doc: OscalDocument) => void;
		onsave?: (doc: OscalDocument) => void;
		onvalidate?: (errors: ValidationError[]) => void;
	}

	let {
		document = $bindable(),
		readonly = false,
		showValidation = true,
		autoSave = false,
		autoSaveInterval = 30000,
		onchange,
		onsave,
		onvalidate
	}: Props = $props();

	// State
	let activeZone: EditorZone = $state('metadata');
	let parameterView: ParameterView = $state('assigned');
	let validationErrors: ValidationError[] = $state([]);
	let isDirty = $state(false);
	let isValidating = $state(false);
	let showJsonView = $state(false);
	let jsonContent = $state('');
	let expandedControls: Set<string> = $state(new Set());
	let searchQuery = $state('');
	let autoSaveTimer: ReturnType<typeof setInterval> | null = null;

	// Derived state
	let documentType = $derived(document?.type ?? 'catalog');
	let metadata = $derived(document?.metadata ?? { title: '', 'last-modified': '', version: '', 'oscal-version': '1.1.2' });
	let controls = $derived(extractControls(document));
	let parameters = $derived(extractParameters(document));
	let filteredControls = $derived(
		searchQuery
			? controls.filter(c =>
				c.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
				c.title.toLowerCase().includes(searchQuery.toLowerCase())
			)
			: controls
	);

	// Available zones based on document type
	let availableZones = $derived(getAvailableZones(documentType));

	function getAvailableZones(type: string): EditorZone[] {
		switch (type) {
			case 'catalog':
				return ['metadata', 'controls', 'parameters', 'back-matter'];
			case 'profile':
				return ['metadata', 'controls', 'parameters', 'back-matter'];
			case 'ssp':
				return ['metadata', 'controls', 'implementation', 'back-matter'];
			case 'component-definition':
				return ['metadata', 'controls', 'implementation', 'back-matter'];
			case 'poam':
				return ['metadata', 'back-matter'];
			default:
				return ['metadata', 'back-matter'];
		}
	}

	function extractControls(doc: OscalDocument | undefined): OscalControl[] {
		if (!doc?.content) return [];

		const content = doc.content;

		// Handle different document types
		if (content.catalog?.controls) {
			return content.catalog.controls;
		}
		if (content.catalog?.groups) {
			return content.catalog.groups.flatMap((g: any) => g.controls ?? []);
		}
		if (content['system-security-plan']?.['control-implementation']?.['implemented-requirements']) {
			return content['system-security-plan']['control-implementation']['implemented-requirements'].map((ir: any) => ({
				id: ir['control-id'],
				title: ir.description ?? ir['control-id'],
				parts: ir.statements?.map((s: any) => ({ id: s['statement-id'], name: 'statement', prose: s.description })) ?? []
			}));
		}

		return [];
	}

	function extractParameters(doc: OscalDocument | undefined): OscalParameter[] {
		if (!doc?.content) return [];

		const content = doc.content;

		if (content.catalog?.params) {
			return content.catalog.params;
		}

		// Extract from controls
		const params: OscalParameter[] = [];
		const controls = extractControls(doc);
		for (const control of controls) {
			if (control.params) {
				params.push(...control.params);
			}
		}

		return params;
	}

	// Document manipulation functions
	function updateMetadata(field: keyof OscalMetadata, value: string) {
		if (!document) return;

		document = {
			...document,
			metadata: {
				...document.metadata!,
				[field]: value,
				'last-modified': new Date().toISOString()
			}
		};

		markDirty();
	}

	function updateControlProse(controlId: string, partName: string, prose: string) {
		if (!document?.content) return;

		const content = { ...document.content };
		const controls = extractControls(document);
		const control = controls.find(c => c.id === controlId);

		if (control) {
			const part = control.parts?.find(p => p.name === partName);
			if (part) {
				part.prose = prose;
			}
		}

		document = { ...document, content };
		markDirty();
	}

	function updateParameter(paramId: string, value: string) {
		if (!document?.content) return;

		const content = { ...document.content };
		const params = extractParameters(document);
		const param = params.find(p => p.id === paramId);

		if (param) {
			param.values = [value];
		}

		document = { ...document, content };
		markDirty();
	}

	function markDirty() {
		isDirty = true;
		onchange?.(document!);
	}

	// Validation
	async function validateDocument() {
		if (!document) return;

		isValidating = true;
		const errors: ValidationError[] = [];

		// Basic validation rules
		if (!document.metadata?.title) {
			errors.push({ path: 'metadata.title', message: 'Title is required', severity: 'error' });
		}

		if (!document.metadata?.['oscal-version']) {
			errors.push({ path: 'metadata.oscal-version', message: 'OSCAL version is required', severity: 'error' });
		}

		// Check for controls without titles
		const controls = extractControls(document);
		for (const control of controls) {
			if (!control.title) {
				errors.push({ path: `controls.${control.id}.title`, message: `Control ${control.id} missing title`, severity: 'warning' });
			}
		}

		// Check for empty parameter values
		const params = extractParameters(document);
		for (const param of params) {
			if (!param.values?.length && !param.select) {
				errors.push({ path: `parameters.${param.id}`, message: `Parameter ${param.id} has no value`, severity: 'info' });
			}
		}

		validationErrors = errors;
		isValidating = false;
		onvalidate?.(errors);
	}

	// Format conversion
	function toJson(): string {
		if (!document?.content) return '{}';
		return JSON.stringify(document.content, null, 2);
	}

	function toYaml(): string {
		// Simple YAML conversion (for complex YAML, use a library)
		if (!document?.content) return '';
		return jsonToYaml(document.content);
	}

	function jsonToYaml(obj: any, indent = 0): string {
		const spaces = '  '.repeat(indent);
		let yaml = '';

		for (const [key, value] of Object.entries(obj)) {
			if (value === null || value === undefined) continue;

			if (Array.isArray(value)) {
				yaml += `${spaces}${key}:\n`;
				for (const item of value) {
					if (typeof item === 'object') {
						yaml += `${spaces}- ${jsonToYaml(item, indent + 1).trim()}\n`;
					} else {
						yaml += `${spaces}- ${item}\n`;
					}
				}
			} else if (typeof value === 'object') {
				yaml += `${spaces}${key}:\n${jsonToYaml(value, indent + 1)}`;
			} else {
				yaml += `${spaces}${key}: ${value}\n`;
			}
		}

		return yaml;
	}

	function fromJson(json: string): boolean {
		try {
			const content = JSON.parse(json);
			document = {
				...document!,
				content,
				metadata: extractMetadataFromContent(content)
			};
			markDirty();
			return true;
		} catch (e) {
			return false;
		}
	}

	function extractMetadataFromContent(content: any): OscalMetadata {
		// Try to find metadata in different OSCAL document types
		const possiblePaths = [
			content.catalog?.metadata,
			content.profile?.metadata,
			content['system-security-plan']?.metadata,
			content['component-definition']?.metadata,
			content['assessment-plan']?.metadata,
			content['assessment-results']?.metadata,
			content['plan-of-action-and-milestones']?.metadata
		];

		const metadata = possiblePaths.find(m => m) ?? {};

		return {
			title: metadata.title ?? '',
			'last-modified': metadata['last-modified'] ?? new Date().toISOString(),
			version: metadata.version ?? '1.0',
			'oscal-version': metadata['oscal-version'] ?? '1.1.2'
		};
	}

	// Save functionality
	function save() {
		if (!document) return;
		onsave?.(document);
		isDirty = false;
	}

	// Control expansion
	function toggleControl(controlId: string) {
		const newSet = new Set(expandedControls);
		if (newSet.has(controlId)) {
			newSet.delete(controlId);
		} else {
			newSet.add(controlId);
		}
		expandedControls = newSet;
	}

	function expandAll() {
		expandedControls = new Set(controls.map(c => c.id));
	}

	function collapseAll() {
		expandedControls = new Set();
	}

	// Parameter view helpers
	function getParameterDisplayValue(param: OscalParameter): string {
		switch (parameterView) {
			case 'blank':
				return `{{ ${param.id} }}`;
			case 'catalog':
				return param.guidelines?.[0]?.prose ?? param.label ?? param.id;
			case 'profile':
				return param.select?.choice?.[0] ?? param.values?.[0] ?? param.id;
			case 'assigned':
				return param.values?.[0] ?? `[${param.id}]`;
			default:
				return param.id;
		}
	}

	// Lifecycle
	onMount(() => {
		if (document) {
			jsonContent = toJson();
			validateDocument();
		}

		if (autoSave) {
			autoSaveTimer = setInterval(() => {
				if (isDirty) {
					save();
				}
			}, autoSaveInterval);
		}
	});

	onDestroy(() => {
		if (autoSaveTimer) {
			clearInterval(autoSaveTimer);
		}
	});

	// Watch for document changes
	$effect(() => {
		if (document) {
			jsonContent = toJson();
		}
	});

	// Zone icons
	const zoneIcons: Record<EditorZone, string> = {
		metadata: 'fa-info-circle',
		controls: 'fa-shield-halved',
		parameters: 'fa-sliders',
		'back-matter': 'fa-book',
		implementation: 'fa-cogs'
	};

	// Zone labels
	const zoneLabels: Record<EditorZone, string> = {
		metadata: 'Metadata',
		controls: 'Controls',
		parameters: 'Parameters',
		'back-matter': 'Back Matter',
		implementation: 'Implementation'
	};
</script>

<div class="oscal-editor flex flex-col h-full bg-white rounded-lg shadow-lg">
	<!-- Toolbar -->
	<div class="toolbar flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50">
		<div class="flex items-center gap-4">
			<span class="font-semibold text-gray-700">
				<i class="fas fa-file-code mr-2"></i>
				OSCAL Editor
			</span>
			{#if document}
				<span class="text-sm text-gray-500">
					{documentType.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
				</span>
			{/if}
			{#if isDirty}
				<span class="text-xs text-orange-500 font-medium">
					<i class="fas fa-circle text-[6px] mr-1"></i>
					Unsaved changes
				</span>
			{/if}
		</div>

		<div class="flex items-center gap-2">
			<!-- Parameter View Selector -->
			<div class="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
				<Tooltip positioning={{ placement: 'bottom' }} contentBase="card bg-gray-800 text-white p-2 text-xs">
					{#snippet trigger()}
						<button
							class="px-2 py-1 text-xs rounded {parameterView === 'blank' ? 'bg-white shadow' : 'hover:bg-gray-200'}"
							onclick={() => parameterView = 'blank'}
						>
							Blank
						</button>
					{/snippet}
					{#snippet content()}
						Show parameter placeholders
					{/snippet}
				</Tooltip>
				<button
					class="px-2 py-1 text-xs rounded {parameterView === 'catalog' ? 'bg-white shadow' : 'hover:bg-gray-200'}"
					onclick={() => parameterView = 'catalog'}
				>
					Catalog
				</button>
				<button
					class="px-2 py-1 text-xs rounded {parameterView === 'profile' ? 'bg-white shadow' : 'hover:bg-gray-200'}"
					onclick={() => parameterView = 'profile'}
				>
					Profile
				</button>
				<button
					class="px-2 py-1 text-xs rounded {parameterView === 'assigned' ? 'bg-white shadow' : 'hover:bg-gray-200'}"
					onclick={() => parameterView = 'assigned'}
				>
					Assigned
				</button>
			</div>

			<!-- View Toggle -->
			<button
				class="px-3 py-1 text-sm rounded border {showJsonView ? 'bg-blue-50 border-blue-200 text-blue-700' : 'border-gray-300 hover:bg-gray-100'}"
				onclick={() => showJsonView = !showJsonView}
			>
				<i class="fas {showJsonView ? 'fa-edit' : 'fa-code'} mr-1"></i>
				{showJsonView ? 'Editor' : 'JSON'}
			</button>

			<!-- Validate -->
			<button
				class="px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50"
				onclick={validateDocument}
				disabled={isValidating}
			>
				<i class="fas fa-check-circle mr-1"></i>
				Validate
			</button>

			<!-- Save -->
			{#if !readonly}
				<button
					class="px-3 py-1 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
					onclick={save}
					disabled={!isDirty}
				>
					<i class="fas fa-save mr-1"></i>
					Save
				</button>
			{/if}
		</div>
	</div>

	<!-- Main Content -->
	<div class="flex flex-1 overflow-hidden">
		<!-- Zone Navigation -->
		<div class="zone-nav w-48 border-r border-gray-200 bg-gray-50 p-2">
			<nav class="flex flex-col gap-1">
				{#each availableZones as zone}
					<button
						class="flex items-center gap-2 px-3 py-2 text-sm rounded-lg text-left transition-colors {activeZone === zone ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'}"
						onclick={() => activeZone = zone}
					>
						<i class="fas {zoneIcons[zone]} w-4"></i>
						{zoneLabels[zone]}
						{#if zone === 'controls' && controls.length > 0}
							<span class="ml-auto text-xs bg-gray-200 px-1.5 py-0.5 rounded">{controls.length}</span>
						{/if}
					</button>
				{/each}
			</nav>

			{#if showValidation && validationErrors.length > 0}
				<div class="mt-4 pt-4 border-t border-gray-200">
					<h4 class="text-xs font-semibold text-gray-500 uppercase px-3 mb-2">Validation</h4>
					<div class="flex flex-col gap-1 max-h-40 overflow-y-auto">
						{#each validationErrors as error}
							<div class="px-3 py-1 text-xs {error.severity === 'error' ? 'text-red-600' : error.severity === 'warning' ? 'text-yellow-600' : 'text-blue-600'}">
								<i class="fas {error.severity === 'error' ? 'fa-times-circle' : error.severity === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle'} mr-1"></i>
								{error.message}
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>

		<!-- Content Area -->
		<div class="flex-1 overflow-auto p-4">
			{#if showJsonView}
				<!-- JSON Editor View -->
				<div class="json-editor h-full">
					<textarea
						class="w-full h-full p-4 font-mono text-sm border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
						bind:value={jsonContent}
						disabled={readonly}
						oninput={() => {
							const success = fromJson(jsonContent);
							if (!success) {
								// Show parse error
							}
						}}
					></textarea>
				</div>
			{:else}
				<!-- Zone Editor View -->
				{#if activeZone === 'metadata'}
					<div class="metadata-editor space-y-4">
						<h2 class="text-lg font-semibold text-gray-800">
							<i class="fas fa-info-circle mr-2 text-blue-500"></i>
							Document Metadata
						</h2>

						<div class="grid grid-cols-2 gap-4">
							<div>
								<label class="block text-sm font-medium text-gray-700 mb-1">Title</label>
								<input
									type="text"
									class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
									value={metadata.title}
									disabled={readonly}
									oninput={(e) => updateMetadata('title', e.currentTarget.value)}
								/>
							</div>

							<div>
								<label class="block text-sm font-medium text-gray-700 mb-1">Version</label>
								<input
									type="text"
									class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
									value={metadata.version}
									disabled={readonly}
									oninput={(e) => updateMetadata('version', e.currentTarget.value)}
								/>
							</div>

							<div>
								<label class="block text-sm font-medium text-gray-700 mb-1">OSCAL Version</label>
								<select
									class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
									value={metadata['oscal-version']}
									disabled={readonly}
									onchange={(e) => updateMetadata('oscal-version', e.currentTarget.value)}
								>
									<option value="1.1.2">1.1.2</option>
									<option value="1.1.1">1.1.1</option>
									<option value="1.1.0">1.1.0</option>
									<option value="1.0.6">1.0.6</option>
									<option value="1.0.4">1.0.4</option>
								</select>
							</div>

							<div>
								<label class="block text-sm font-medium text-gray-700 mb-1">Last Modified</label>
								<input
									type="text"
									class="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
									value={metadata['last-modified']}
									disabled
								/>
							</div>
						</div>
					</div>

				{:else if activeZone === 'controls'}
					<div class="controls-editor space-y-4">
						<div class="flex items-center justify-between">
							<h2 class="text-lg font-semibold text-gray-800">
								<i class="fas fa-shield-halved mr-2 text-blue-500"></i>
								Controls
							</h2>

							<div class="flex items-center gap-2">
								<input
									type="text"
									placeholder="Search controls..."
									class="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
									bind:value={searchQuery}
								/>
								<button class="text-sm text-blue-600 hover:text-blue-800" onclick={expandAll}>
									Expand All
								</button>
								<button class="text-sm text-blue-600 hover:text-blue-800" onclick={collapseAll}>
									Collapse All
								</button>
							</div>
						</div>

						<div class="controls-list space-y-2">
							{#each filteredControls as control}
								<div class="control-item border border-gray-200 rounded-lg overflow-hidden">
									<button
										class="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left"
										onclick={() => toggleControl(control.id)}
									>
										<div class="flex items-center gap-3">
											<i class="fas {expandedControls.has(control.id) ? 'fa-chevron-down' : 'fa-chevron-right'} text-gray-400 w-4"></i>
											<span class="font-mono text-sm text-blue-600">{control.id}</span>
											<span class="text-gray-700">{control.title}</span>
										</div>
										{#if control.class}
											<span class="text-xs bg-gray-200 px-2 py-0.5 rounded">{control.class}</span>
										{/if}
									</button>

									{#if expandedControls.has(control.id)}
										<div class="control-content p-4 space-y-3 border-t border-gray-200">
											{#if control.parts}
												{#each control.parts as part}
													<div class="part">
														<label class="block text-xs font-medium text-gray-500 uppercase mb-1">
															{part.name}
														</label>
														{#if readonly}
															<div class="prose-content text-sm text-gray-700 bg-gray-50 p-3 rounded">
																{@html (part.prose ?? '').replace(/\{\{([^}]+)\}\}/g, (_, paramId) => {
																	const param = parameters.find(p => p.id === paramId.trim());
																	return param ? `<span class="parameter bg-blue-100 px-1 rounded">${getParameterDisplayValue(param)}</span>` : `<span class="parameter bg-yellow-100 px-1 rounded">[${paramId}]</span>`;
																})}
															</div>
														{:else}
															<textarea
																class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg resize-y min-h-[80px] focus:outline-none focus:ring-2 focus:ring-blue-500"
																value={part.prose ?? ''}
																oninput={(e) => updateControlProse(control.id, part.name, e.currentTarget.value)}
															></textarea>
														{/if}
													</div>
												{/each}
											{/if}

											{#if control.params && control.params.length > 0}
												<div class="control-params mt-4 pt-4 border-t border-gray-100">
													<h4 class="text-xs font-medium text-gray-500 uppercase mb-2">Parameters</h4>
													<div class="grid grid-cols-2 gap-2">
														{#each control.params as param}
															<div class="flex items-center gap-2 text-sm">
																<span class="font-mono text-blue-600">{param.id}:</span>
																{#if readonly}
																	<span class="text-gray-700">{getParameterDisplayValue(param)}</span>
																{:else}
																	<input
																		type="text"
																		class="flex-1 px-2 py-1 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
																		value={param.values?.[0] ?? ''}
																		placeholder={param.label ?? param.id}
																		oninput={(e) => updateParameter(param.id, e.currentTarget.value)}
																	/>
																{/if}
															</div>
														{/each}
													</div>
												</div>
											{/if}
										</div>
									{/if}
								</div>
							{/each}

							{#if filteredControls.length === 0}
								<div class="text-center py-8 text-gray-500">
									<i class="fas fa-search text-3xl mb-2"></i>
									<p>No controls found</p>
								</div>
							{/if}
						</div>
					</div>

				{:else if activeZone === 'parameters'}
					<div class="parameters-editor space-y-4">
						<h2 class="text-lg font-semibold text-gray-800">
							<i class="fas fa-sliders mr-2 text-blue-500"></i>
							Parameters
						</h2>

						<div class="parameters-table">
							<table class="w-full text-sm">
								<thead>
									<tr class="border-b border-gray-200">
										<th class="text-left py-2 px-3 font-medium text-gray-600">ID</th>
										<th class="text-left py-2 px-3 font-medium text-gray-600">Label</th>
										<th class="text-left py-2 px-3 font-medium text-gray-600">Value</th>
										<th class="text-left py-2 px-3 font-medium text-gray-600">Guidelines</th>
									</tr>
								</thead>
								<tbody>
									{#each parameters as param}
										<tr class="border-b border-gray-100 hover:bg-gray-50">
											<td class="py-2 px-3 font-mono text-blue-600">{param.id}</td>
											<td class="py-2 px-3 text-gray-700">{param.label ?? '-'}</td>
											<td class="py-2 px-3">
												{#if readonly}
													<span class="text-gray-700">{getParameterDisplayValue(param)}</span>
												{:else if param.select}
													<select
														class="w-full px-2 py-1 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
														value={param.values?.[0] ?? ''}
														onchange={(e) => updateParameter(param.id, e.currentTarget.value)}
													>
														<option value="">Select...</option>
														{#each param.select.choice as choice}
															<option value={choice}>{choice}</option>
														{/each}
													</select>
												{:else}
													<input
														type="text"
														class="w-full px-2 py-1 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
														value={param.values?.[0] ?? ''}
														oninput={(e) => updateParameter(param.id, e.currentTarget.value)}
													/>
												{/if}
											</td>
											<td class="py-2 px-3 text-gray-500 text-xs">{param.guidelines?.[0]?.prose ?? '-'}</td>
										</tr>
									{/each}
								</tbody>
							</table>

							{#if parameters.length === 0}
								<div class="text-center py-8 text-gray-500">
									<i class="fas fa-sliders text-3xl mb-2"></i>
									<p>No parameters defined</p>
								</div>
							{/if}
						</div>
					</div>

				{:else if activeZone === 'implementation'}
					<div class="implementation-editor space-y-4">
						<h2 class="text-lg font-semibold text-gray-800">
							<i class="fas fa-cogs mr-2 text-blue-500"></i>
							Implementation Details
						</h2>

						<p class="text-gray-600">
							Implementation details for SSP and Component Definition documents.
						</p>

						<!-- Add implementation-specific editing here -->
						<div class="bg-gray-50 rounded-lg p-4 text-center text-gray-500">
							<i class="fas fa-tools text-3xl mb-2"></i>
							<p>Implementation editing view</p>
							<p class="text-sm">Edit control implementations and component mappings</p>
						</div>
					</div>

				{:else if activeZone === 'back-matter'}
					<div class="back-matter-editor space-y-4">
						<h2 class="text-lg font-semibold text-gray-800">
							<i class="fas fa-book mr-2 text-blue-500"></i>
							Back Matter
						</h2>

						<p class="text-gray-600">
							Resources, references, and supporting documentation.
						</p>

						<div class="bg-gray-50 rounded-lg p-4 text-center text-gray-500">
							<i class="fas fa-link text-3xl mb-2"></i>
							<p>Back matter resources</p>
							<p class="text-sm">Add references, citations, and external links</p>
						</div>
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>

<style>
	.oscal-editor {
		min-height: 600px;
	}

	.parameter {
		font-family: monospace;
		font-size: 0.875rem;
	}

	.prose-content :global(.parameter) {
		display: inline;
		padding: 0 0.25rem;
		border-radius: 0.25rem;
	}
</style>
