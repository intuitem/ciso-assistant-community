<script lang="ts">
	import Select from '../Select.svelte';
	import NumberField from '../NumberField.svelte';
	import TextField from '../TextField.svelte';
	import TextArea from '../TextArea.svelte';
	import { m } from '$paraglide/messages';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperForm } from 'sveltekit-superforms';
	import { Accordion, AccordionItem } from '@skeletonlabs/skeleton';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import RadioGroupInput from '../RadioGroupInput.svelte';
	import { safeTranslate } from '$lib/utils/i18n';

	export let form: SuperForm<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};

	const formStore = form.form;

	// Prowler provider options
	const providerOptions = [
		{ label: 'Amazon Web Services (AWS)', value: 'aws' },
		{ label: 'Microsoft Azure', value: 'azure' },
		{ label: 'Google Cloud Platform (GCP)', value: 'gcp' },
		{ label: 'Kubernetes', value: 'kubernetes' },
		{ label: 'Microsoft 365', value: 'microsoft365' }
	];

	// Output format options
	const outputFormatOptions = [
		{ label: 'JSON', value: 'json' },
		{ label: 'CSV', value: 'csv' },
		{ label: 'HTML', value: 'html' },
		{ label: 'JUnit XML', value: 'junit-xml' },
		{ label: 'ASFF', value: 'asff' }
	];

	// Severity level options
	const severityOptions = [
		{ label: 'Critical', value: 'critical' },
		{ label: 'High', value: 'high' },
		{ label: 'Medium', value: 'medium' },
		{ label: 'Low', value: 'low' },
		{ label: 'Informational', value: 'informational' }
	];

	$: selectedProvider = formDataCache['prowler_provider'] || 'aws';
</script>

<Accordion regionControl="font-bold">
	<AccordionItem open>
		<svelte:fragment slot="summary">
			<i class="fa-solid fa-cloud mr-2"></i>Provider Configuration
		</svelte:fragment>
		<svelte:fragment slot="content">
			<div class="p-4 space-y-4">
				<Select
					{form}
					field="prowler_provider"
					cacheLock={cacheLocks['prowler_provider']}
					bind:cachedValue={formDataCache['prowler_provider']}
					options={providerOptions}
					label="Cloud Provider"
					helpText="Select the cloud provider to audit"
				/>

				<!-- AWS Configuration -->
				{#if selectedProvider === 'aws'}
					<div class="bg-blue-50 p-4 rounded-lg space-y-4">
						<h4 class="font-semibold text-lg">AWS Configuration</h4>

						<TextField
							{form}
							field="prowler_aws_account_id"
							label="AWS Account ID"
							helpText="AWS Account ID to audit"
							bind:cachedValue={formDataCache['prowler_aws_account_id']}
						/>

						<div class="grid grid-cols-1 gap-4">
							<TextField
								{form}
								field="prowler_aws_access_key_id"
								label="AWS Access Key ID"
								helpText="AWS_ACCESS_KEY_ID"
								bind:cachedValue={formDataCache['prowler_aws_access_key_id']}
							/>

							<TextField
								{form}
								field="prowler_aws_secret_access_key"
								label="AWS Secret Access Key"
								type="password"
								helpText="AWS_SECRET_ACCESS_KEY"
								bind:cachedValue={formDataCache['prowler_aws_secret_access_key']}
							/>

							<TextField
								{form}
								field="prowler_aws_session_token"
								label="AWS Session Token (Optional)"
								type="password"
								helpText="AWS_SESSION_TOKEN - Required for temporary credentials"
								bind:cachedValue={formDataCache['prowler_aws_session_token']}
							/>
						</div>
					</div>
				{/if}

				<!-- Azure Configuration -->
				{#if selectedProvider === 'azure'}
					<div class="bg-blue-50 p-4 rounded-lg space-y-4">
						<h4 class="font-semibold text-lg">Azure Configuration</h4>

						<TextField
							{form}
							field="prowler_azure_subscription_id"
							label="Azure Subscription ID"
							helpText="--subscription-id parameter"
							bind:cachedValue={formDataCache['prowler_azure_subscription_id']}
						/>

						<Checkbox
							{form}
							field="prowler_azure_sp_env_auth"
							label="Use Service Principal Environment Authentication"
							helpText="Enable --sp-env-auth flag"
							bind:cachedValue={formDataCache['prowler_azure_sp_env_auth']}
						/>

						<div class="grid grid-cols-1 gap-4">
							<TextField
								{form}
								field="prowler_azure_client_id"
								label="Azure Client ID"
								helpText="AZURE_CLIENT_ID environment variable"
								bind:cachedValue={formDataCache['prowler_azure_client_id']}
							/>

							<TextField
								{form}
								field="prowler_azure_client_secret"
								label="Azure Client Secret"
								type="password"
								helpText="AZURE_CLIENT_SECRET environment variable"
								bind:cachedValue={formDataCache['prowler_azure_client_secret']}
							/>

							<TextField
								{form}
								field="prowler_azure_tenant_id"
								label="Azure Tenant ID"
								helpText="AZURE_TENANT_ID environment variable"
								bind:cachedValue={formDataCache['prowler_azure_tenant_id']}
							/>
						</div>
					</div>
				{/if}

				<!-- Microsoft 365 Configuration -->
				{#if selectedProvider === 'microsoft365'}
					<div class="bg-blue-50 p-4 rounded-lg space-y-4">
						<h4 class="font-semibold text-lg">Microsoft 365 Configuration</h4>

						<Checkbox
							{form}
							field="prowler_m365_sp_env_auth"
							label="Use Service Principal Environment Authentication"
							helpText="Enable --sp-env-auth flag"
							bind:cachedValue={formDataCache['prowler_m365_sp_env_auth']}
						/>

						<div class="grid grid-cols-1 gap-4">
							<TextField
								{form}
								field="prowler_m365_client_id"
								label="Azure Client ID"
								helpText="AZURE_CLIENT_ID environment variable"
								bind:cachedValue={formDataCache['prowler_m365_client_id']}
							/>

							<TextField
								{form}
								field="prowler_m365_client_secret"
								label="Azure Client Secret"
								type="password"
								helpText="AZURE_CLIENT_SECRET environment variable"
								bind:cachedValue={formDataCache['prowler_m365_client_secret']}
							/>

							<TextField
								{form}
								field="prowler_m365_tenant_id"
								label="Azure Tenant ID"
								helpText="AZURE_TENANT_ID environment variable"
								bind:cachedValue={formDataCache['prowler_m365_tenant_id']}
							/>
						</div>
					</div>
				{/if}

				<!-- GCP Configuration -->
				{#if selectedProvider === 'gcp'}
					<div class="bg-blue-50 p-4 rounded-lg space-y-4">
						<h4 class="font-semibold text-lg">Google Cloud Configuration</h4>

						<TextField
							{form}
							field="prowler_gcp_project_id"
							label="GCP Project ID"
							helpText="--project-id parameter"
							bind:cachedValue={formDataCache['prowler_gcp_project_id']}
						/>

						<div class="space-y-2">
							<label class="label">
								<span>Service Account Credentials (JSON)</span>
							</label>
							<TextArea
								{form}
								field="prowler_gcp_credentials_file"
								label=""
								rows={8}
								helpText="Paste the entire JSON content of your GCP service account credentials file (--credentials-file)"
								bind:cachedValue={formDataCache['prowler_gcp_credentials_file']}
							/>
						</div>
					</div>
				{/if}

				<!-- Kubernetes Configuration -->
				{#if selectedProvider === 'kubernetes'}
					<div class="bg-blue-50 p-4 rounded-lg space-y-4">
						<h4 class="font-semibold text-lg">Kubernetes Configuration</h4>

						<div class="space-y-2">
							<label class="label">
								<span>Kubeconfig File Content</span>
							</label>
							<TextArea
								{form}
								field="prowler_k8s_kubeconfig_file"
								label=""
								rows={12}
								helpText="Paste the entire content of your kubeconfig file (--kubeconfig-file parameter)"
								bind:cachedValue={formDataCache['prowler_k8s_kubeconfig_file']}
							/>
						</div>
					</div>
				{/if}
			</div>
		</svelte:fragment>
	</AccordionItem>

	<AccordionItem open>
		<svelte:fragment slot="summary">
			<i class="fa-solid fa-list-check mr-2"></i>Check Configuration
		</svelte:fragment>
		<svelte:fragment slot="content">
			<div class="p-4 space-y-4">
				<div class="grid grid-cols-2 gap-4">
					<TextField
						{form}
						field="prowler_checks_include"
						label="Include Checks"
						helpText="Comma-separated list of check IDs to include (e.g., iam_user_mfa_enabled)"
						bind:cachedValue={formDataCache['prowler_checks_include']}
					/>

					<TextField
						{form}
						field="prowler_checks_exclude"
						label="Exclude Checks"
						helpText="Comma-separated list of check IDs to exclude"
						bind:cachedValue={formDataCache['prowler_checks_exclude']}
					/>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<TextField
						{form}
						field="prowler_services_include"
						label="Include Services"
						helpText="Comma-separated list of services to include (e.g., iam,s3,ec2)"
						bind:cachedValue={formDataCache['prowler_services_include']}
					/>

					<TextField
						{form}
						field="prowler_services_exclude"
						label="Exclude Services"
						helpText="Comma-separated list of services to exclude"
						bind:cachedValue={formDataCache['prowler_services_exclude']}
					/>
				</div>

				<Select
					{form}
					field="prowler_severity"
					cacheLock={cacheLocks['prowler_severity']}
					bind:cachedValue={formDataCache['prowler_severity']}
					options={severityOptions}
					label="Minimum Severity Level"
					helpText="Only show findings at or above this severity level"
				/>

				<Checkbox
					{form}
					field="prowler_only_fail"
					label="Show Only Failed Checks"
					helpText="Display only checks that failed (hide PASS results)"
					bind:cachedValue={formDataCache['prowler_only_fail']}
				/>
			</div>
		</svelte:fragment>
	</AccordionItem>

	<AccordionItem open>
		<svelte:fragment slot="summary">
			<i class="fa-solid fa-file-export mr-2"></i>Output Configuration
		</svelte:fragment>
		<svelte:fragment slot="content">
			<div class="p-4 space-y-4">
				<Select
					{form}
					field="prowler_output_format"
					cacheLock={cacheLocks['prowler_output_format']}
					bind:cachedValue={formDataCache['prowler_output_format']}
					options={outputFormatOptions}
					label="Output Format"
					helpText="Format for the scan results"
				/>

				<TextField
					{form}
					field="prowler_output_directory"
					label="Output Directory"
					helpText="Directory path to save scan results"
					bind:cachedValue={formDataCache['prowler_output_directory']}
				/>

				<div class="grid grid-cols-2 gap-4">
					<Checkbox
						{form}
						field="prowler_quiet"
						label="Quiet Mode"
						helpText="Suppress verbose output during scan"
						bind:cachedValue={formDataCache['prowler_quiet']}
					/>

					<Checkbox
						{form}
						field="prowler_no_banner"
						label="Hide Banner"
						helpText="Don't display the Prowler banner"
						bind:cachedValue={formDataCache['prowler_no_banner']}
					/>
				</div>
			</div>
		</svelte:fragment>
	</AccordionItem>

	<AccordionItem>
		<svelte:fragment slot="summary">
			<i class="fa-solid fa-shield-halved mr-2"></i>Compliance Frameworks
		</svelte:fragment>
		<svelte:fragment slot="content">
			<div class="p-4 space-y-4">
				<div class="grid grid-cols-2 gap-4">
					<Checkbox
						{form}
						field="prowler_compliance_cis"
						label="CIS Benchmarks"
						helpText="Center for Internet Security benchmarks"
						bind:cachedValue={formDataCache['prowler_compliance_cis']}
					/>

					<Checkbox
						{form}
						field="prowler_compliance_pci"
						label="PCI DSS"
						helpText="Payment Card Industry Data Security Standard"
						bind:cachedValue={formDataCache['prowler_compliance_pci']}
					/>

					<Checkbox
						{form}
						field="prowler_compliance_gdpr"
						label="GDPR"
						helpText="General Data Protection Regulation"
						bind:cachedValue={formDataCache['prowler_compliance_gdpr']}
					/>

					<Checkbox
						{form}
						field="prowler_compliance_hipaa"
						label="HIPAA"
						helpText="Health Insurance Portability and Accountability Act"
						bind:cachedValue={formDataCache['prowler_compliance_hipaa']}
					/>

					<Checkbox
						{form}
						field="prowler_compliance_nist"
						label="NIST"
						helpText="National Institute of Standards and Technology"
						bind:cachedValue={formDataCache['prowler_compliance_nist']}
					/>

					<Checkbox
						{form}
						field="prowler_compliance_iso27001"
						label="ISO 27001"
						helpText="Information Security Management System"
						bind:cachedValue={formDataCache['prowler_compliance_iso27001']}
					/>
				</div>
			</div>
		</svelte:fragment>
	</AccordionItem>

	<AccordionItem>
		<svelte:fragment slot="summary">
			<i class="fa-solid fa-cog mr-2"></i>Advanced Settings
		</svelte:fragment>
		<svelte:fragment slot="content">
			<div class="p-4 space-y-4">
				<div class="grid grid-cols-2 gap-4">
					<NumberField
						{form}
						field="prowler_max_workers"
						label="Max Workers"
						min={1}
						max={50}
						step={1}
						helpText="Maximum number of concurrent workers"
						cacheLock={cacheLocks['prowler_max_workers']}
						bind:cachedValue={formDataCache['prowler_max_workers']}
					/>

					<NumberField
						{form}
						field="prowler_timeout"
						label="Timeout (seconds)"
						min={30}
						max={3600}
						step={30}
						helpText="Timeout for individual checks"
						cacheLock={cacheLocks['prowler_timeout']}
						bind:cachedValue={formDataCache['prowler_timeout']}
					/>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<Checkbox
						{form}
						field="prowler_ignore_exit_code_3"
						label="Ignore Exit Code 3"
						helpText="Don't fail on findings (exit code 3)"
						bind:cachedValue={formDataCache['prowler_ignore_exit_code_3']}
					/>

					<Checkbox
						{form}
						field="prowler_based_on_findings"
						label="Exit Based on Findings"
						helpText="Exit with code 3 if any findings are found"
						bind:cachedValue={formDataCache['prowler_based_on_findings']}
					/>
				</div>
			</div>
		</svelte:fragment>
	</AccordionItem>

	<AccordionItem>
		<svelte:fragment slot="summary">
			<i class="fa-solid fa-clock mr-2"></i>Scheduling
		</svelte:fragment>
		<svelte:fragment slot="content">
			<div class="p-4 space-y-4">
				<Checkbox
					{form}
					field="prowler_schedule_enabled"
					label="Enable Scheduled Scans"
					helpText="Run Prowler scans on a schedule"
					bind:cachedValue={formDataCache['prowler_schedule_enabled']}
				/>

				<RadioGroupInput
					{form}
					label="Scan Frequency"
					field="prowler_schedule_frequency"
					options={[
						{ label: 'Daily', value: 'daily' },
						{ label: 'Weekly', value: 'weekly' },
						{ label: 'Monthly', value: 'monthly' },
						{ label: 'Custom (Cron)', value: 'custom' }
					]}
					bind:cachedValue={formDataCache['prowler_schedule_frequency']}
				/>

				<TextField
					{form}
					field="prowler_cron_expression"
					label="Cron Expression"
					helpText="Custom cron expression (e.g., '0 2 * * 0' for weekly Sunday 2AM)"
					bind:cachedValue={formDataCache['prowler_cron_expression']}
				/>
			</div>
		</svelte:fragment>
	</AccordionItem>
</Accordion>
