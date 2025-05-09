<script lang="ts">
  import { safeTranslate } from '$lib/utils/i18n';
  export let data;
  console.log(Object.entries(data.log.changes))
</script>

<main class="card shadow-lg bg-white p-4">
	<!-- Main content area - modified to use flex layout -->
		<div class="flex w-full">
			<div class="w-full rounded-lg border border-gray-100 py-3 shadow-sm">
				<dl class="-my-3 divide-y divide-gray-100 text-sm">
					{#each Object.entries(data.log.changes) as [field, change]}
          {@const before = change[0]}
          {@const after = change[1]}
						<div class="grid grid-cols-6 gap-4 py-3 px-2 even:bg-gray-50">
							<dt
								class="font-medium text-gray-900"
								data-testid="{field.replace('_', '-')}-field-title"
							>
								{safeTranslate(field)}
							</dt>
							<dd class="text-gray-700 col-span-2">
								<ul>
									<li
										class="list-none whitespace-pre-line"
										data-testid={!(change instanceof Array)
											? field.replace('_', '-') + '-before-value'
											: null}
									>
                  {before}
									</li>
								</ul>
							</dd>
              <i class="fa-solid fa-arrow-right" />
							<dd class="text-gray-700 col-span-2">
								<ul>
									<li
										class="list-none whitespace-pre-line"
										data-testid={!(change instanceof Array)
											? field.replace('_', '-') + '-after-value'
											: null}
									>
                  {after}
									</li>
								</ul>
							</dd>
						</div>
					{/each}
				</dl>
			</div>
		</div>
</main>

