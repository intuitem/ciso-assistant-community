# PPTX Template Engine - Design Document

## Overview

A PowerPoint template engine that allows users to upload PPTX templates with placeholder
markup and generate customized presentations by filling in data.

## PPTX File Structure

```
template.pptx (ZIP archive)
├── [Content_Types].xml          # MIME types for all parts
├── _rels/.rels                  # Root relationships
├── docProps/
│   ├── app.xml                  # App metadata
│   └── core.xml                 # Document properties
└── ppt/
    ├── presentation.xml         # Slide order, sizes
    ├── _rels/presentation.xml.rels
    ├── slides/
    │   ├── slide1.xml
    │   ├── _rels/slide1.xml.rels
    │   └── ...
    ├── slideLayouts/
    ├── slideMasters/
    ├── media/                   # Images, embedded files
    └── theme/
```

## Placeholder Syntax

### Text Placeholders
```
{{variable_name}}
```
Replaced with string values. Supports nested access: `{{user.name}}`

### Image Placeholders
```
{{image:variable_name}}
```
The placeholder text is replaced with an image. The image inherits the text box dimensions.

### Table Row Loops
```
{{#each items}}
| {{name}} | {{value}} | {{status}} |
{{/each}}
```
The row containing `{{#each}}` is duplicated for each item in the collection.

### Slide Loops
```
{{#slide findings}}
... entire slide content with {{title}}, {{description}}, etc. ...
{{/slide}}
```
The entire slide is duplicated for each item in the collection.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PPTXTemplateEngine                              │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                        process(template, context)             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│         │                                                            │
│         ▼                                                            │
│  ┌─────────────┐                                                    │
│  │   Unpacker  │  Extract ZIP to temp directory                     │
│  └─────────────┘                                                    │
│         │                                                            │
│         ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    SlideProcessor                            │    │
│  │  For each slide:                                             │    │
│  │    1. Check for {{#slide}} → duplicate slide if needed       │    │
│  │    2. Normalize XML text runs                                │    │
│  │    3. Process {{#each}} table loops                          │    │
│  │    4. Replace {{image:*}} placeholders                       │    │
│  │    5. Replace {{text}} placeholders                          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│         │                                                            │
│         ▼                                                            │
│  ┌─────────────┐                                                    │
│  │  Repacker   │  Repackage to new PPTX                             │
│  └─────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

## XML Text Normalization

### The Problem

PowerPoint splits text across multiple runs unpredictably:

```xml
<a:p>
  <a:r><a:t>Hello {{</a:t></a:r>
  <a:r><a:rPr b="1"/><a:t>user</a:t></a:r>
  <a:r><a:t>}}, welcome!</a:t></a:r>
</a:p>
```

### Solution: Pre-normalize

1. Parse the paragraph
2. Concatenate all text: `"Hello {{user}}, welcome!"`
3. Find placeholder positions: `{{user}}` at index 6-14
4. Determine which runs contain the placeholder
5. Merge those runs, preserving first run's formatting
6. Replace the placeholder text

```python
class TextNormalizer:
    def normalize_paragraph(self, p_element):
        """
        Merge text runs that contain split placeholders.
        Preserves formatting from the first run of each merged group.
        """
        runs = p_element.findall('.//a:r', NAMESPACES)
        full_text = ''.join(r.find('a:t', NAMESPACES).text or '' for r in runs)

        # Find all placeholders
        placeholders = re.finditer(r'\{\{[^}]+\}\}', full_text)

        for match in placeholders:
            # Find runs that span this placeholder
            start_run, end_run = self._find_spanning_runs(runs, match.start(), match.end())
            # Merge runs between start_run and end_run
            self._merge_runs(p_element, start_run, end_run)
```

## Image Replacement

### Process

1. Find `{{image:variable_name}}` in text
2. Get the shape (sp element) containing this text
3. Extract shape position and dimensions (xfrm)
4. Add image to `ppt/media/` directory
5. Create relationship in slide's `.rels` file
6. Update `[Content_Types].xml` if needed
7. Replace the `<p:sp>` with `<p:pic>` element

### XML Structure for Images

```xml
<p:pic>
  <p:nvPicPr>
    <p:cNvPr id="4" name="Picture 3"/>
    <p:cNvPicPr/>
    <p:nvPr/>
  </p:nvPicPr>
  <p:blipFill>
    <a:blip r:embed="rId2"/>  <!-- relationship ID -->
    <a:stretch><a:fillRect/></a:stretch>
  </p:blipFill>
  <p:spPr>
    <a:xfrm>
      <a:off x="1234" y="5678"/>
      <a:ext cx="9999" cy="8888"/>
    </a:xfrm>
    <a:prstGeom prst="rect"/>
  </p:spPr>
</p:pic>
```

## Loop Handling

### Table Row Loops

1. Find row containing `{{#each collection}}`
2. Find closing `{{/each}}`
3. Extract the template row
4. For each item in collection:
   - Clone the template row
   - Replace placeholders with item values
   - Insert row into table
5. Remove original template row

### Slide Loops

1. Find slide containing `{{#slide collection}}`
2. For each item in collection:
   - Copy slide XML file
   - Copy slide relationships
   - Update presentation.xml slide list
   - Replace placeholders with item values
3. Remove original template slide

## Relationship Management

Each slide has a `.rels` file mapping relationship IDs to resources:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type=".../slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type=".../image" Target="../media/image1.png"/>
</Relationships>
```

### Adding Images

```python
class RelationshipManager:
    def add_image(self, slide_rels_path, image_path):
        """Add image relationship and return the rId."""
        tree = ET.parse(slide_rels_path)
        root = tree.getroot()

        # Find next available rId
        existing_ids = [r.get('Id') for r in root.findall('Relationship')]
        next_id = f"rId{max(int(id[3:]) for id in existing_ids) + 1}"

        # Add relationship
        ET.SubElement(root, 'Relationship', {
            'Id': next_id,
            'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image',
            'Target': f'../media/{os.path.basename(image_path)}'
        })

        tree.write(slide_rels_path, xml_declaration=True, encoding='UTF-8')
        return next_id
```

## Content Types

`[Content_Types].xml` must include entries for all file types:

```xml
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="jpeg" ContentType="image/jpeg"/>
  <Default Extension="jpg" ContentType="image/jpeg"/>
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <!-- ... -->
</Types>
```

## Error Handling

```python
class PPTXTemplateError(Exception):
    """Base exception for template errors."""
    pass

class InvalidTemplateError(PPTXTemplateError):
    """Template file is not a valid PPTX."""
    pass

class PlaceholderError(PPTXTemplateError):
    """Error in placeholder syntax or unmatched placeholder."""
    pass

class MissingContextError(PPTXTemplateError):
    """Required context variable not provided."""
    pass

class ImageError(PPTXTemplateError):
    """Error processing image placeholder."""
    pass
```

## Usage Example

```python
from core.pptx_engine import PPTXTemplateEngine

engine = PPTXTemplateEngine()

context = {
    'company_name': 'Acme Corp',
    'date': '2024-01-15',
    'logo': '/path/to/logo.png',  # For {{image:logo}}
    'findings': [  # For {{#slide findings}} or {{#each findings}}
        {'title': 'SQL Injection', 'severity': 'High', 'description': '...'},
        {'title': 'XSS Vulnerability', 'severity': 'Medium', 'description': '...'},
    ],
    'summary_table': [  # For {{#each summary_table}}
        {'control': 'AC-1', 'status': 'Compliant', 'score': 95},
        {'control': 'AC-2', 'status': 'Partial', 'score': 67},
    ],
}

output_path = engine.process(
    template_path='/path/to/template.pptx',
    context=context,
    output_path='/path/to/output.pptx'  # Optional, generates temp file if not provided
)
```

## Django Integration

### Model

```python
class PPTXTemplate(AbstractBaseModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template_file = models.FileField(upload_to='pptx_templates/')
    template_type = models.CharField(
        max_length=50,
        choices=[
            ('risk_assessment', 'Risk Assessment Report'),
            ('compliance_report', 'Compliance Report'),
            ('audit_report', 'Audit Report'),
            ('executive_summary', 'Executive Summary'),
        ]
    )
    # Metadata about available placeholders (auto-extracted or manual)
    placeholders = models.JSONField(default=list)

    class Meta:
        verbose_name = 'PPTX Template'
```

### View

```python
class PPTXExportView(APIView):
    def post(self, request, pk):
        template = get_object_or_404(PPTXTemplate, pk=pk)

        # Build context based on template_type
        context = self.build_context(template.template_type, request.data)

        engine = PPTXTemplateEngine()
        output_file = engine.process(
            template_path=template.template_file.path,
            context=context
        )

        response = FileResponse(
            open(output_file, 'rb'),
            content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
        response['Content-Disposition'] = f'attachment; filename="{template.name}_{date.today()}.pptx"'
        return response
```

## Security Considerations

1. **File Validation**: Verify uploaded templates are valid PPTX files
2. **Path Traversal**: Sanitize all paths when extracting/creating ZIP entries
3. **Size Limits**: Enforce maximum template and output file sizes
4. **Content Scanning**: Optional virus/malware scanning of uploaded templates
5. **Placeholder Injection**: Validate context values don't contain malicious content

## Performance Considerations

1. **Streaming**: For large presentations, process slides individually
2. **Caching**: Cache parsed template structure for repeated use
3. **Temp Files**: Clean up temporary extraction directories
4. **Memory**: Use iterative XML parsing for large slides

## Testing Strategy

1. **Unit Tests**: Each component (normalizer, replacers) tested independently
2. **Integration Tests**: Full template processing with various placeholder combinations
3. **Edge Cases**: Empty collections, missing variables, malformed placeholders
4. **Regression Tests**: Known PowerPoint versions and their XML quirks
