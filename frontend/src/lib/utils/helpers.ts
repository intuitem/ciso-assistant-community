export function formatStringToDate(inputString: string, locale = 'en') {
	const date = new Date(inputString);
	return date.toLocaleDateString(locale, {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	});
}

export const isURL = (url: string) => {
	try {
		const urlToCheck = new URL(url);
		if (urlToCheck.protocol !== 'http:' && urlToCheck.protocol !== 'https:') return false;
		return true;
	} catch (e) {
		return false;
	}
};

export function getRequirementTitle(ref_id: string, name: string) {
	const pattern = (ref_id ? 2 : 0) + (name ? 1 : 0);
	const title: string =
		pattern == 3 ? `${ref_id} - ${name}` : pattern == 2 ? ref_id : pattern == 1 ? name : '';
	return title;
}

export function displayScoreColor(value: number | null, max_score: number, inversedColors = false) {
	value ??= 0;
	value = (value * 100) / max_score;
	if (inversedColors) {
		if (value < 25) {
			return 'stroke-green-300';
		}
		if (value < 50) {
			return 'stroke-yellow-300';
		}
		if (value < 75) {
			return 'stroke-orange-400';
		}
		return 'stroke-red-400';
	} else {
		if (value < 25) {
			return 'stroke-red-400';
		}
		if (value < 50) {
			return 'stroke-orange-400';
		}
		if (value < 75) {
			return 'stroke-yellow-300';
		}
		return 'stroke-green-300';
	}
}

export function formatScoreValue(value: number, max_score: number, fullDonut = false) {
	if (value === null) {
		return 0;
	} else if (fullDonut) {
		return 100;
	}
	return (value * 100) / max_score;
}

export function getSecureRedirect(url: any): string {
	const SECURE_REDIRECT_URL_REGEX = /^\/\w+/;
	return typeof url === 'string' && SECURE_REDIRECT_URL_REGEX.test(url) ? url : '';
}

export function darkenColor(hex: string, amount: number) {
	hex = hex.slice(1);
	const num = parseInt(hex, 16);

	let r = (num >> 16) - amount * 255;
	let g = ((num >> 8) & 0x00ff) - amount * 255;
	let b = (num & 0x0000ff) - amount * 255;

	r = Math.max(0, Math.min(255, r));
	g = Math.max(0, Math.min(255, g));
	b = Math.max(0, Math.min(255, b));

	return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}

export function stringify(value: string | number | boolean | null = null) {
	return String(value)
		.toLowerCase()
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '');
}

export function isDark(hexcolor: string): boolean {
	const r = parseInt(hexcolor.slice(1, 3), 16);
	const g = parseInt(hexcolor.slice(3, 5), 16);
	const b = parseInt(hexcolor.slice(5, 7), 16);
	// compute brightness from rgb values
	// https://www.w3.org/tr/aert/#color-contrast
	const brightness = (r * 299 + g * 587 + b * 114) / 1000;
	return brightness < 128;
}

// Get the search key from an option object or the option itself
// if it's a string or number
export const getSearchTarget = (opt: Option): string => {
	// Handle primitive values (string/number)
	if (typeof opt === 'string' || typeof opt === 'number') {
		return String(opt).trim();
	}

	// Handle non-object types
	if (!opt || typeof opt !== 'object') {
		return '';
	}

	// Validate object structure
	if (opt.label === undefined) {
		const opt_str = JSON.stringify(opt);
		console.error(`MultiSelect option ${opt_str} is an object but has no label key`);
		return '';
	}

	// Build searchable components
	const components: string[] = [];

	// Add path information (hierarchical context)
	if (opt.path && Array.isArray(opt.path)) {
		const pathString = opt.path
			.filter(Boolean) // Remove empty/null values
			.map((item) => String(item).trim())
			.join(' ');
		if (pathString) {
			components.push(pathString);
		}
	}

	// Add main label (primary searchable content)
	const mainLabel = String(opt.label || '').trim();
	if (mainLabel) {
		components.push(mainLabel);
	}

	// Add translated label if different from main label
	if (opt.translatedLabel && opt.translatedLabel !== opt.label) {
		const translatedLabel = String(opt.translatedLabel).trim();
		if (translatedLabel && translatedLabel !== mainLabel) {
			components.push(translatedLabel);
		}
	}

	// Add value if it's different from label (for ID-based searches)
	if (opt.value !== undefined && opt.value !== opt.label) {
		const valueString = String(opt.value).trim();
		if (valueString && valueString !== mainLabel) {
			components.push(valueString);
		}
	}

	// Add info string content
	if (opt.infoString?.string) {
		const infoString = String(opt.infoString.string).trim();
		if (infoString) {
			components.push(infoString);
		}
	}

	// Combine all components with spaces
	const searchTarget = components.join(' ');

	// Normalize the search target
	return normalizeSearchString(searchTarget);
};

// Helper function to normalize search strings for better matching
export function normalizeSearchString(str: string): string {
	return str
		.toLowerCase()
		.normalize('NFD') // Decompose accented characters
		.replace(/\p{Diacritic}/gu, '') // Remove combining marks (diacritics)
		.replace(/[^\w\s-]/g, ' ') // Replace special chars with spaces
		.replace(/\s+/g, ' ') // Collapse multiple spaces
		.trim();
}

export function isQuestionVisible(question: any, answers: any): boolean {
	if (!question.depends_on) return true;

	const dependency = question.depends_on;
	const targetAnswer = answers[dependency.question];
	if (!targetAnswer) return false;

	if (dependency.condition === 'any') {
		// If targetAnswer is an array (multiple choice)
		if (Array.isArray(targetAnswer)) {
			return targetAnswer.some((a) => dependency.answers.includes(a));
		}
		// Single value
		return dependency.answers.includes(targetAnswer);
	}

	if (dependency.condition === 'all') {
		if (Array.isArray(targetAnswer)) {
			return dependency.answers.every((a) => targetAnswer.includes(a));
		}
		// Single value (must match all, so only true if exactly one)
		return dependency.answers.length === 1 && dependency.answers[0] === targetAnswer;
	}

	return true; // fallback
}

export function computeRequirementScoreAndResult(questions: any, answers: any) {
	if (!questions) return { score: null, result: null };

	let totalScore: number | null = 0;
	let results: boolean[] | null = [];
	let visibleCount = 0;
	let answeredVisibleCount = 0;
	let hasAnyScorableQuestions = false;
	let hasAnyResultQuestions = false;

	// First pass: check if ANY question (visible or not) has scoring/result capability
	for (const [q_urn, question] of Object.entries(questions)) {
		if (question.choices && Array.isArray(question.choices)) {
			for (const choice of question.choices) {
				if (choice.add_score !== undefined && choice.add_score !== null) {
					hasAnyScorableQuestions = true;
				}
				if (choice.compute_result !== undefined && choice.compute_result !== null) {
					hasAnyResultQuestions = true;
				}
			}
		}
	}

	// If there are no scorable questions at all, return early
	if (!hasAnyScorableQuestions) {
		totalScore = null;
	}

	// Second pass: compute actual scores and results from visible, answered questions
	for (const [q_urn, question] of Object.entries(questions)) {
		if (!isQuestionVisible(question, answers)) continue;

		visibleCount++;

		const selectedChoiceURNs = answers?.[q_urn];

		// Determine if the question is actually answered:
		// - not answered if undefined or null
		// - not answered if string and empty after trim
		// - not answered if array and empty (important for multiple_choice)
		const hasAnswer =
			selectedChoiceURNs !== undefined &&
			selectedChoiceURNs !== null &&
			!(typeof selectedChoiceURNs === 'string' && selectedChoiceURNs.trim() === '') &&
			!(Array.isArray(selectedChoiceURNs) && selectedChoiceURNs.length === 0);

		if (!hasAnswer) {
			// visible but unanswered -> will lead to 'not_assessed' overall
			continue;
		}

		answeredVisibleCount++;

		const choiceURNs = Array.isArray(selectedChoiceURNs)
			? selectedChoiceURNs
			: [selectedChoiceURNs];

		// Validate that choices array exists before iterating
		if (!question.choices || !Array.isArray(question.choices)) continue;

		for (const urn of choiceURNs) {
			const selectedChoice = question.choices.find((choice: any) => choice.urn === urn);
			if (!selectedChoice) continue;

			if (selectedChoice.add_score !== undefined && selectedChoice.add_score !== null) {
				totalScore += selectedChoice.add_score;
			}

			if (selectedChoice.compute_result !== undefined && selectedChoice.compute_result !== null) {
				results.push(!!selectedChoice.compute_result);
			}
		}
	}

	// No visible questions → not applicable
	if (visibleCount === 0) {
		return { score: 0, result: 'not_applicable' };
	}

	// Not all visible questions are answered → not assessed
	if (answeredVisibleCount < visibleCount) {
		return { score: totalScore, result: 'not_assessed' };
	}

	// Compute overall result
	let result = hasAnyResultQuestions ? 'not_assessed' : null;
	if (results?.length > 0) {
		if (results.every((r) => r === true)) result = 'compliant';
		else if (results.some((r) => r === true)) result = 'partially_compliant';
		else result = 'non_compliant';
	}

	return { score: totalScore, result };
}
