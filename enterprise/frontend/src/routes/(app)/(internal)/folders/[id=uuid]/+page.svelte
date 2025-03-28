<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData, ActionData } from './$types';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import * as m from '$paraglide/messages';
	import { safeTranslate} from '$lib/utils/i18n';
	import ConfirmExportBody from '$lib/components/Modals/ConfirmExportBody.svelte';


	import type { ModalSettings, ModalComponent, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import ConfirmExportScopeModal from '$lib/components/Modals/ConfirmExportScopeModal.svelte';

	export let data: PageData;
	export let form: ActionData;

	const modalStore: ModalStore = getModalStore();

	$: if (form && form.redirect) {
		goto(getSecureRedirect(form.redirect));
	}

	function confirmExport(event: Event) {
		event.preventDefault();

		if (data.has_out_of_scope_objects?.length) {
			const modalComponent: ModalComponent = {
				ref: ConfirmExportScopeModal,
				props: {
					outOfScopeObjects: data.out_of_scope_objects || {},
					bodyComponent: ConfirmExportBody,
					bodyProps: {
						types: data.has_out_of_scope_objects
					}
				}
			};
			const modal: ModalSettings = {
				type: 'component',
				component: modalComponent,
				title: m.confirmModalTitleWarning(),
				response: (r: boolean) => {
					if (r) (event.target as HTMLFormElement).submit();
				}
			};
			modalStore.trigger(modal);
		} else {
			(event.target as HTMLFormElement).submit();
		}
	}
</script>

<DetailView {data}>
	<div slot="actions" class="flex flex-col space-y-2 justify-end">
		<form
			class="flex justify-end"
			action={`${$page.url.pathname}/export`}
			method="GET"
			on:submit={confirmExport}
		>
			<button type="submit" class="btn variant-filled-primary h-fit">
				<i class="fa-solid fa-download mr-2" />
				{m.exportButton()}
			</button>
		</form>
	</div>
</DetailView>
