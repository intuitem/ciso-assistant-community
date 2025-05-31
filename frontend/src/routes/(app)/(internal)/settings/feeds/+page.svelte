<script lang="ts">
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { m } from '$paraglide/messages';
	import { pageTitle } from '$lib/utils/stores';
	import {
		IconBrandAws,
		IconBrandAzure,
		IconBrandGoogle,
		IconBrandOffice,
		IconCloud
	} from '@tabler/icons-svelte';
	pageTitle.set('Data feed settings');
</script>

<main class="h-screen">
	<div class="text-xl font-bold">Data sources</div>
	<div class="text font-semibold mb-6">Setup your credentials to pull data feeds</div>
	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-shield-halved"
		header="Prowler checks"
	>
		<div class="flex flex-col space-y-4">
			<div class="grid grid-cols-3 p-6 border rounded-lg gap-6">
				<div class="shadow-lg rounded-lg bg-slate-100 h-40 p-4 font-semibold text-xl">
					<IconBrandAws size={52} stroke={1} />
					<div>Amazon Web Services</div>
				</div>
				<div class="shadow-lg rounded-lg bg-slate-100 h-40 p-4 font-semibold text-xl">
					<IconBrandAzure size={52} stroke={1} />
					<div>Microsoft Azure</div>
				</div>
				<div class="shadow-lg rounded-lg bg-slate-100 h-40 p-4 font-semibold text-xl">
					<IconBrandGoogle size={52} stroke={1} />
					<div>Google Cloud</div>
				</div>
				<div class="shadow-lg rounded-lg bg-slate-100 h-40 p-4 font-semibold text-xl">
					<IconBrandOffice size={52} stroke={1} />
					<div>Microsoft O365</div>
				</div>
				<div class="shadow-lg rounded-lg bg-slate-100 h-40 p-4 font-semibold text-xl">
					<IconCloud size={52} stroke={1} />
					<div>Kubernetes</div>
				</div>
			</div>
		</div>
	</Dropdown>
	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-shield-halved"
		header="Prowler Cloud"
	>
		<div class="flex flex-col space-y-4">Prowler Cloud</div>
	</Dropdown>
	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-shield-halved"
		header="Lynis audit"
	>
		<div class="flex flex-col space-y-4">Lynis settings</div>
	</Dropdown>
	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-shield-halved"
		header="Wazuh"
	>
		<div class="flex flex-col space-y-4">Wazuh API</div>
	</Dropdown>
</main>
