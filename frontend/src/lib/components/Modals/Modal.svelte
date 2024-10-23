<script lang="ts" context="module">
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

	// Props (components)
	export let components: Record<string, ModalComponent> = {};

	// Props (backdrop)
	export let position: CssClasses = 'items-center';

	// Props (modal)
	export let background: CssClasses = 'bg-surface-100-800-token';
	export let width: CssClasses = 'w-modal';
	export let height: CssClasses = 'h-auto';
	export let padding: CssClasses = 'p-4';
	export let spacing: CssClasses = 'space-y-4';
	export let rounded: CssClasses = 'rounded-container-token';
	export let shadow: CssClasses = 'shadow-xl';
	export let zIndex: CssClasses = 'z-[999]';

	// Props (buttons)
	export let buttonNeutral: CssClasses = 'variant-ghost-surface';
	export let buttonPositive: CssClasses = 'variant-filled';
	export let buttonTextCancel: CssClasses = 'Cancel';
	export let buttonTextConfirm: CssClasses = 'Confirm';
	export let buttonTextSubmit: CssClasses = 'Submit';

	// Props (regions)
	export let regionBackdrop: CssClasses = '';
	export let regionHeader: CssClasses = 'text-2xl font-bold';
	export let regionBody: CssClasses = 'max-h-[200px] overflow-hidden';
	export let regionFooter: CssClasses = 'flex justify-end space-x-2';

	// Props (transition)
	export let transitions = !$prefersReducedMotionStore;
	export let transitionIn: TransitionIn = fly as TransitionIn;
	export let transitionInParams: TransitionParams<TransitionIn> = {
		duration: 150,
		opacity: 0,
		x: 0,
		y: 100
	};
	export let transitionOut: TransitionOut = fly as TransitionOut;
	export let transitionOutParams: TransitionParams<TransitionOut> = {
		duration: 150,
		opacity: 0,
		x: 0,
		y: 100
	};

	// Base Styles
	const cBackdrop = 'fixed top-0 left-0 right-0 bottom-0 bg-surface-backdrop-token p-4';
	const cTransitionLayer = 'w-full h-fit min-h-full overflow-y-auto flex justify-center';
	const cModal = 'block overflow-y-auto';
	const cModalImage = 'w-full h-auto';

	// Local
	let promptValue: any;
	const buttonTextDefaults: Record<string, string> = {
		buttonTextCancel,
		buttonTextConfirm,
		buttonTextSubmit
	};
	let currentComponent: ModalComponent | undefined;
	let registeredInteractionWithBackdrop = false;
	let modalElement: HTMLDivElement;
	let windowHeight: number;
	let backdropOverflow = 'overflow-y-auto';

	const modalStore = getModalStore();

	$: if ($modalStore.length) handleModals($modalStore);

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

	$: onModalHeightChange(modalElement);

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

	// State & Reactive
	$: cPosition = $modalStore[0]?.position ?? position;
	$: classesBackdrop = `${cBackdrop} ${regionBackdrop} ${zIndex} ${classProp} ${
		$modalStore[0]?.backdropClasses ?? ''
	}`;
	$: classesTransitionLayer = `${cTransitionLayer} ${cPosition ?? ''}`;
	$: classesModal = `${cModal} ${background} ${width} ${height} ${padding} ${spacing} ${rounded} ${shadow} ${
		$modalStore[0]?.modalClasses ?? ''
	}`;

	$: parent = {
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
	};
</script>

<svelte:window bind:innerHeight={windowHeight} on:keydown={onKeyDown} />

{#if $modalStore.length > 0}
	{#key $modalStore}
		<!-- Backdrop -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="modal-backdrop {classesBackdrop} {backdropOverflow}"
			data-testid="modal-backdrop"
			on:mousedown={onBackdropInteractionBegin}
			on:mouseup={onBackdropInteractionEnd}
			on:touchstart|passive
			on:touchend|passive
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
								<button type="button" class="btn {buttonNeutral}" on:click={onClose}
									>{buttonTextCancel}</button
								>
							</footer>
						{:else if $modalStore[0].type === 'confirm'}
							<footer class="modal-footer {regionFooter}">
								<button type="button" class="btn {buttonNeutral}" on:click={onClose}
									>{buttonTextCancel}</button
								>
								<button type="button" class="btn {buttonPositive}" on:click={onConfirm}
									>{buttonTextConfirm}</button
								>
							</footer>
						{:else if $modalStore[0].type === 'prompt'}
							<form class="space-y-4" on:submit={onPromptSubmit}>
								<input
									class="modal-prompt-input input"
									name="prompt"
									type="text"
									bind:value={promptValue}
									{...$modalStore[0].valueAttr}
								/>
								<footer class="modal-footer {regionFooter}">
									<button type="button" class="btn {buttonNeutral}" on:click={onClose}
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
							<svelte:component this={currentComponent?.ref} {...currentComponent?.props} {parent}>
								{currentComponent?.slot}
							</svelte:component>
						{:else}
							<svelte:component
								this={currentComponent?.ref}
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
