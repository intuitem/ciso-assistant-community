# PPTX Generation Engine - Implementation Status

## Current State (as of 2026-01-13)

### Completed

The core PPTX template engine is **fully implemented** and tested:

| File | Lines | Purpose |
|------|-------|---------|
| `engine.py` | 335 | Main orchestrator - extract, process, repackage |
| `normalizer.py` | 224 | Handles PowerPoint text fragmentation |
| `replacers/text.py` | 159 | `{{variable}}` placeholder replacement |
| `replacers/image.py` | 411 | `{{image:var}}` image insertion |
| `replacers/loops.py` | 605 | Table row loops and slide duplication |
| `utils.py` | 211 | XML/context utilities |
| `constants.py` | 60 | Namespaces, patterns, content types |
| `exceptions.py` | 72 | Custom exception hierarchy |
| `DESIGN.md` | 366 | Architecture documentation |
| **Tests** | 799 | Comprehensive test coverage |

### Key Design Decisions

1. **XML-based approach**: Uses lxml for raw XML manipulation instead of python-pptx
   - Enables fine-grained control for complex operations (slide duplication, relationship management)
   - No additional dependencies beyond lxml

2. **Text normalization**: Pre-normalizes XML runs before replacement
   - Solves PowerPoint's text fragmentation problem (placeholders split across runs)

3. **Image handling**: Images are copied to `ppt/media/`, relationships managed in `.rels` files

### Placeholder Syntax

```
{{variable}}              - Text replacement (supports dot notation: {{user.name}})
{{image:variable}}        - Image insertion (inherits text box dimensions)
{{#each collection}}...{{/each}}  - Table row iteration
{{#slide collection}}...{{/slide}} - Slide duplication
```

## Remaining Work

### Backend Integration ✅ Complete

- [x] **`pptx_report()` view method** in `ComplianceAssessmentViewSet` (`views.py`)
  - Follow pattern from `word_report()` method
  - Load language-specific template
  - Build context and call engine
  - Return StreamingHttpResponse with PPTX

- [x] **`gen_audit_pptx_context()` function** in `generators.py`
  - Adapt from `gen_audit_context()`
  - Generate chart images to temp files (for `{{image:var}}` syntax)
  - Build context dict with audit data

- [x] **Image aspect ratio preservation** in `replacers/image.py`
  - Added `_get_image_dimensions()` to read image dimensions
  - Added `_fit_image_to_bounds()` to preserve aspect ratio while centering

- [x] **Improved donut chart rendering** in `generators.py`
  - Filter out zero values to avoid clutter
  - Show percentages only for slices >= 5%
  - Legend placed outside chart for readability

### Frontend Integration ✅ Complete

- [x] Create `/compliance-assessments/[id=uuid]/export/pptx/+server.ts`
  - Follow pattern from `/export/word/+server.ts`
  - Call `/api/compliance-assessments/{id}/pptx_report/`

- [x] Add PPTX export option to UI
  - Add to export dropdown/menu in compliance assessment pages
  - Added `asPowerPoint` translation to en.json and fr.json

### Template Design (User Task)

- [ ] **Template placeholders** - Create/update `audit_report_template_en.pptx`
  - User is designing the template with supported placeholders
  - Create French template if needed

### Bug Fixes Applied

- [x] Fixed re-parsing bug in `engine.py` that discarded image/loop changes
- [x] Fixed table row insertion position bug in `loops.py` (was using row index instead of child element index)
- [x] Fixed `None` value handling with `NOT_FOUND` sentinel pattern
- [x] Removed debug print statements from `loops.py`

### Testing

- [ ] Integration test with real compliance assessment data
- [ ] End-to-end test of full export workflow
- [ ] Test with various assessment sizes

## Architecture Reference

```
Frontend Request
└─> GET /api/compliance-assessments/{id}/pptx_report/
    └─> ComplianceAssessmentViewSet.pptx_report()
        ├─ Load template (audit_report_template_{lang}.pptx)
        ├─ Build requirement tree
        ├─ gen_audit_pptx_context()
        │   ├─ Compute statistics
        │   ├─ Generate charts to temp files
        │   └─ Return context dict
        └─> PPTXTemplateEngine.process_to_bytes()
            ├─ Extract PPTX to temp dir
            ├─ Process slides (normalize, replace, loops)
            └─> Return PPTX bytes
```

## Files to Modify

| File | Changes Needed |
|------|----------------|
| `backend/core/views.py` | Add `pptx_report()` action method |
| `backend/core/generators.py` | Add `gen_audit_pptx_context()` function |
| `backend/core/templates/core/audit_report_template_en.pptx` | Verify placeholders |
| `frontend/src/routes/(app)/(internal)/compliance-assessments/[id=uuid]/export/pptx/+server.ts` | Create endpoint |
