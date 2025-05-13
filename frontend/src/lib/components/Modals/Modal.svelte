<script lang="ts" module>
	import { dynamicTransition } from '$lib/components/utils/transitions';
	import {
		prefersReducedMotionStore,
		type Transition,
		type TransitionParams
	} from '@skeletonlabs/skeleton';
	import { fade, fly } from 'svelte/transition';

	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	type FlyTransition = typeof fly;
	type TransitionIn = Transition;
	type TransitionOut = Transition;
</script>

<script
	lang="ts"
	generics="TransitionIn extends Transition = FlyTransition, TransitionOut extends Transition = FlyTransition"
>
	import { run, createBubbler, passive } from 'svelte/legacy';

	const bubble = createBubbler();
	import { createEventDispatcher } from 'svelte';

	// Event Dispatcher
	type ModalEvent = {
		backdrop: MouseEvent;
	};
	const dispatch = createEventDispatcher<ModalEvent>();

	// Types
	import type { CssClasses, SvelteEvent } from '@skeletonlabs/skeleton';
	import type { ModalComponent, ModalSettings } from '@skeletonlabs/skeleton';
	import { focusTrap, getModalStore } from '@skeletonlabs/skeleton';

	

	

	

	

	

	
	interface Props {
		// Props (components)
		components?: Record<string, ModalComponent>;
		// Props (backdrop)
		position?: CssClasses;
		// Props (modal)
		background?: CssClasses;
		width?: CssClasses;
		height?: CssClasses;
		padding?: CssClasses;
		spacing?: CssClasses;
		rounded?: CssClasses;
		shadow?: CssClasses;
		zIndex?: CssClasses;
		// Props (buttons)
		buttonNeutral?: CssClasses;
		buttonPositive?: CssClasses;
		buttonTextCancel?: CssClasses;
		buttonTextConfirm?: CssClasses;
		buttonTextSubmit?: CssClasses;
		// Props (regions)
		regionBackdrop?: CssClasses;
		regionHeader?: CssClasses;
		regionBody?: CssClasses;
		regionFooter?: CssClasses;
		// Props (transition)
		transitions?: any;
		transitionIn?: TransitionIn;
		transitionInParams?: TransitionParams<TransitionIn>;
		transitionOut?: TransitionOut;
		transitionOutParams?: TransitionParams<TransitionOut>;
	}

	let {
		components = {},
		position = 'items-center',
		background = 'bg-surface-100-800-token',
		width = 'w-modal',
		height = 'h-auto',
		padding = 'p-4',
		spacing = 'space-y-4',
		rounded = 'rounded-container-token',
		shadow = 'shadow-xl',
		zIndex = 'z-[999]',
		buttonNeutral = 'variant-ghost-surface',
		buttonPositive = 'variant-filled',
		buttonTextCancel = $bindable('Cancel'),
		buttonTextConfirm = $bindable('Confirm'),
		buttonTextSubmit = $bindable('Submit'),
		regionBackdrop = '',
		regionHeader = 'text-2xl font-bold',
		regionBody = 'max-h-[200px] overflow-hidden',
		regionFooter = 'flex justify-end space-x-2',
		transitions = !$prefersReducedMotionStore,
		transitionIn = fly as TransitionIn,
		transitionInParams = {
		duration: 150,
		opacity: 0,
		x: 0,
		y: 100
	},
		transitionOut = fly as TransitionOut,
		transitionOutParams = {
		duration: 150,
		opacity: 0,
		x: 0,
		y: 100
	}
	}: Props = $props();

	// Base Styles
	const cBackdrop = 'fixed top-0 left-0 right-0 bottom-0 bg-surface-backdrop-token p-4';
	const cTransitionLayer = 'w-full h-fit min-h-full overflow-y-auto flex justify-center';
	const cModal = 'block overflow-y-auto';
	const cModalImage = 'w-full h-auto';

	// Local
	let promptValue: any = $state();
	const buttonTextDefaults: Record<string, string> = {
		buttonTextCancel,
		buttonTextConfirm,
		buttonTextSubmit
	};
	let currentComponent: ModalComponent | undefined = $state();
	let registeredInteractionWithBackdrop = false;
	let modalElement: HTMLDivElement = $state();
	let windowHeight: number = $state();
	let backdropOverflow = 'overflow-y-auto';

	const modalStore = getModalStore();


	function handleModals(modals: ModalSettings[]) {
		if (modals[0].type === 'prompt') promptValue = modals[0].value;
		buttonTextCancel = modals[0].buttonTextCancel || buttonTextDefaults.buttonTextCancel;
		buttonTextConfirm = modals[0].buttonTextConfirm || buttonTextDefaults.buttonTextConfirm;
		buttonTextSubmit = modals[0].buttonTextSubmit || buttonTextDefaults.buttonTextSubmit;
		currentComponent =
			typeof modals[0].component === 'string'
				? components[modals[0].component]
				: modals[0].component;
	}

	function onModalHeightChange(modal: HTMLDivElement) {
		let modalHeight = modal?.clientHeight;
		if (!modalHeight) modalHeight = (modal?.firstChild as HTMLElement)?.clientHeight;
		if (!modalHeight) return;
	}


	function onBackdropInteractionBegin(event: SvelteEvent<MouseEvent, HTMLDivElement>): void {
		if (!(event.target instanceof Element)) return;
		const classList = event.target.classList;
		if (classList.contains('modal-backdrop') || classList.contains('modal-transition')) {
			registeredInteractionWithBackdrop = true;
		}
	}

	function onBackdropInteractionEnd(event: SvelteEvent<MouseEvent, HTMLDivElement>): void {
		if (!(event.target instanceof Element)) return;
		const classList = event.target.classList;
		if (
			(classList.contains('modal-backdrop') || classList.contains('modal-transition')) &&
			registeredInteractionWithBackdrop
		) {
			if ($modalStore[0].response) $modalStore[0].response(undefined);
			modalStore.close();
			dispatch('backdrop', event);
		}
		registeredInteractionWithBackdrop = false;
	}

	function onClose(): void {
		if ($modalStore[0].response) $modalStore[0].response(false);
		modalStore.close();
	}

	function onConfirm(): void {
		if ($modalStore[0].response) $modalStore[0].response(true);
		modalStore.close();
	}

	function onPromptSubmit(event: SvelteEvent<SubmitEvent, HTMLFormElement>): void {
		event.preventDefault();
		if ($modalStore[0].response) {
			if (
				$modalStore[0].valueAttr !== undefined &&
				'type' in $modalStore[0].valueAttr &&
				$modalStore[0].valueAttr.type === 'number'
			)
				$modalStore[0].response(parseInt(promptValue));
			else $modalStore[0].response(promptValue);
		}
		modalStore.close();
	}

	function onKeyDown(event: SvelteEvent<KeyboardEvent, Window>): void {
		if (!$modalStore.length) return;
		if (event.code === 'Escape') onClose();
	}

	// Replacing $$props.class with classProp for compatibility
	let classProp = ''; // Replacing $$props.class


	run(() => {
		if ($modalStore.length) handleModals($modalStore);
	});
	run(() => {
		onModalHeightChange(modalElement);
	});
	// State & Reactive
	let cPosition = $derived($modalStore[0]?.position ?? position);
	let classesBackdrop = $derived(`${cBackdrop} ${regionBackdrop} ${zIndex} ${classProp} ${
		$modalStore[0]?.backdropClasses ?? ''
	}`);
	let classesTransitionLayer = $derived(`${cTransitionLayer} ${cPosition ?? ''}`);
	let classesModal = $derived(`${cModal} ${background} ${width} ${height} ${padding} ${spacing} ${rounded} ${shadow} ${
		$modalStore[0]?.modalClasses ?? ''
	}`);
	let parent = $derived({
		position,
		background,
		width,
		height,
		padding,
		spacing,
		rounded,
		shadow,
		buttonNeutral,
		buttonPositive,
		buttonTextCancel,
		buttonTextConfirm,
		buttonTextSubmit,
		regionBackdrop,
		regionHeader,
		regionBody,
		regionFooter,
		onClose,
		onConfirm
	});
</script>

<svelte:window bind:innerHeight={windowHeight} onkeydown={onKeyDown} />

{#if $modalStore.length > 0}
	{#key $modalStore}
		<!-- Backdrop -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="modal-backdrop {classesBackdrop} {backdropOverflow}"
			data-testid="modal-backdrop"
			onmousedown={onBackdropInteractionBegin}
			onmouseup={onBackdropInteractionEnd}
			use:passive={['touchstart', () => bubble('touchstart')]}
			use:passive={['touchend', () => bubble('touchend')]}
			transition:dynamicTransition|global={{
				transition: fade,
				params: { duration: 150 },
				enabled: transitions
			}}
			use:focusTrap={true}
		>
			<!-- Transition Layer -->
			<div
				class="modal-transition {classesTransitionLayer}"
				in:dynamicTransition|global={{
					transition: transitionIn,
					params: transitionInParams,
					enabled: transitions
				}}
				out:dynamicTransition|global={{
					transition: transitionOut,
					params: transitionOutParams,
					enabled: transitions
				}}
			>
				{#if $modalStore[0].type !== 'component'}
					<!-- Modal: Presets -->
					<div
						class="modal {classesModal}"
						bind:this={modalElement}
						data-testid="modal"
						role="dialog"
						aria-modal="true"
						aria-label={$modalStore[0].title ?? 'Modal'}
					>
						{#if $modalStore[0]?.title}
							<header class="modal-header {regionHeader}">{$modalStore[0].title}</header>
						{/if}
						{#if $modalStore[0]?.body}
							<article class="modal-body {regionBody}">{$modalStore[0].body}</article>
						{/if}
						{#if $modalStore[0]?.image && typeof $modalStore[0]?.image === 'string'}
							<img class="modal-image {cModalImage}" src={$modalStore[0]?.image} alt="Modal" />
						{/if}
						{#if $modalStore[0].type === 'alert'}
							<footer class="modal-footer {regionFooter}">
								<button type="button" class="btn {buttonNeutral}" onclick={onClose}
									>{buttonTextCancel}</button
								>
							</footer>
						{:else if $modalStore[0].type === 'confirm'}
							<footer class="modal-footer {regionFooter}">
								<button type="button" class="btn {buttonNeutral}" onclick={onClose}
									>{buttonTextCancel}</button
								>
								<button type="button" class="btn {buttonPositive}" onclick={onConfirm}
									>{buttonTextConfirm}</button
								>
							</footer>
						{:else if $modalStore[0].type === 'prompt'}
							<form class="space-y-4" onsubmit={onPromptSubmit}>
								<input
									class="modal-prompt-input input"
									name="prompt"
									type="text"
									bind:value={promptValue}
									{...$modalStore[0].valueAttr}
								/>
								<footer class="modal-footer {regionFooter}">
									<button type="button" class="btn {buttonNeutral}" onclick={onClose}
										>{buttonTextCancel}</button
									>
									<button type="submit" class="btn {buttonPositive}">{buttonTextSubmit}</button>
								</footer>
							</form>
						{/if}
					</div>
				{:else}
					<!-- Modal: Components -->
					<div
						bind:this={modalElement}
						class="modal contents {$modalStore[0]?.modalClasses ?? ''}"
						data-testid="modal-component"
						role="dialog"
						aria-modal="true"
						aria-label={$modalStore[0].title ?? 'Modal'}
					>
						{#if currentComponent?.slot}
							{@const SvelteComponent = currentComponent?.ref}
							<SvelteComponent {...currentComponent?.props} {parent}>
								{currentComponent?.slot}
							</SvelteComponent>
						{:else}
							{@const SvelteComponent_1 = currentComponent?.ref}
							<SvelteComponent_1
								{...currentComponent?.props}
								{parent}
							/>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/key}
{/if}
