/**
 * OSCAL Editor Component
 *
 * A zone-based OSCAL document editor inspired by OSCAL-GUI patterns.
 *
 * Features:
 * - Zone-based editing (metadata, controls, parameters, back-matter)
 * - Parameter view switching (Blank/Catalog/Profile/Assigned)
 * - Rich text editing for prose content
 * - Real-time validation
 * - Format conversion (JSON/YAML)
 * - Auto-save functionality
 *
 * Usage:
 * ```svelte
 * <script>
 *   import OscalEditor from '$lib/components/OscalEditor';
 *
 *   let document = {
 *     type: 'catalog',
 *     content: catalogJson,
 *     metadata: { title: 'My Catalog', ... }
 *   };
 * </script>
 *
 * <OscalEditor
 *   bind:document
 *   onchange={(doc) => console.log('Changed', doc)}
 *   onsave={(doc) => saveToServer(doc)}
 *   onvalidate={(errors) => console.log('Validation', errors)}
 * />
 * ```
 */

export { default } from './OscalEditor.svelte';
export { default as OscalEditor } from './OscalEditor.svelte';
