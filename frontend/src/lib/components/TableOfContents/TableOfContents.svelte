<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { m } from '$paraglide/messages';

	interface TocItem {
		id: string;
		title: string;
		level: number;
	}

	interface Props {
		items: TocItem[];
		isVisible?: boolean;
		position?: 'left' | 'right';
		className?: string;
	}

	let { items, isVisible = true, position = 'right', className = '' }: Props = $props();

	let activeId = $state('');
	let isCollapsed = $state(false);
	let searchQuery = $state('');
	let focusedIndex = $state(-1);
	let tocContainer = $state<HTMLDivElement>();
	let searchInput = $state<HTMLInputElement>();
	let navigationButtons = $state<HTMLButtonElement[]>([]);
	let isScrolling = $state(false);

	// Observer for active section tracking
	let observer: IntersectionObserver;

	let filteredItems = $derived(
		items.filter((item) => item.title.toLowerCase().includes(searchQuery.toLowerCase()))
	);

	$effect(() => {
		if (filteredItems.length > 0 && focusedIndex >= filteredItems.length) {
			focusedIndex = 0;
		}
	});

	onMount(() => {
		if (browser) {
			const observerOptions = {
				rootMargin: '-10% 0% -80% 0%',
				threshold: 0.1
			};

			observer = new IntersectionObserver((entries) => {
				if (isScrolling) return;

				let maxRatio = 0;
				let mostVisibleEntry = null;

				entries.forEach((entry) => {
					if (entry.isIntersecting && entry.intersectionRatio > maxRatio) {
						maxRatio = entry.intersectionRatio;
						mostVisibleEntry = entry;
					}
				});

				if (mostVisibleEntry) {
					activeId = mostVisibleEntry.target.id;
				}
			}, observerOptions);

			// Observe all sections
			items.forEach((item) => {
				const element = document.getElementById(item.id);
				if (element) {
					observer.observe(element);
				}
			});

			const handleClickOutside = (event: MouseEvent) => {
				if (tocContainer && !tocContainer.contains(event.target as Node) && !isCollapsed) {
					isCollapsed = true;
				}
			};

			document.addEventListener('click', handleClickOutside);

			return () => {
				if (observer) {
					observer.disconnect();
				}
				document.removeEventListener('click', handleClickOutside);
			};
		}
	});

	function scrollToSection(id: string) {
		isScrolling = true;
		activeId = id;

		const element = document.getElementById(id);
		if (element) {
			element.scrollIntoView({
				behavior: 'smooth',
				block: 'start'
			});
		}

		// Reset scrolling state after scroll completes
		setTimeout(() => {
			isScrolling = false;
		}, 1000);
		if (window.innerWidth < 1024) {
			isCollapsed = true;
		}
	}

	function toggleCollapse() {
		isCollapsed = !isCollapsed;
		if (!isCollapsed) {
			setTimeout(() => {
				if (searchInput) {
					searchInput.focus();
				}
			}, 100);
		} else {
			searchQuery = '';
			focusedIndex = -1;
		}
	}

	function clearSearch() {
		searchQuery = '';
		focusedIndex = -1;
		if (searchInput) {
			searchInput.focus();
		}
	}

	function focusItem(index: number) {
		if (index >= 0 && index < filteredItems.length && navigationButtons[index]) {
			focusedIndex = index;
			navigationButtons[index].focus();
			navigationButtons[index].scrollIntoView({
				block: 'nearest',
				behavior: 'smooth'
			});
		}
	}

	function navigateToFocused() {
		if (focusedIndex >= 0 && focusedIndex < filteredItems.length) {
			scrollToSection(filteredItems[focusedIndex].id);
		}
	}

	// keyboard navigation for search input
	function handleSearchKeydown(event: KeyboardEvent) {
		switch (event.key) {
			case 'Escape':
				event.preventDefault();
				if (searchQuery) {
					clearSearch();
				} else {
					isCollapsed = true;
				}
				break;

			case 'ArrowDown':
				event.preventDefault();
				if (filteredItems.length > 0) {
					if (focusedIndex < 0) {
						focusItem(0);
					} else {
						focusItem(Math.min(focusedIndex + 1, filteredItems.length - 1));
					}
				}
				break;

			case 'ArrowUp':
				event.preventDefault();
				if (filteredItems.length > 0 && focusedIndex > 0) {
					focusItem(focusedIndex - 1);
				} else if (focusedIndex === 0) {
					focusedIndex = -1;
					searchInput?.focus();
				}
				break;

			case 'Enter':
				event.preventDefault();
				if (focusedIndex >= 0) {
					navigateToFocused();
				} else if (filteredItems.length > 0) {
					scrollToSection(filteredItems[0].id);
				}
				break;

			case 'Home':
				event.preventDefault();
				if (filteredItems.length > 0) {
					focusItem(0);
				}
				break;

			case 'End':
				event.preventDefault();
				if (filteredItems.length > 0) {
					focusItem(filteredItems.length - 1);
				}
				break;
		}
	}

	// Keyboard navigation for TOC buttons
	function handleButtonKeydown(event: KeyboardEvent, index: number) {
		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				if (index < filteredItems.length - 1) {
					focusItem(index + 1);
				}
				break;

			case 'ArrowUp':
				event.preventDefault();
				if (index > 0) {
					focusItem(index - 1);
				} else {
					focusedIndex = -1;
					searchInput?.focus();
				}
				break;

			case 'Home':
				event.preventDefault();
				focusItem(0);
				break;

			case 'End':
				event.preventDefault();
				focusItem(filteredItems.length - 1);
				break;

			case 'Escape':
				event.preventDefault();
				isCollapsed = true;
				break;

			case 'Enter':
			case ' ':
				event.preventDefault();
				scrollToSection(filteredItems[index].id);
				break;
		}
	}

	function handleButtonFocus(index: number) {
		focusedIndex = index;
	}

	function handleButtonClick(id: string, index: number) {
		focusedIndex = index;
		scrollToSection(id);
	}

	function highlightSegments(title: string, query: string): { text: string; match: boolean }[] {
		if (!query) return [{ text: title, match: false }];
		const lowerTitle = title.toLowerCase();
		const lowerQuery = query.toLowerCase();
		const segments: { text: string; match: boolean }[] = [];
		let start = 0;
		let idx = lowerTitle.indexOf(lowerQuery, start);
		while (idx !== -1) {
			if (idx > start) segments.push({ text: title.slice(start, idx), match: false });
			segments.push({ text: title.slice(idx, idx + query.length), match: true });
			start = idx + query.length;
			idx = lowerTitle.indexOf(lowerQuery, start);
		}
		if (start < title.length) segments.push({ text: title.slice(start), match: false });
		return segments;
	}
</script>

{#if isVisible && items.length > 0}
	<div
		bind:this={tocContainer}
		class="toc-container fixed z-40 {position === 'right' ? 'right-4' : 'left-4'}
               top-1/2 transform -translate-y-1/2 max-h-[100vh] {className}"
	>
		<button
			onclick={toggleCollapse}
			class="toc-toggle mb-2 p-2 bg-surface-200 hover:bg-surface-300 rounded-full shadow-lg transition-all duration-200 relative z-50 cursor-pointer {isCollapsed
				? ''
				: 'hidden'}"
			title={m.showTableOfContents()}
			aria-label={m.showTableOfContents()}
			style="pointer-events: auto;"
		>
			<i class="fa-solid fa-list text-sm" aria-hidden="true"></i>
		</button>

		<!-- TOC Content -->
		{#if !isCollapsed}
			<div
				class="toc-content bg-surface-50 border border-surface-300 rounded-lg shadow-lg p-4 w-64 max-h-[60vh] overflow-hidden flex flex-col relative"
			>
				<button
					onclick={toggleCollapse}
					class="absolute top-2 right-2 p-1 text-surface-400 hover:text-surface-600 hover:bg-surface-200 rounded transition-colors duration-150"
					title={m.hideTableOfContents()}
					aria-label={m.hideTableOfContents()}
				>
					<i class="fa-solid fa-times text-sm" aria-hidden="true"></i>
				</button>

				<h3 class="text-sm font-semibold text-surface-700 mb-3 flex items-center pr-8">
					<i class="fa-solid fa-list-ul mr-2" aria-hidden="true"></i>
					{m.tableOfContents()}
				</h3>

				<!-- Search Field -->
				<div class="relative mb-3">
					<div class="relative">
						<input
							bind:this={searchInput}
							bind:value={searchQuery}
							onkeydown={handleSearchKeydown}
							type="text"
							placeholder={m.searchSections()}
							aria-label={m.searchSections()}
							class="w-full px-3 py-2 pr-8 text-sm border border-surface-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
						/>
						<div class="absolute inset-y-0 right-0 flex items-center pr-3">
							{#if searchQuery}
								<button
									onclick={clearSearch}
									class="text-surface-400 hover:text-surface-600 transition-colors"
									title={m.clearSearch()}
									aria-label={m.clearSearch()}
									tabindex="-1"
								>
									<i class="fa-solid fa-times text-xs" aria-hidden="true"></i>
								</button>
							{:else}
								<i class="fa-solid fa-search text-surface-400 text-xs" aria-hidden="true"></i>
							{/if}
						</div>
					</div>

					<!-- Keyboard hints -->
					<div class="mt-1 text-xs text-surface-400">
						<kbd class="px-1 py-0.5 bg-surface-200 rounded text-xs">↑↓</kbd> navigate
						<kbd class="px-1 py-0.5 bg-surface-200 rounded text-xs ml-1">Enter</kbd> go
						<kbd class="px-1 py-0.5 bg-surface-200 rounded text-xs ml-1">Esc</kbd> close
					</div>
				</div>

				<!-- Navigation -->
				<nav
					class="toc-nav flex-1 overflow-y-auto"
					role="navigation"
					aria-label={m.tableOfContents()}
				>
					{#if filteredItems.length > 0}
						<ul class="space-y-1 text-sm" role="list">
							{#each filteredItems as item, index}
								<li role="listitem">
									<button
										bind:this={navigationButtons[index]}
										onclick={() => handleButtonClick(item.id, index)}
										onkeydown={(e) => handleButtonKeydown(e, index)}
										onfocus={() => handleButtonFocus(index)}
										class="toc-link w-full text-left px-2 py-1 rounded transition-colors duration-150
                                               {activeId === item.id
											? 'bg-primary-100 text-primary-700 font-medium border-l-2 border-primary-500'
											: 'text-surface-600 hover:bg-surface-100 hover:text-surface-800'}
                                               {focusedIndex === index
											? 'ring-2 ring-primary-300'
											: ''}"
										style="padding-left: {item.level * 8 + 8}px"
										aria-label={`Jump to section: ${item.title}`}
										aria-current={activeId === item.id ? 'location' : false}
										tabindex={focusedIndex === index ? 0 : -1}
									>
										<span class="truncate block" title={item.title}>
											{#if searchQuery}
												{#each highlightSegments(item.title, searchQuery) as seg}
													{#if seg.match}
														<mark class="bg-yellow-200 px-1 rounded">{seg.text}</mark>
													{:else}
														{seg.text}
													{/if}
												{/each}
											{:else}
												{item.title}
											{/if}
										</span>
									</button>
								</li>
							{/each}
						</ul>
					{:else if searchQuery}
						<div class="text-center py-4 text-surface-500 text-sm" role="status" aria-live="polite">
							<i class="fa-solid fa-search mb-2 text-lg" aria-hidden="true"></i>
							<p>{m.noResultsFound()}</p>
							<button
								onclick={clearSearch}
								class="mt-2 text-primary-600 hover:text-primary-800 underline text-xs"
								aria-label={m.clearSearch()}
							>
								{m.clearSearch()}
							</button>
						</div>
					{/if}
				</nav>

				<!-- Footer -->
				{#if searchQuery && filteredItems.length > 0}
					<div
						class="mt-2 pt-2 border-t border-surface-200 text-xs text-surface-500 text-center"
						role="status"
						aria-live="polite"
					>
						{filteredItems.length} of {items.length} sections
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}

<style>
	.toc-container {
		max-width: 16rem;
		pointer-events: auto;
	}

	.toc-toggle {
		background-color: oklch(70.2% 0.183 293.541);
		color: white;
		pointer-events: auto;
		cursor: pointer;
	}

	.toc-content {
		backdrop-filter: blur(8px);
		background-color: rgba(255, 255, 255, 0.95);
	}

	.toc-link {
		word-break: break-word;
		line-height: 1.3;
	}

	:global(.toc-link mark) {
		background-color: #fef08a;
		color: inherit;
		padding: 0 2px;
		border-radius: 2px;
	}
	kbd {
		font-family:
			ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
		font-size: 0.75rem;
	}
	@media (max-width: 768px) {
		.toc-container {
			display: none;
		}
	}

	.toc-nav::-webkit-scrollbar {
		width: 4px;
	}

	.toc-nav::-webkit-scrollbar-track {
		background: #f1f5f9;
		border-radius: 2px;
	}

	.toc-nav::-webkit-scrollbar-thumb {
		background: #cbd5e1;
		border-radius: 2px;
	}

	.toc-nav::-webkit-scrollbar-thumb:hover {
		background: #94a3b8;
	}
</style>
