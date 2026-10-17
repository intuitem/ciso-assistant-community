<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { m } from '$paraglide/messages';
	import { Switch } from '@skeletonlabs/skeleton-svelte';
	import { untrack } from 'svelte';

	interface Props {
		data: { mailerSettings: MailerConfigApi | null; mailerHealth?: HealthRow[] };
	}

	let { data }: Props = $props();

	type Encryption = 'none' | 'starttls' | 'ssl';
	type MailerForm = {
		position: number;
		transport: 'smtp' | 'smtp-oauth2';
		host: string;
		port: string;
		encryption: Encryption;
		username: string;
		password: string;
		has_password: boolean;
		oauth2_grant_type: string;
		oauth2_token_url: string;
		oauth2_scope: string;
		oauth2_client_id: string;
		oauth2_client_secret: string;
		has_oauth2_client_secret: boolean;
		oauth2_refresh_token: string;
		has_oauth2_refresh_token: boolean;
		oauth2_issuer: string;
		oauth2_private_key: string;
		has_oauth2_private_key: boolean;
		oauth2_audience: string;
	};

	type MailerTestResult = {
		mailer: string;
		ok: boolean;
		backend?: string | null;
		error?: string | null;
	};
	type TestResult = {
		ok: boolean;
		recipient?: string;
		error?: string | null;
		results?: MailerTestResult[];
		test_token?: string;
	};
	type HealthRow = {
		alias: string;
		source: string;
		last_attempt_at: string | null;
		last_outcome: string | null;
		last_error: string;
		via_failover: boolean;
		last_success_at: string | null;
	};
	type MailerApi = Partial<MailerForm> & {
		position: number;
		port?: number | null;
		use_tls?: boolean;
		use_ssl?: boolean;
	};
	type MailerConfigApi = {
		is_active: boolean;
		from_email: string;
		last_tested_at: string | null;
		mailers: MailerApi[];
	};

	const toastStore = getToastStore();

	function emptyMailer(position: number): MailerForm {
		return {
			position,
			transport: 'smtp',
			host: '',
			port: '',
			encryption: 'starttls',
			username: '',
			password: '',
			has_password: false,
			oauth2_grant_type: 'client_credentials',
			oauth2_token_url: '',
			oauth2_scope: '',
			oauth2_client_id: '',
			oauth2_client_secret: '',
			has_oauth2_client_secret: false,
			oauth2_refresh_token: '',
			has_oauth2_refresh_token: false,
			oauth2_issuer: '',
			oauth2_private_key: '',
			has_oauth2_private_key: false,
			oauth2_audience: ''
		};
	}

	function fromApi(row: MailerApi): MailerForm {
		return {
			...emptyMailer(row.position),
			...row,
			port: row.port == null ? '' : String(row.port),
			encryption: row.use_ssl ? 'ssl' : row.use_tls ? 'starttls' : 'none',
			// Secrets never come back from the API; the form starts blank and
			// a blank value on save means "keep the stored one".
			password: '',
			oauth2_client_secret: '',
			oauth2_refresh_token: '',
			oauth2_private_key: ''
		};
	}

	function toApi(form: MailerForm): Record<string, unknown> {
		const api: Record<string, unknown> = {
			...form,
			port: form.port === '' ? null : Number(form.port),
			use_tls: form.encryption === 'starttls',
			use_ssl: form.encryption === 'ssl'
		};
		// Form-only fields; the API neither expects nor wants them.
		for (const key of [
			'encryption',
			'has_password',
			'has_oauth2_client_secret',
			'has_oauth2_refresh_token',
			'has_oauth2_private_key'
		]) {
			delete api[key];
		}
		return api;
	}

	// Seed the form once from the loaded configuration; later loads refresh
	// `data` for the health table, the form keeps what the admin typed.
	const initial = untrack(() => data.mailerSettings);
	let isActive = $state<boolean>(initial?.is_active ?? false);
	let fromEmail = $state<string>(initial?.from_email ?? '');
	let mailers = $state<MailerForm[]>(
		initial?.mailers?.length ? initial.mailers.map(fromApi) : [emptyMailer(1)]
	);
	let lastTestedAt = $state<string | null>(initial?.last_tested_at ?? null);
	let override = $state(false);
	let testToken = $state<string | null>(null);
	let testResult = $state<TestResult | null>(null);
	let testing = $state(false);
	let saving = $state(false);

	const health = $derived<HealthRow[]>(data.mailerHealth ?? []);
	const canSave = $derived(Boolean(testToken) || override);

	function invalidateTest() {
		// The token proves these exact values were tested; any edit voids it.
		testToken = null;
		testResult = null;
	}

	function payload(extra: Record<string, unknown> = {}) {
		return {
			is_active: isActive,
			from_email: fromEmail,
			mailers: mailers.map(toApi),
			...extra
		};
	}

	function describeError(body: unknown): string {
		if (!body) return m.anErrorOccurred();
		if (typeof body === 'string') return body;
		if (typeof body !== 'object') return String(body);
		const record = body as Record<string, unknown>;
		if (record.error) return String(record.error);
		return Object.entries(record)
			.map(
				([field, messages]) =>
					`${field}: ${Array.isArray(messages) ? messages.join(' ') : JSON.stringify(messages)}`
			)
			.join(' ');
	}

	async function sendTest() {
		testing = true;
		try {
			const response = await fetch('/fe-api/mailer-settings/test', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload())
			});
			const body = await response.json();
			if (!response.ok) {
				testResult = { ok: false, error: describeError(body), results: [] };
				testToken = null;
				return;
			}
			testResult = body;
			testToken = body.ok ? (body.test_token ?? null) : null;
			await invalidateAll();
		} catch (error) {
			testResult = { ok: false, error: String(error), results: [] };
			testToken = null;
		} finally {
			testing = false;
		}
	}

	async function save() {
		saving = true;
		try {
			const response = await fetch('/fe-api/mailer-settings', {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload({ test_token: testToken ?? '', override_untested: override }))
			});
			const body = await response.json();
			if (!response.ok) {
				toastStore.trigger({
					message: m.mailerSaveFailed({ error: describeError(body) }),
					background: 'preset-filled-error-500'
				});
				return;
			}
			toastStore.trigger({ message: m.mailerSaved(), background: 'preset-filled-success-500' });
			testToken = null;
			testResult = null;
			override = false;
			await invalidateAll();
			mailers = body.mailers?.length ? body.mailers.map(fromApi) : [emptyMailer(1)];
			lastTestedAt = body.last_tested_at ?? null;
		} catch (error) {
			toastStore.trigger({
				message: m.mailerSaveFailed({ error: String(error) }),
				background: 'preset-filled-error-500'
			});
		} finally {
			saving = false;
		}
	}

	function addSecondary() {
		if (mailers.length < 2) mailers = [...mailers, emptyMailer(2)];
		invalidateTest();
	}

	function removeSecondary() {
		mailers = mailers.slice(0, 1);
		invalidateTest();
	}

	// Provider values live here and in the installation docs, never in the backend.
	function fillMicrosoft(mailer: MailerForm) {
		Object.assign(mailer, {
			transport: 'smtp-oauth2',
			host: 'smtp.office365.com',
			port: '587',
			encryption: 'starttls',
			oauth2_grant_type: 'client_credentials',
			oauth2_token_url: 'https://login.microsoftonline.com/<tenant id>/oauth2/v2.0/token',
			oauth2_scope: 'https://outlook.office365.com/.default'
		});
		invalidateTest();
	}

	function fillGoogle(mailer: MailerForm) {
		Object.assign(mailer, {
			transport: 'smtp-oauth2',
			host: 'smtp.gmail.com',
			port: '587',
			encryption: 'starttls',
			oauth2_grant_type: 'jwt_bearer',
			oauth2_token_url: 'https://oauth2.googleapis.com/token',
			oauth2_scope: 'https://mail.google.com/'
		});
		invalidateTest();
	}

	function outcomeLabel(outcome: string | null): string {
		if (!outcome) return m.mailerOutcomeNever();
		if (outcome === 'ok') return m.mailerOutcomeOk();
		if (outcome === 'unreachable') return m.mailerOutcomeUnreachable();
		return m.mailerOutcomeFailed();
	}

	function sourceLabel(source: string): string {
		return source === 'custom' ? m.mailerSourceCustom() : m.mailerSourceEnvironment();
	}

	function when(value: string | null): string {
		return value ? new Date(value).toLocaleString() : m.mailerNever();
	}

	const inputClass =
		'input w-full text-sm border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40';
</script>

<div class="flex flex-col gap-6" oninput={invalidateTest}>
	<span class="text-surface-600-400">{m.mailerSettingsDescription()}</span>

	<div class="card p-4 flex flex-col gap-4">
		<div class="flex items-center justify-between gap-4">
			<div>
				<p class="font-semibold">{m.mailerUseCustom()}</p>
				<p class="text-sm text-surface-600-400">{m.mailerUseCustomHelp()}</p>
			</div>
			<Switch
				name="mailer-active"
				checked={isActive}
				onCheckedChange={(e) => {
					isActive = e.checked;
					invalidateTest();
				}}
				data-testid="mailer-active"
			>
				<Switch.Control><Switch.Thumb /></Switch.Control>
				<Switch.HiddenInput />
			</Switch>
		</div>
		<label class="label">
			<span class="text-sm font-medium">{m.mailerSenderAddress()}</span>
			<input
				class={inputClass}
				type="email"
				bind:value={fromEmail}
				data-testid="mailer-from-email"
			/>
		</label>
		{#if lastTestedAt}
			<p class="text-xs text-surface-600-400">
				{m.mailerLastTested()}: {when(lastTestedAt)}
			</p>
		{/if}
	</div>

	{#each mailers as mailer, index (mailer.position)}
		<div class="card p-4 flex flex-col gap-4" data-testid="mailer-{mailer.position}">
			<div class="flex items-center justify-between gap-4 flex-wrap">
				<h3 class="text-base font-semibold flex items-center gap-2">
					<i class="fa-solid fa-server text-sm text-primary-500"></i>
					{index === 0 ? m.mailerPrimary() : m.mailerSecondary()}
				</h3>
				<div class="flex items-center gap-2">
					<button
						type="button"
						class="btn btn-sm preset-tonal"
						onclick={() => fillMicrosoft(mailer)}
					>
						{m.mailerFillMicrosoft()}
					</button>
					<button type="button" class="btn btn-sm preset-tonal" onclick={() => fillGoogle(mailer)}>
						{m.mailerFillGoogle()}
					</button>
					{#if index === 1}
						<button type="button" class="btn btn-sm preset-tonal-error" onclick={removeSecondary}>
							{m.mailerRemoveSecondary()}
						</button>
					{/if}
				</div>
			</div>
			{#if index === 1}
				<p class="text-sm text-surface-600-400">{m.mailerSecondaryHelp()}</p>
			{/if}

			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<label class="label">
					<span class="text-sm font-medium">{m.mailerTransport()}</span>
					<select class="select" bind:value={mailer.transport}>
						<option value="smtp">{m.mailerTransportPassword()}</option>
						<option value="smtp-oauth2">{m.mailerTransportOauth2()}</option>
					</select>
				</label>
				<label class="label">
					<span class="text-sm font-medium">{m.mailerEncryption()}</span>
					<select class="select" bind:value={mailer.encryption}>
						<option value="starttls">{m.mailerEncryptionStarttls()}</option>
						<option value="ssl">{m.mailerEncryptionSsl()}</option>
						<option value="none">{m.mailerEncryptionNone()}</option>
					</select>
				</label>
				<label class="label">
					<span class="text-sm font-medium">{m.mailerHost()}</span>
					<input class={inputClass} type="text" bind:value={mailer.host} />
				</label>
				<label class="label">
					<span class="text-sm font-medium">{m.mailerPort()}</span>
					<input
						class={inputClass}
						type="number"
						min="1"
						max="65535"
						placeholder={mailer.use_ssl ? '465' : '25'}
						bind:value={mailer.port}
					/>
				</label>
				<label class="label">
					<span class="text-sm font-medium">
						{mailer.transport === 'smtp-oauth2' ? m.mailerMailbox() : m.mailerUsername()}
					</span>
					<input class={inputClass} type="text" bind:value={mailer.username} />
				</label>
				{#if mailer.transport === 'smtp'}
					<label class="label">
						<span class="text-sm font-medium">{m.mailerPassword()}</span>
						<input
							class={inputClass}
							type="password"
							autocomplete="new-password"
							bind:value={mailer.password}
						/>
						{#if mailer.has_password}
							<span class="text-xs text-surface-600-400">{m.mailerSecretStored()}</span>
						{/if}
					</label>
				{/if}
			</div>

			{#if mailer.transport === 'smtp-oauth2'}
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<label class="label">
						<span class="text-sm font-medium">{m.mailerGrantType()}</span>
						<select class="select" bind:value={mailer.oauth2_grant_type}>
							<option value="client_credentials">client_credentials</option>
							<option value="jwt_bearer">jwt_bearer</option>
							<option value="refresh_token">refresh_token</option>
						</select>
					</label>
					<label class="label">
						<span class="text-sm font-medium">{m.mailerTokenUrl()}</span>
						<input class={inputClass} type="url" bind:value={mailer.oauth2_token_url} />
					</label>
					<label class="label md:col-span-2">
						<span class="text-sm font-medium">{m.mailerScope()}</span>
						<input class={inputClass} type="text" bind:value={mailer.oauth2_scope} />
					</label>
					{#if mailer.oauth2_grant_type !== 'jwt_bearer'}
						<label class="label">
							<span class="text-sm font-medium">{m.mailerClientId()}</span>
							<input class={inputClass} type="text" bind:value={mailer.oauth2_client_id} />
						</label>
						<label class="label">
							<span class="text-sm font-medium">{m.mailerClientSecret()}</span>
							<input
								class={inputClass}
								type="password"
								autocomplete="new-password"
								bind:value={mailer.oauth2_client_secret}
							/>
							{#if mailer.has_oauth2_client_secret}
								<span class="text-xs text-surface-600-400">{m.mailerSecretStored()}</span>
							{/if}
						</label>
					{/if}
					{#if mailer.oauth2_grant_type === 'refresh_token'}
						<label class="label md:col-span-2">
							<span class="text-sm font-medium">{m.mailerRefreshToken()}</span>
							<input
								class={inputClass}
								type="password"
								autocomplete="new-password"
								bind:value={mailer.oauth2_refresh_token}
							/>
							{#if mailer.has_oauth2_refresh_token}
								<span class="text-xs text-surface-600-400">{m.mailerSecretStored()}</span>
							{/if}
						</label>
					{/if}
					{#if mailer.oauth2_grant_type === 'jwt_bearer'}
						<label class="label">
							<span class="text-sm font-medium">{m.mailerIssuer()}</span>
							<input class={inputClass} type="text" bind:value={mailer.oauth2_issuer} />
						</label>
						<label class="label">
							<span class="text-sm font-medium">{m.mailerAudience()}</span>
							<input class={inputClass} type="url" bind:value={mailer.oauth2_audience} />
						</label>
						<label class="label md:col-span-2">
							<span class="text-sm font-medium">{m.mailerPrivateKey()}</span>
							<textarea
								class="{inputClass} font-mono"
								rows="6"
								autocomplete="off"
								bind:value={mailer.oauth2_private_key}
							></textarea>
							{#if mailer.has_oauth2_private_key}
								<span class="text-xs text-surface-600-400">{m.mailerSecretStored()}</span>
							{/if}
						</label>
					{/if}
				</div>
			{/if}
		</div>
	{/each}

	{#if mailers.length < 2}
		<div>
			<button type="button" class="btn btn-sm preset-tonal" onclick={addSecondary}>
				<i class="fa-solid fa-plus mr-1"></i>
				{m.mailerAddSecondary()}
			</button>
		</div>
	{/if}

	<div class="card p-4 flex flex-col gap-3">
		<div class="flex items-center gap-3 flex-wrap">
			<button
				type="button"
				class="btn preset-tonal-primary"
				disabled={testing}
				onclick={sendTest}
				data-testid="mailer-send-test"
			>
				<i class="fa-solid fa-paper-plane mr-1"></i>
				{m.mailerSendTest()}
			</button>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				disabled={saving || !canSave}
				onclick={save}
				data-testid="mailer-save"
			>
				{m.save()}
			</button>
			{#if !canSave}
				<span class="text-sm text-surface-600-400">{m.mailerTestRequired()}</span>
			{/if}
		</div>
		<p class="text-xs text-surface-600-400">{m.mailerSendTestHelp()}</p>
		{#if testResult}
			<div
				class="rounded p-3 text-sm {testResult.ok ? 'preset-tonal-success' : 'preset-tonal-error'}"
				data-testid="mailer-test-result"
			>
				{#if testResult.error}
					{m.mailerTestFailed({ error: testResult.error })}
				{:else}
					{testResult.ok ? m.mailerTestAllOk() : m.mailerTestSomeFailed()}
				{/if}
				{#each testResult.results ?? [] as result (result.mailer)}
					<div class="text-xs mt-1">
						{#if result.ok}
							<i class="fa-solid fa-check mr-1"></i>
							{m.mailerTestMailerOk({
								mailer: result.mailer,
								recipient: testResult.recipient ?? ''
							})}
						{:else}
							<i class="fa-solid fa-xmark mr-1"></i>
							{m.mailerTestMailerFailed({ mailer: result.mailer, error: result.error ?? '' })}
						{/if}
					</div>
				{/each}
			</div>
		{/if}
		<label class="flex items-center gap-2 text-sm">
			<input
				class="checkbox"
				type="checkbox"
				bind:checked={override}
				data-testid="mailer-override"
			/>
			{m.mailerOverrideUntested()}
		</label>
	</div>

	<div class="card overflow-hidden">
		<h3 class="text-base font-semibold flex items-center gap-2 p-4">
			<i class="fa-solid fa-heart-pulse text-sm text-primary-500"></i>
			{m.mailerDeliveryHealth()}
		</h3>
		{#if health.length === 0}
			<p class="text-sm text-surface-600-400 px-4 pb-4">{m.mailerDeliveryHealthEmpty()}</p>
		{:else}
			<table class="table w-full text-sm" data-testid="mailer-health">
				<thead>
					<tr class="bg-surface-100-900">
						<th class="px-4 py-2 text-left font-medium">{m.mailerHealthMailer()}</th>
						<th class="px-4 py-2 text-left font-medium">{m.mailerHealthSource()}</th>
						<th class="px-4 py-2 text-left font-medium">{m.mailerHealthLastAttempt()}</th>
						<th class="px-4 py-2 text-left font-medium">{m.mailerHealthOutcome()}</th>
						<th class="px-4 py-2 text-left font-medium">{m.mailerHealthLastSuccess()}</th>
					</tr>
				</thead>
				<tbody>
					{#each health as row (row.alias)}
						<tr class="border-t border-surface-200-800">
							<td class="px-4 py-2 font-mono text-xs">{row.alias}</td>
							<td class="px-4 py-2 text-xs text-surface-600-400">{sourceLabel(row.source)}</td>
							<td class="px-4 py-2 text-xs">{when(row.last_attempt_at)}</td>
							<td class="px-4 py-2">
								<span
									class="badge {row.last_outcome === 'ok'
										? 'preset-filled-success-500'
										: row.last_outcome
											? 'preset-filled-error-500'
											: 'preset-tonal'}"
								>
									{outcomeLabel(row.last_outcome)}
								</span>
								{#if row.via_failover}
									<span class="text-xs text-surface-600-400 ml-1"
										>({m.mailerHealthViaFailover()})</span
									>
								{/if}
								{#if row.last_error}
									<div class="text-xs text-surface-600-400 mt-1 break-all">{row.last_error}</div>
								{/if}
							</td>
							<td class="px-4 py-2 text-xs">{when(row.last_success_at)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</div>
