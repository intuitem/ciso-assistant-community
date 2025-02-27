<script lang="ts">
	import type { PageData } from './$types';

	export let data: PageData;
    console.log(data)
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg">
        {#each data.requirementAssessments as requirementAssessment}
            <div class="flex flex-col">
                <div class="flex flex-row">
                    <div class="flex flex-col">
                        <div class="text-lg font-bold">{requirementAssessment.folder.str}/{requirementAssessment.compliance_assessment.str}</div>
                        <div class="text-lg font-bold">{requirementAssessment.name}</div>
                        <div class="text-sm">{requirementAssessment.description}</div>
                    </div>
                </div>
            </div>
        {/each}
    </div>
</div>