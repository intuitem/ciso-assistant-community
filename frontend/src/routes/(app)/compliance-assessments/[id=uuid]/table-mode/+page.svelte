<script lang="ts">
	import type { PageData } from './$types';
	import {
		Accordion,
		AccordionItem,
		getModalStore,
		RadioGroup,
		RadioItem,
		SlideToggle,

		type ModalComponent,

		type ModalSettings,

		type ModalStore

	} from '@skeletonlabs/skeleton';
	import * as m from '$paraglide/messages';
	import { breadcrumbObject } from '$lib/utils/stores';
	import {
		complianceResultTailwindColorMap,
		complianceStatusTailwindColorMap
	} from '$lib/utils/constants';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { capitalizeFirstLetter } from '$lib/utils/locales';
	import { getModelInfo } from '$lib/utils/crud';
	import { invalidate } from '$app/navigation';
	import { page } from '$app/stores';

	export let data: PageData;

	/** Is the page used for shallow routing? */
	export let shallow = false;

	export let actionPath: string = '';
	export let questionnaireOnly: boolean = false;
	export let assessmentOnly: boolean = false;

	if (!shallow) breadcrumbObject.set(data.compliance_assessment);

	const result_options = [
		{ id: 'not_assessed', label: m.notAssessed() },
		{ id: 'non_compliant', label: m.nonCompliant() },
		{ id: 'partially_compliant', label: m.partiallyCompliant() },
		{ id: 'compliant', label: m.compliant() },
		{ id: 'not_applicable', label: m.notApplicable() }
	];
	const status_options = [
		{ id: 'to_do', label: m.toDo() },
		{ id: 'in_progress', label: m.inProgress() },
		{ id: 'in_review', label: m.inReview() },
		{ id: 'done', label: m.done() }
	];

	const requirementHashmap = Object.fromEntries(
		data.requirements.map((requirement) => [requirement.id, requirement])
	);

	function title(requirementAssessment) {
		const requirement = requirementHashmap[requirementAssessment.requirement];
		const parent = data.requirements.find((req) => req.urn === requirement.parent_urn);
		return requirement.display_short
			? requirement.display_short
			: parent.display_short
				? parent.display_short
				: parent.description;
	}

	// Function to update requirement assessments
	function update(requirementAssessment, field: string, value: string, question: string = '') {
		if (question) {
			const questionIndex = requirementAssessment.answer.questions.findIndex(
				(q) => q.urn === question.urn
			);
			requirementAssessment.answer.questions[questionIndex].answer = value;
			value = requirementAssessment.answer;
		}
		const form = document.getElementById(`tableModeForm-${requirementAssessment.id}`);
		const formData = {
			id: requirementAssessment.id,
			[field]: value
		};
		fetch(form.action, {
			method: 'POST',
			body: JSON.stringify(formData)
		});
	}

	function addColor(result: string, map: Record<string, string>) {
		return map[result];
	}

	let questionnaireMode = questionnaireOnly ? true : assessmentOnly ? false : true;

	const modalStore: ModalStore = getModalStore();

	function modalEvidenceCreateForm(createform): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: createform,
				formAction: `${actionPath}?/createEvidence`,
				invalidateAll: false,
				model: data.evidenceModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate('add' + capitalizeFirstLetter(data.evidenceModel.localName)),
			response: (r) => {
				if (r===true) {
					invalidate($page.url.pathname);
				}
			}
		};
		modalStore.trigger(modal);
	}

	function modalConfirmDelete(id: string, name: string): void {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: data.deleteForm,
				formAction: `${actionPath}?/deleteEvidence`,
				id: id,
				invalidateAll: false,
				debug: false,
				URLModel: getModelInfo('evidences').urlModel
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.deleteModalTitle(),
			body: `${m.deleteModalMessage()}: ${name}?`
		};
		modalStore.trigger(modal);
	}
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div
		class="card px-6 py-4 bg-white flex flex-col justify-between shadow-lg w-full h-full space-y-2"
	>
		{#if !(questionnaireOnly ? !assessmentOnly : assessmentOnly)}
			<div class="flex items-center justify-center space-x-4">
				{#if questionnaireMode}
					<p class="font-bold text-sm">{m.assessmentMode()}</p>
				{:else}
					<p class="font-bold text-sm text-green-500">{m.assessmentMode()}</p>
				{/if}
				<SlideToggle
					name="questionnaireToggle"
					class="flex flex-row items-center justify-center"
					active="bg-primary-500"
					background="bg-green-500"
					bind:checked={questionnaireMode}
					on:click={() => (questionnaireMode = !questionnaireMode)}
				>
					{#if questionnaireMode}
						<p class="font-bold text-sm text-primary-500">{m.questionnaireMode()}</p>
					{:else}
						<p class="font-bold text-sm">{m.questionnaireMode()}</p>
					{/if}
				</SlideToggle>
			</div>
		{/if}
		{#each data.requirement_assessments as requirementAssessment}
			<div
				class="flex flex-col items-center justify-center border pb-2 px-2 shadow-lg rounded-md space-y-2"
			>
				<h1 class="font-semibold text-xl">{title(requirementAssessment)}</h1>
				<form
					class="flex flex-col space-y-2 items-center justify-evenly w-full"
					id="tableModeForm-{requirementAssessment.id}"
					action="{actionPath}?/updateRequirementAssessment"
					method="post"
				>
					{#if !questionnaireMode}
						<div class="flex flex-row w-full space-x-2">
							<div class="flex flex-col items-center w-1/2">
								<p class="flex items-center font-semibold">{m.status()}</p>
								<RadioGroup class="w-full flex-wrap items-center">
									{#each status_options as option}
										<RadioItem
											class="h-full"
											id={option.id}
											active={addColor(
												requirementAssessment.status,
												complianceStatusTailwindColorMap
											)}
											value={option.id}
											bind:group={requirementAssessment.status}
											name="status"
											on:change={(event) => update(requirementAssessment, 'status', option.id)}
											>{option.label}</RadioItem
										>
									{/each}
								</RadioGroup>
							</div>
							<div class="flex flex-col items-center w-1/2">
								<p class="flex items-center font-semibold">{m.result()}</p>
								<RadioGroup class="w-full flex-wrap items-center">
									{#each result_options as option}
										<RadioItem
											class="h-full"
											active={addColor(
												requirementAssessment.result,
												complianceResultTailwindColorMap
											)}
											id={option.id}
											value={option.id}
											bind:group={requirementAssessment.result}
											name="result"
											on:change={(event) => update(requirementAssessment, 'result', option.id)}
											>{option.label}</RadioItem
										>
									{/each}
								</RadioGroup>
							</div>
						</div>
					{/if}
					{#if requirementAssessment.description}
						<div class="flex flex-col w-full">
							<p class="flex font-semibold">{m.description()}</p>
							{requirementAssessment.description}
						</div>
					{/if}
					{#if Object.keys(requirementAssessment.answer).length !== 0}
						<div class="flex flex-col w-full space-y-2">
							{#each requirementAssessment.answer.questions as question}
								<li class="flex flex-col space-y-2 rounded-xl">
									<p class="font-semibold">{question.text}</p>
									{#if question.type === 'unique_choice'}
										<RadioGroup
											class="w-fit"
											active="variant-filled-primary"
											hover="hover:variant-soft-primary"
											flexDirection="flex-col"
										>
											{#each question.options as option}
												<RadioItem
													class="flex justify-start"
													bind:group={question.answer}
													name="question"
													value={option}
													on:change={(event) =>
														update(requirementAssessment, 'answer', option, question)}
													>{option}</RadioItem
												>
											{/each}
										</RadioGroup>
									{:else if question.type === 'date'}
										<input
											type="date"
											placeholder=""
											class="input w-fit"
											bind:value={question.answer}
											on:change={(event) =>
												update(requirementAssessment, 'answer', question.answer, question)}
											{...$$restProps}
										/>
									{:else}
										<textarea
											placeholder=""
											class="input w-full"
											bind:value={question.answer}
											on:keydown={(event) => event.key === 'Enter' && event.preventDefault()}
											on:change={(event) =>
												update(requirementAssessment, 'answer', question.answer, question)}
											{...$$restProps}
										/>
									{/if}
								</li>
							{/each}
						</div>
					{/if}
					<div class="flex flex-col w-full place-items-center">
						<Accordion regionCaret="flex">
							<AccordionItem>
								<svelte:fragment slot="summary"
									><p class="flex">{m.observation()}</p></svelte:fragment
								>
								<svelte:fragment slot="content">
									<div>
										<textarea
											placeholder=""
											class="input w-full"
											bind:value={requirementAssessment.observation}
											on:keydown={(event) => event.key === 'Enter' && event.preventDefault()}
										/>
										{#if requirementAssessment.observationBuffer !== requirementAssessment.observation}
											<button
												class="rounded-md w-8 h-8 border shadow-lg hover:bg-green-300 hover:text-green-500 duration-300"
												on:click={(event) => {update(requirementAssessment, 'observation', requirementAssessment.observation); requirementAssessment.observationBuffer = requirementAssessment.observation}}
												type="button"
											>
											<i class="fa-solid fa-check opacity-70"></i>
											</button>
											<button
												class="rounded-md w-8 h-8 border shadow-lg hover:bg-red-300 hover:text-red-500 duration-300"
												on:click={() => (requirementAssessment.observation = requirementAssessment.observationBuffer)}
												type="button"
											>
											<i class="fa-solid fa-xmark opacity-70"></i>
											</button>
										{/if}
									</div>
								</svelte:fragment>
							</AccordionItem>
							<AccordionItem>
								<svelte:fragment slot="summary"
									><p class="flex">
										{m.evidence()} ({requirementAssessment.evidences.length})
									</p></svelte:fragment
								>
								<svelte:fragment slot="content">
									<div class="flex flex-row space-x-2 items-center">
										<button
											class="btn variant-filled-primary self-start"
											on:click={() =>
												modalEvidenceCreateForm(requirementAssessment.evidenceCreateForm)}
											type="button"><i class="fa-solid fa-plus mr-2" />{m.addEvidence()}</button
										>
										{#each requirementAssessment.evidences as evidence}
											<p class="card p-2">
												<i class="fa-solid fa-file mr-2"></i>{evidence.str}
												<button
													on:click={(_) => modalConfirmDelete(evidence.id, evidence.str)}
													type="button"
												>
													<i class="fa-solid fa-xmark ml-2 text-red-500"></i>
												</button>
											</p>
										{/each}
									</div>
								</svelte:fragment>
							</AccordionItem>
						</Accordion>
					</div>
				</form>
			</div>
		{/each}
	</div>
</div>
