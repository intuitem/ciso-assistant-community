<script lang="ts">
	import {
		getBuilderContext,
		getTranslation,
		withTranslation,
		type BuilderRequirement
	} from './builder-state';
	import { createCopyHandler, createHandleGatedDragHandlers } from './builder-utils.svelte';
	import ConfirmAction from './ConfirmAction.svelte';
	import QuestionEditor from './QuestionEditor.svelte';

	interface Props {
		requirement: BuilderRequirement;
	}

	let { requirement }: Props = $props();

	const builder = getBuilderContext();
	const {
		framework: frameworkStore,
		errors: errorsStore,
		activeLanguage: activeLanguageStore
	} = builder;
	const urnCopy = createCopyHandler();

	const depthColors = [
		'border-l-blue-400',
		'border-l-violet-400',
		'border-l-amber-400',
		'border-l-emerald-400'
	];
	const depthColor = $derived(depthColors[requirement.depth % depthColors.length]);

	async function saveField(field: string, value: unknown) {
		await builder.updateNode(requirement.node.id, { [field]: value });
	}

	const allQuestions = $derived(requirement.questions.map((q) => q.question));

	// Drag state for children
	const childDrag = createHandleGatedDragHandlers((from, to) =>
		builder.reorderRequirements(requirement.node.id, from, to)
	);

	/** Auto-grow a textarea to fit its content */
	function autoGrow(el: HTMLTextAreaElement) {
		el.style.height = 'auto';
		el.style.height = Math.max(40, el.scrollHeight) + 'px';
	}

	/** Svelte action: auto-grow textarea on mount and on input */
	function autogrowAction(el: HTMLTextAreaElement) {
		autoGrow(el);
		const onInput = () => autoGrow(el);
		el.addEventListener('input', onInput);
		return {
			destroy() {
				el.removeEventListener('input', onInput);
			}
		};
	}

	/** Name length for live character counter */
	let nameLength = $derived((requirement.node.name ?? '').length);
</script>

<div style="margin-left: {Math.min(requirement.depth, 3) * 16}px">
	<div
		class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden {requirement.depth >
		0
			? `border-l-4 ${depthColor}`
			: ''}"
	>
		<!-- Parent breadcrumb for deep nesting -->
		{#if requirement.depth >= 3 && requirement.node.parent_urn}
			<div class="px-4 pt-2 pb-0">
				<span class="text-[10px] text-gray-400">
					<i class="fa-solid fa-turn-up fa-rotate-90 mr-1"></i>nested under {requirement.node.parent_urn
						.split(':')
						.pop()
						?.slice(0, 12)}
				</span>
			</div>
		{/if}

		<!-- Header -->
		<div class="px-4 py-3 border-b border-gray-100 flex items-start gap-3 group">
			<span class="cursor-grab text-gray-300 group-hover:text-gray-400 mt-1" data-drag-handle>
				<i class="fa-solid fa-grip-vertical text-xs"></i>
			</span>
			<div class="flex-1 min-w-0 space-y-1">
				{#if $activeLanguageStore}
					{@const lang = $activeLanguageStore}
					<div class="flex items-center gap-2">
						<input
							type="text"
							value={requirement.node.ref_id ?? ''}
							placeholder="Ref ID"
							class="w-24 text-xs font-mono bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors text-gray-500"
							onblur={(e) => saveField('ref_id', e.currentTarget.value || null)}
						/>
					</div>
					<div class="grid grid-cols-2 gap-3">
						<input
							type="text"
							value={requirement.node.name ?? ''}
							readonly
							class="text-sm font-medium bg-transparent border-0 border-b border-transparent py-0.5 text-gray-400 cursor-default"
						/>
						<input
							type="text"
							value={getTranslation(requirement.node.translations, lang, 'name')}
							placeholder="Translate name..."
							class="text-sm font-medium bg-transparent border-0 border-b border-transparent hover:border-blue-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors"
							onblur={(e) =>
								saveField(
									'translations',
									withTranslation(
										requirement.node.translations,
										lang,
										'name',
										e.currentTarget.value
									)
								)}
						/>
					</div>
					{#if requirement.node.urn}
						<button
							type="button"
							class="inline-flex items-center gap-1 text-[10px] font-mono text-gray-300 hover:text-gray-500 transition-colors truncate max-w-full text-left group/urn"
							onclick={() => urnCopy.copy(requirement.node.urn ?? '')}
						>
							<i
								class="fa-solid {urnCopy.copied ? 'fa-check text-green-500' : 'fa-copy'} text-[9px]"
							></i>
							{#if urnCopy.copied}
								<span class="text-green-500">Copied!</span>
							{:else}
								{requirement.node.urn}
							{/if}
						</button>
					{/if}
					<div class="grid grid-cols-2 gap-3">
						<textarea
							value={requirement.node.description ?? ''}
							readonly
							rows="3"
							use:autogrowAction
							class="w-full text-xs text-gray-300 bg-transparent border-0 border-b border-transparent resize-none py-0.5 cursor-default"
						></textarea>
						<textarea
							value={getTranslation(requirement.node.translations, lang, 'description')}
							placeholder="Translate description..."
							rows="3"
							use:autogrowAction
							class="w-full text-xs bg-transparent border-0 border-b border-transparent hover:border-blue-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
							onblur={(e) =>
								saveField(
									'translations',
									withTranslation(
										requirement.node.translations,
										lang,
										'description',
										e.currentTarget.value
									)
								)}
						></textarea>
					</div>
					<div class="grid grid-cols-2 gap-3">
						<textarea
							value={requirement.node.typical_evidence ?? ''}
							readonly
							rows="2"
							use:autogrowAction
							class="w-full text-xs text-gray-300 bg-transparent border-0 border-b border-transparent resize-none py-0.5 cursor-default"
						></textarea>
						<textarea
							value={getTranslation(requirement.node.translations, lang, 'typical_evidence')}
							placeholder="Translate typical evidence..."
							rows="2"
							use:autogrowAction
							class="w-full text-xs bg-transparent border-0 border-b border-transparent hover:border-blue-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
							onblur={(e) =>
								saveField(
									'translations',
									withTranslation(
										requirement.node.translations,
										lang,
										'typical_evidence',
										e.currentTarget.value
									)
								)}
						></textarea>
					</div>
				{:else}
					<div class="flex items-center gap-2">
						<input
							type="text"
							value={requirement.node.ref_id ?? ''}
							placeholder="Ref ID"
							class="w-24 text-xs font-mono bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors text-gray-500"
							onblur={(e) => saveField('ref_id', e.currentTarget.value || null)}
						/>
						<div class="relative flex-1">
							<input
								type="text"
								value={requirement.node.name ?? ''}
								placeholder={requirement.node.description
									? requirement.node.description.slice(0, 60) +
										(requirement.node.description.length > 60 ? '...' : '')
									: 'Requirement name'}
								class="w-full text-sm font-medium bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors"
								onblur={(e) => saveField('name', e.currentTarget.value || null)}
							/>
							{#if nameLength > 0}
								<span
									class="absolute right-0 top-0 text-[10px] {nameLength > 180
										? 'text-red-500 font-medium'
										: 'text-gray-300'}"
								>
									{nameLength}/200
								</span>
							{/if}
						</div>
					</div>
					{#if requirement.node.urn}
						<button
							type="button"
							class="inline-flex items-center gap-1 text-[10px] font-mono text-gray-300 hover:text-gray-500 transition-colors truncate max-w-full text-left group/urn"
							onclick={() => urnCopy.copy(requirement.node.urn ?? '')}
						>
							<i
								class="fa-solid {urnCopy.copied ? 'fa-check text-green-500' : 'fa-copy'} text-[9px]"
							></i>
							{#if urnCopy.copied}
								<span class="text-green-500">Copied!</span>
							{:else}
								{requirement.node.urn}
							{/if}
						</button>
					{/if}
					<textarea
						value={requirement.node.description ?? ''}
						placeholder="Description (optional)"
						rows="3"
						use:autogrowAction
						class="w-full text-xs text-gray-500 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
						onblur={(e) => saveField('description', e.currentTarget.value || null)}
					></textarea>
					<textarea
						value={requirement.node.typical_evidence ?? ''}
						placeholder="Typical evidence (optional)"
						rows="2"
						use:autogrowAction
						class="w-full text-xs text-gray-500 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 px-0.5 py-0.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
						onblur={(e) => saveField('typical_evidence', e.currentTarget.value || null)}
					></textarea>
				{/if}
			</div>

			<div class="flex items-center gap-1 shrink-0">
				<label
					class="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer hover:text-gray-600 transition-colors"
					title="Whether this requirement is assessable by respondents"
				>
					<input
						type="checkbox"
						checked={requirement.node.assessable}
						onchange={(e) => saveField('assessable', e.currentTarget.checked)}
						class="w-4 h-4 rounded border-gray-300 cursor-pointer"
					/>
					Assessable
				</label>
				<ConfirmAction
					onconfirm={() => builder.deleteRequirement(requirement.node.id)}
					confirmLabel="Delete"
					triggerClass="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 transition-all"
					confirmClass="text-xs text-red-600 font-medium px-2 py-0.5 rounded bg-red-50"
				/>
			</div>
		</div>

		<!-- Implementation groups -->
		{#if $frameworkStore.implementation_groups_definition && $frameworkStore.implementation_groups_definition.length > 0}
			<div class="px-4 py-2 border-b border-gray-100">
				<span class="text-xs text-gray-500 mr-2">Implementation groups:</span>
				{#each $frameworkStore.implementation_groups_definition as ig}
					{@const refId = (ig as Record<string, string>).ref_id}
					{@const selected = (requirement.node.implementation_groups ?? []).includes(refId)}
					<button
						type="button"
						class="text-xs px-2 py-0.5 rounded-full border mr-1 transition-colors {selected
							? 'bg-blue-100 border-blue-300 text-blue-700'
							: 'bg-gray-50 border-gray-200 text-gray-400 hover:border-gray-300'}"
						onclick={() => {
							const current = requirement.node.implementation_groups ?? [];
							const next = selected ? current.filter((g) => g !== refId) : [...current, refId];
							builder.updateNode(requirement.node.id, { implementation_groups: next });
						}}
					>
						{refId}
					</button>
				{/each}
			</div>
		{/if}

		<!-- Visibility expression (CEL) -->
		<div class="px-4 py-2 border-b border-gray-100">
			<label class="text-xs text-gray-500 block mb-1">
				Visibility expression (CEL)
				<span
					class="text-gray-400 ml-1"
					title="CEL expression that must evaluate to true for this requirement to be visible. Example: requirements[&quot;urn:...&quot;].score > 50"
					>&#9432;</span
				>
			</label>
			<input
				type="text"
				class="w-full text-xs px-2 py-1 border border-gray-200 rounded font-mono bg-gray-50 focus:bg-white focus:border-blue-300 focus:outline-none"
				placeholder={'e.g. requirements["urn:..."].score > 50'}
				value={requirement.node.visibility_expression ?? ''}
				onblur={(e) => saveField('visibility_expression', e.currentTarget.value || null)}
			/>
		</div>

		<!-- Questions -->
		<div class="px-4 py-3 space-y-1">
			{#each requirement.questions as bq, qIndex (bq.question.id)}
				<QuestionEditor
					question={bq.question}
					reqNodeId={requirement.node.id}
					{qIndex}
					siblingQuestions={allQuestions}
				/>
			{/each}

			<button
				type="button"
				class="w-full py-2 border-2 border-dashed border-gray-200 rounded-lg text-xs text-gray-400 hover:text-gray-600 hover:border-gray-300 transition-colors"
				onclick={() => builder.addQuestion(requirement.node.id)}
			>
				<i class="fa-solid fa-plus mr-1"></i>Add question
			</button>
			{#if requirement.node.urn}
				<button
					type="button"
					class="w-full py-1 text-[11px] text-gray-300 hover:text-gray-500 transition-colors"
					onclick={() => builder.addRequirement(requirement.node.id, requirement.node.urn ?? '')}
				>
					<i class="fa-solid fa-plus mr-1"></i>Add sub-requirement
				</button>
			{/if}
		</div>

		{#if $errorsStore.has(`node-${requirement.node.id}`)}
			<div class="px-4 py-2 bg-red-50 border-t border-red-200">
				<p class="text-xs text-red-600">{$errorsStore.get(`node-${requirement.node.id}`)}</p>
			</div>
		{/if}
	</div>

	<!-- Children rendered as siblings (outside card) to avoid compound padding -->
	{#if requirement.children.length > 0}
		<div class="space-y-3 mt-2">
			{#each requirement.children as child, childIndex (child.node.id)}
				<div
					class:opacity-50={childDrag.draggedIndex === childIndex}
					draggable="true"
					onmousedown={childDrag.recordMousedown}
					ondragstart={(e) => childDrag.handleDragStart(e, childIndex)}
					ondragover={childDrag.handleDragOver}
					ondrop={(e) => childDrag.handleDrop(e, childIndex)}
					ondragend={childDrag.handleDragEnd}
					role="listitem"
				>
					<svelte:self requirement={child} />
				</div>
			{/each}
		</div>
	{/if}
</div>
