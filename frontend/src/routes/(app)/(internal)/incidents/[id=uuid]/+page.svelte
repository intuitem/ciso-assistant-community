<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData } from './$types';
    import SuperForm from '$lib/components/Forms/Form.svelte';
    import { superForm } from 'sveltekit-superforms';
    import { zod } from 'sveltekit-superforms/adapters';
    import { modelSchema } from '$lib/utils/schemas';
    import * as m from '$paraglide/messages.js';
    import { getSecureRedirect } from '$lib/utils/helpers';
    import { goto } from '$lib/utils/breadcrumbs';
    import TimelineEntryForm from '$lib/components/Forms/ModelForm/TimelineEntryForm.svelte';
    import { createModalCache } from '$lib/utils/stores';


	export let data: PageData;
	let invalidateAll = true;
	let formAction = '?/create';
	let context = 'create';
    let parent: any
    const form = data.relatedModels['timeline-entries'].createForm
    const model = data.relatedModels['timeline-entries']
    let schema = modelSchema('timeline-entries');

    const _form = superForm(form, {
		dataType: 'json',
		enctype: 'application/x-www-form-urlencoded',
		invalidateAll,
		applyAction: $$props.applyAction ?? true,
		resetForm: $$props.resetForm ?? false,
		validators: zod(schema),
		taintedMessage: m.taintedFormMessage(),
		validationMethod: 'auto',
		onUpdated: async ({ form }) => {
			if (form.message?.redirect) {
				goto(getSecureRedirect(form.message.redirect));
			}
			if (form.valid) {
				parent.onConfirm();
				createModalCache.deleteCache(model.urlModel);
			}
		}
	});
</script>

<DetailView {data}>
    <div slot="widgets">
        <SuperForm
            class="flex flex-col space-y-3"
            action={formAction}
            dataType={'json'}
            enctype={'application/x-www-form-urlencoded'}
            data={form}
            {_form}
            {invalidateAll}
            let:form
            let:data
            let:initialData
            validators={zod(schema)}
            onUpdated={() => createModalCache.deleteCache(model.urlModel)}
            {...$$restProps}
        >
           <TimelineEntryForm
                {form}
                {model}
                {initialData}
                {context}
            />
            <div class="flex flex-row justify-between space-x-4">
                <button
                    class="btn variant-filled-primary font-semibold w-full"
                    data-testid="save-button"
                    type="submit">{m.save()}</button
                >
            </div>
        </SuperForm>
    </div>
</DetailView>
