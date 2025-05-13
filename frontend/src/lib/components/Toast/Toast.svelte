<script lang="ts" module>
	import { fly } from 'svelte/transition';
	import {
		type Transition,
		type TransitionParams,
		type CssClasses,
		prefersReducedMotionStore
	} from '@skeletonlabs/skeleton';

	import { dynamicTransition } from '$lib/components/utils/transitions';

	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	type FlyTransition = typeof fly;
	type TransitionIn = Transition;
	type TransitionOut = Transition;
</script>

<script
	lang="ts"
	generics="TransitionIn extends Transition = FlyTransition, TransitionOut extends Transition = FlyTransition"
>
	import { run } from 'svelte/legacy';

	import { flip } from 'svelte/animate';

	// Stores
	import { getToastStore } from '@skeletonlabs/skeleton';
	const toastStore = getToastStore();

	

	

	

	
	interface Props {
		// Props
		position?: 't' | 'b' | 'l' | 'r' | 'tl' | 'tr' | 'bl' | 'br';
		max?: number;
		// Props (styles)
		background?: CssClasses;
		width?: CssClasses;
		color?: CssClasses;
		padding?: CssClasses;
		spacing?: CssClasses;
		rounded?: CssClasses;
		shadow?: CssClasses;
		zIndex?: CssClasses;
		// Props (buttons)
		buttonAction?: CssClasses;
		buttonDismiss?: CssClasses;
		buttonDismissLabel?: string;
		// Props (transition)
		transitions?: any;
		transitionIn?: TransitionIn;
		transitionInParams?: TransitionParams<TransitionIn>;
		transitionOut?: TransitionOut;
		transitionOutParams?: TransitionParams<TransitionOut>;
	}

	let {
		position = 'b',
		max = 3,
		background = 'variant-filled-secondary',
		width = 'max-w-[640px]',
		color = '',
		padding = 'p-4',
		spacing = 'space-x-4',
		rounded = 'rounded-container-token',
		shadow = 'shadow-lg',
		zIndex = 'z-[888]',
		buttonAction = 'btn variant-filled',
		buttonDismiss = 'btn-icon btn-icon-sm variant-filled',
		buttonDismissLabel = '✕',
		transitions = !$prefersReducedMotionStore,
		transitionIn = fly as TransitionIn,
		transitionInParams = { duration: 250 },
		transitionOut = fly as TransitionOut,
		transitionOutParams = { duration: 250 }
	}: Props = $props();

	// Base Classes
	const cWrapper = 'flex fixed top-0 left-0 right-0 bottom-0 pointer-events-none';
	const cSnackbar = 'flex flex-col gap-y-2';
	const cToast = 'flex justify-between items-center pointer-events-auto';
	const cToastActions = 'flex items-center space-x-2';

	// Local
	let cPosition: string = $state();
	let cAlign: string = $state();
	let animAxis = $state({ x: 0, y: 0 });

	// Set Position
	switch (position) {
		case 't':
			cPosition = 'justify-center items-start';
			cAlign = 'items-center';
			animAxis = { x: 0, y: -100 };
			break;
		case 'b':
			cPosition = 'justify-center items-end';
			cAlign = 'items-center';
			animAxis = { x: 0, y: 100 };
			break;
		case 'l':
			cPosition = 'justify-start items-center';
			cAlign = 'items-start';
			animAxis = { x: -100, y: 0 };
			break;
		case 'r':
			cPosition = 'justify-end items-center';
			cAlign = 'items-end';
			animAxis = { x: 100, y: 0 };
			break;
		case 'tl':
			cPosition = 'justify-start items-start';
			cAlign = 'items-start';
			animAxis = { x: -100, y: 0 };
			break;
		case 'tr':
			cPosition = 'justify-end items-start';
			cAlign = 'items-end';
			animAxis = { x: 100, y: 0 };
			break;
		case 'bl':
			cPosition = 'justify-start items-end';
			cAlign = 'items-start';
			animAxis = { x: -100, y: 0 };
			break;
		case 'br':
			cPosition = 'justify-end items-end';
			cAlign = 'items-end';
			animAxis = { x: 100, y: 0 };
			break;
	}

	function onAction(index: number): void {
		$toastStore[index]?.action?.response();
		toastStore.close($toastStore[index].id);
	}

	function onMouseEnter(index: number): void {
		if ($toastStore[index]?.hoverable) {
			toastStore.freeze(index);
			classesSnackbar += ' scale-[105%]';
		}
	}

	function onMouseLeave(index: number): void {
		if ($toastStore[index]?.hoverable) {
			toastStore.unfreeze(index);
			classesSnackbar = classesSnackbar.replace(' scale-[105%]', '');
		}
	}

	let wrapperVisible = $state(false);

	// Reactive
	let classProp = ''; // Replacing $$props.class
	let classesWrapper = $derived(`${cWrapper} ${cPosition} ${zIndex} ${classProp}`);
	let classesSnackbar = $derived(`${cSnackbar} ${cAlign} ${padding}`);
	let classesToast = $derived(`${cToast} ${width} ${color} ${padding} ${spacing} ${rounded} ${shadow}`);
	// Filtered Toast Store
	let filteredToasts = $derived(Array.from($toastStore).slice(0, max));

	run(() => {
		if (filteredToasts.length) {
			wrapperVisible = true;
		}
	});
</script>

{#if filteredToasts.length > 0 || wrapperVisible}
	<!-- Wrapper -->
	<div class="snackbar-wrapper {classesWrapper}" data-testid="snackbar-wrapper">
		<!-- List -->
		<div class="snackbar {classesSnackbar}">
			{#each filteredToasts as t, i (t)}
				<div
					animate:flip={{ duration: transitions ? 250 : 0 }}
					in:dynamicTransition|global={{
						transition: transitionIn,
						params: { x: animAxis.x, y: animAxis.y, ...transitionInParams },
						enabled: transitions
					}}
					out:dynamicTransition|global={{
						transition: transitionOut,
						params: { x: animAxis.x, y: animAxis.y, ...transitionOutParams },
						enabled: transitions
					}}
					onoutroend={() => {
						const outroFinishedForLastToastOnQueue = filteredToasts.length === 0;
						if (outroFinishedForLastToastOnQueue) wrapperVisible = false;
					}}
					onmouseenter={() => onMouseEnter(i)}
					onmouseleave={() => onMouseLeave(i)}
					role={t.hideDismiss ? 'alert' : 'alertdialog'}
					aria-live="polite"
				>
					<!-- Toast -->
					<div
						class="toast {classesToast} {t.background ?? background} {t.classes ?? ''}"
						data-testid="toast"
					>
						<div class="text-base">{t.message}</div>
						{#if t.action || !t.hideDismiss}
							<div class="toast-actions {cToastActions}">
								{#if t.action}
									<button class={buttonAction} onclick={() => onAction(i)}>{t.action.label}</button
									>
								{/if}
								{#if !t.hideDismiss}
									<button
										class={buttonDismiss}
										aria-label="Dismiss toast"
										onclick={() => toastStore.close(t.id)}>{buttonDismissLabel}</button
									>
								{/if}
							</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}
