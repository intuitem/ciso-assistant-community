<script lang="ts">
	import { isDark } from '$lib/utils/helpers';
	import { m } from '$paraglide/messages';

	interface Level {
		id: number;
		abbreviation: string;
		name: string;
		description: string;
		hexcolor: string;
	}

	interface Props {
		levels: Level[];
		title: string;
		onchange: (levels: Level[]) => void;
	}

	let { levels = $bindable(), title, onchange }: Props = $props();

	const COLOR_PALETTES: Record<string, string[]> = {
		classic: [
			'#4CAF50',
			'#8BC34A',
			'#FFEB3B',
			'#FF9800',
			'#F44336',
			'#B71C1C',
			'#4A148C',
			'#1A237E'
		],
		accessible: [
			'#0072B2',
			'#56B4E9',
			'#F0E442',
			'#E69F00',
			'#D55E00',
			'#CC79A7',
			'#009E73',
			'#000000'
		],
		warm: ['#FFF9C4', '#FFE082', '#FFB74D', '#FF8A65', '#E57373', '#EF5350', '#C62828', '#880E4F'],
		cool: ['#E0F7FA', '#80DEEA', '#4DD0E1', '#26C6DA', '#00ACC1', '#00838F', '#006064', '#004D40']
	};

	let selectedPalette = $state('classic');

	const DEFAULT_COLORS = COLOR_PALETTES.classic;

	function applyPalette(paletteName: string) {
		selectedPalette = paletteName;
		const palette = COLOR_PALETTES[paletteName];
		levels = levels.map((l, i) => ({
			...l,
			hexcolor: palette[i % palette.length]
		}));
		onchange(levels);
	}

	function addLevel() {
		const newId = levels.length;
		const color = DEFAULT_COLORS[newId % DEFAULT_COLORS.length];
		levels = [
			...levels,
			{
				id: newId,
				abbreviation: String(newId + 1),
				name: '',
				description: '',
				hexcolor: color
			}
		];
		onchange(levels);
	}

	function removeLevel(index: number) {
		if (levels.length <= 2) return;
		levels = levels.filter((_, i) => i !== index).map((l, i) => ({ ...l, id: i }));
		onchange(levels);
	}

	function updateLevel(index: number, field: keyof Level, value: string) {
		levels = levels.map((l, i) => (i === index ? { ...l, [field]: value } : l));
		onchange(levels);
	}

	function moveLevel(index: number, direction: -1 | 1) {
		const target = index + direction;
		if (target < 0 || target >= levels.length) return;
		const newLevels = [...levels];
		[newLevels[index], newLevels[target]] = [newLevels[target], newLevels[index]];
		levels = newLevels.map((l, i) => ({ ...l, id: i }));
		onchange(levels);
	}
</script>

<div class="space-y-3">
	<div class="flex items-center justify-between flex-wrap gap-2">
		<h3 class="text-lg font-semibold">{title}</h3>
		<div class="flex items-center gap-2">
			<!-- Color palette presets -->
			<div class="flex items-center gap-1">
				<span class="text-xs text-gray-500"><i class="fa-solid fa-palette mr-1"></i></span>
				{#each Object.entries(COLOR_PALETTES) as [name, colors]}
					<button
						type="button"
						class="flex gap-0.5 px-1.5 py-1 rounded border text-xs {selectedPalette === name
							? 'border-primary-500 ring-1 ring-primary-300'
							: 'border-gray-300'}"
						onclick={() => applyPalette(name)}
						title={name}
					>
						{#each colors.slice(0, 4) as color}
							<span class="w-3 h-3 rounded-sm inline-block" style="background-color: {color}"
							></span>
						{/each}
					</button>
				{/each}
			</div>
			<button type="button" class="btn variant-filled-primary btn-sm" onclick={addLevel}>
				<i class="fa-solid fa-plus mr-1"></i>
				{m.addLevel()}
			</button>
		</div>
	</div>

	<div class="table-container">
		<table class="table table-compact w-full">
			<thead>
				<tr>
					<th class="w-12">#</th>
					<th class="w-24">{m.abbreviation()}</th>
					<th>{m.name()}</th>
					<th>{m.description()}</th>
					<th class="w-20">{m.hexcolor()}</th>
					<th class="w-28"></th>
				</tr>
			</thead>
			<tbody>
				{#each levels as level, i}
					<tr>
						<td>
							<span
								class="inline-flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold"
								style="background-color: {level.hexcolor}; color: {isDark(level.hexcolor)
									? 'white'
									: 'black'}"
							>
								{level.id}
							</span>
						</td>
						<td>
							<input
								type="text"
								class="input input-sm w-full"
								value={level.abbreviation}
								oninput={(e) => updateLevel(i, 'abbreviation', e.currentTarget.value)}
								placeholder="..."
							/>
						</td>
						<td>
							<input
								type="text"
								class="input input-sm w-full"
								value={level.name}
								oninput={(e) => updateLevel(i, 'name', e.currentTarget.value)}
								placeholder={m.levelNamePlaceholder()}
							/>
						</td>
						<td>
							<input
								type="text"
								class="input input-sm w-full"
								value={level.description}
								oninput={(e) => updateLevel(i, 'description', e.currentTarget.value)}
								placeholder={m.descriptionPlaceholder()}
							/>
						</td>
						<td>
							<input
								type="color"
								class="w-10 h-8 cursor-pointer rounded border"
								value={level.hexcolor}
								oninput={(e) => updateLevel(i, 'hexcolor', e.currentTarget.value)}
							/>
						</td>
						<td class="flex gap-1 items-center">
							<button
								type="button"
								class="btn btn-sm variant-ghost"
								disabled={i === 0}
								onclick={() => moveLevel(i, -1)}
								title={m.moveUp()}
							>
								<i class="fa-solid fa-arrow-up text-xs"></i>
							</button>
							<button
								type="button"
								class="btn btn-sm variant-ghost"
								disabled={i === levels.length - 1}
								onclick={() => moveLevel(i, 1)}
								title={m.moveDown()}
							>
								<i class="fa-solid fa-arrow-down text-xs"></i>
							</button>
							<button
								type="button"
								class="btn btn-sm variant-ghost-error"
								disabled={levels.length <= 2}
								onclick={() => removeLevel(i)}
								title={m.removeLevel()}
							>
								<i class="fa-solid fa-trash text-xs"></i>
							</button>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
