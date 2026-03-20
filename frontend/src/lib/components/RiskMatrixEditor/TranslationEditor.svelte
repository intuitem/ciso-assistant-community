<script lang="ts">
	import { isDark } from '$lib/utils/helpers';
	import { m } from '$paraglide/messages';
	import { LOCALE_MAP, language } from '$lib/utils/locales';

	interface Level {
		id: number;
		abbreviation: string;
		name: string;
		description: string;
		hexcolor: string;
		translations?: Record<string, { name?: string; description?: string }>;
	}

	interface Props {
		probabilityLevels: Level[];
		impactLevels: Level[];
		riskLevels: Level[];
		onchange: (probabilityLevels: Level[], impactLevels: Level[], riskLevels: Level[]) => void;
	}

	let {
		probabilityLevels = $bindable(),
		impactLevels = $bindable(),
		riskLevels = $bindable(),
		onchange
	}: Props = $props();

	const AVAILABLE_LANGUAGES = Object.entries(LOCALE_MAP)
		.filter(([code]) => code !== 'en')
		.map(([code, info]) => ({ code, name: language[info.name] ?? info.name }));

	let selectedLang = $state('fr');

	// Get existing languages used across all levels
	let usedLanguages = $derived(() => {
		const langs = new Set<string>();
		for (const levels of [probabilityLevels, impactLevels, riskLevels]) {
			for (const level of levels) {
				if (level.translations) {
					for (const lang of Object.keys(level.translations)) {
						langs.add(lang);
					}
				}
			}
		}
		return langs;
	});

	function getTranslation(level: Level, lang: string, field: 'name' | 'description'): string {
		return level.translations?.[lang]?.[field] ?? '';
	}

	function setTranslation(
		category: 'probability' | 'impact' | 'risk',
		index: number,
		lang: string,
		field: 'name' | 'description',
		value: string
	) {
		function updateLevel(level: Level): Level {
			const translations = { ...level.translations };
			if (!translations[lang]) {
				translations[lang] = {};
			}
			translations[lang] = { ...translations[lang], [field]: value };
			return { ...level, translations };
		}

		if (category === 'probability') {
			probabilityLevels = probabilityLevels.map((l, i) => (i === index ? updateLevel(l) : l));
		} else if (category === 'impact') {
			impactLevels = impactLevels.map((l, i) => (i === index ? updateLevel(l) : l));
		} else {
			riskLevels = riskLevels.map((l, i) => (i === index ? updateLevel(l) : l));
		}
		onchange(probabilityLevels, impactLevels, riskLevels);
	}

	const categories = [
		{ key: 'probability' as const, label: () => m.probability(), levels: () => probabilityLevels },
		{ key: 'impact' as const, label: () => m.impact(), levels: () => impactLevels },
		{ key: 'risk' as const, label: () => m.riskLevels(), levels: () => riskLevels }
	];
</script>

<div class="space-y-4">
	<!-- Language selector -->
	<div class="flex items-center gap-3">
		<label class="label" for="lang-select">
			<span class="font-semibold">{m.locale()}:</span>
		</label>
		<select id="lang-select" class="select select-sm w-48" bind:value={selectedLang}>
			{#each AVAILABLE_LANGUAGES as lang}
				<option value={lang.code}>
					{lang.name} ({lang.code})
					{#if usedLanguages().has(lang.code)}*{/if}
				</option>
			{/each}
		</select>
		<span class="text-xs text-gray-400">* = has translations</span>
	</div>

	<!-- Translation tables per category -->
	{#each categories as cat}
		<div>
			<h4 class="font-semibold text-sm mb-2">{cat.label()}</h4>
			<div class="table-container">
				<table class="table table-compact w-full">
					<thead>
						<tr>
							<th class="w-12">#</th>
							<th class="w-1/4">{m.name()} (original)</th>
							<th class="w-1/4">{m.name()} ({selectedLang})</th>
							<th class="w-1/4">{m.description()} (original)</th>
							<th class="w-1/4">{m.description()} ({selectedLang})</th>
						</tr>
					</thead>
					<tbody>
						{#each cat.levels() as level, i}
							<tr>
								<td>
									<span
										class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold"
										style="background-color: {level.hexcolor}; color: {isDark(level.hexcolor)
											? 'white'
											: 'black'}"
									>
										{level.id}
									</span>
								</td>
								<td>
									<span class="text-sm text-gray-600">{level.name}</span>
								</td>
								<td>
									<input
										type="text"
										class="input input-sm w-full"
										value={getTranslation(level, selectedLang, 'name')}
										oninput={(e) =>
											setTranslation(cat.key, i, selectedLang, 'name', e.currentTarget.value)}
										placeholder="{level.name}..."
									/>
								</td>
								<td>
									<span
										class="text-sm text-gray-600 truncate block max-w-48"
										title={level.description}
									>
										{level.description}
									</span>
								</td>
								<td>
									<input
										type="text"
										class="input input-sm w-full"
										value={getTranslation(level, selectedLang, 'description')}
										oninput={(e) =>
											setTranslation(
												cat.key,
												i,
												selectedLang,
												'description',
												e.currentTarget.value
											)}
										placeholder="{level.description}..."
									/>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/each}
</div>
