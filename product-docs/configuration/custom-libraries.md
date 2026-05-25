# Designing your own Libraries

{% hint style="warning" %}
**NOTE:** This section is still under reworking. For complementary informations, please refer to the [**dedicated README on GitHub**](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/README.md).
{% endhint %}

This documentation explains how to create, maintain and evolve **custom libraries** for CISO Assistant using **Excel**, **YAML**, and the official **tools provided in the community repository**.

***

## 1. What is a Library in CISO Assistant?

A **library** is a container that bundles one or more governance objects that can be imported into CISO Assistant.

A single library may contain:

* **Framework**
* **Threats**
* **Reference controls**
* **Risk matrices**
* **Answer sets**
* **Score definitions**
* **Implementation groups**
* **Mappings between frameworks**

{% hint style="info" %}
In practice, **Risk matrices** and **Mappings between frameworks** have their own library for practical reasons.
{% endhint %}

Libraries are versioned, portable, and reusable across projects.

In practice:

* **Excel (.xlsx)** is the authoring format
* **YAML (.yaml)** is the import/export format
* **Python tools** are used to convert and validate data

***

## 2. Key Concepts

Before creating your first library, it is important to understand a few core concepts.

### 2.1 Frameworks and Requirements

A **framework** is a hierarchical structure representing a standard, regulation, or internal control model.

A framework is composed of:

* Organizational nodes (categories, sections, subsections, information, ...)
* **Requirements**, which are the assessable elements

Only **requirements** can be assessed during audits.

<figure><img src="../.gitbook/assets/Framework Structure.png" alt=""><figcaption><p>Hierarchy example of a framework</p></figcaption></figure>

### 2.2 Assessable vs Non-assessable Nodes

In a framework:

* Categories and sections are **structural**
* Requirements are **assessable**

This distinction is explicit in Excel via the `assessable` column.

### 2.3 Hierarchy and Depth

Frameworks are hierarchical by nature.

* Each row in Excel has a `depth`
* Depth starts at `1`
* Deeper levels represent nested structures

CISO Assistant supports deep hierarchies, but **depths above 6 are strongly discouraged** for readability.

### 2.4 URNs and ref\_id

Each object is uniquely identified by a **URN**.

* `ref_id` is the human-defined identifier
* URNs are generated using `urn_prefix` + `ref_id`
* URNs must remain stable across versions

{% hint style="warning" %}
Changing URNs breaks mappings and historical data.
{% endhint %}

### 2.5 Implementation Groups (IG)

Implementation Groups allow you to:

* Scope requirements
* Build subsets of a framework
* Adapt questionnaires to context or maturity level

They are optional but highly recommended for complex frameworks.

### 2.6 Scores and Answers

Frameworks can define:

* Scoring models
* Answer sets
* Conditional questions
* Weighted scoring

These elements allow frameworks to behave as **questionnaires**, not just checklists.

### 2.7 Mappings

Mappings describe relationships between requirements from different frameworks.

They are used to:

* Translate compliance
* Compare standards
* Build equivalency views

Mappings are directional and typed (equal, subset, superset, intersect).

***

## 3. Recommended Workflow

Here is the recommended procedure for creating and maintaining custom libraries:

{% stepper %}
{% step %}
### Define the framework structure or use an existing one

Plan the structure and decide whether to start from scratch or reuse an existing framework.
{% endstep %}

{% step %}
### Generate a base Excel file (v2 format)

Use the provided tooling to create a valid v2 Excel skeleton.
{% endstep %}

{% step %}
### Fill in framework content

Populate the `_content` tabs with requirements.
{% endstep %}

{% step %}
### Convert Excel to YAML

Use the conversion tool to generate a CISO Assistant-compatible YAML library.
{% endstep %}

{% step %}
### Import the library into CISO Assistant

Upload and validate the generated YAML in CISO Assistant.
{% endstep %}

{% step %}
### Maintain and update the library

Follow versioning and URN stability rules when updating.
{% endstep %}
{% endstepper %}

***

## 4. Creating a Framework using Excel (v2 format)

{% hint style="warning" %}
This section doesn't explain all the object types yet, neither the type of values to put in the columns. In the meantime, you can refer to the [dedicated README on GitHub](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/README.md) for more up-to-date information.
{% endhint %}

### 4.1 Why Excel?

Excel is the recommended authoring format because:

* It is accessible to non-developers
* It enforces structure
* It reduces YAML syntax errors
* It supports collaboration and review

Excel files are converted to YAML only at the final step.

### 4.2 Excel file structure (v2)

Excel files follow strict conventions.

Tabs are divided into:

* `_meta` tabs → configuration and metadata
* `_content` tabs → actual objects and data

Each object type has:

* One `_meta` tab
* One `_content` tab (except `library_meta`)

### 4.3 Example Framework (Strongly Recommended)

Before creating or editing your own framework, we strongly recommend reviewing the provided example file [`example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx).

This file is a **reference implementation** of the Excel v2 format and is designed to help users understand how a valid framework is structured.

#### Why this example matters

The Excel v2 format is powerful but can be confusing at first.\
The example framework helps you understand:

* How `_meta` and `_content` tabs are organized
* How hierarchy is expressed using `depth` and row order
* The difference between structural nodes and assessable requirements
* How advanced fields (implementation groups, questions, answers, scoring) are represented
* How real-world frameworks should be laid out in Excel

The file is intentionally:

* **Color-coded** to highlight structure
* **Annotated with cell notes** (look for the small triangle in the top-right corner of cells)

#### Recommended way to use the example

{% stepper %}
{% step %}
Open `example_framework.xlsx` in Excel or LibreOffice and explore the tabs and cell notes.
{% endstep %}

{% step %}
If you would like to see what this example looks like directly in CISO Assistant, convert it using the standard conversion tool:

{% code title="Convert the example" %}
```shell
python convert_library_v2.py example_framework.xlsx
```
{% endcode %}
{% endstep %}
{% endstepper %}

#### When to come back to the example framework

Use the example file whenever you:

* Start a new framework from scratch
* Are unsure about the meaning of a column
* Encounter validation errors during conversion
* Want to check whether your Excel file follows best practices

{% hint style="info" %}
Before opening a support ticket related to framework creation, consulting the example framework may sometimes solve your problem.
{% endhint %}

### 4.4 The `library_meta` Tab

This tab defines the library itself.

Mandatory fields include:

* `type`
* `urn`
* `version`
* `locale`
* `ref_id`
* `name`
* `description`
* `copyright`
* `provider`
* `packager`

{% hint style="warning" %}
Versioning is critical. If the custom framework is already imported into CISO Assistant and the version number has not been incremented, CISO Assistant will not suggest an update.
{% endhint %}

### 4.5 Framework definition Tabs

A framework is defined using:

* One `_meta` tab of type `framework`
* One `_content` tab listing all nodes

The `_content` tab is ordered top-to-bottom and defines the hierarchy.

Important columns:

* `assessable`
* `depth`
* `ref_id`
* `name`
* `description`
* `implementation_groups` (if applicable)
* `questions` / `answers` (if applicable)

{% hint style="info" %}
Order matters: the hierarchy is inferred from row order + depth.
{% endhint %}

### 4.6 Threats

Threats represent events or situations that may negatively impact an organization.

Typical examples include:

* Data breach
* Ransomware attack
* Insider threat
* Loss of availability

Threats are designed to be **reusable** across multiple frameworks and libraries.

#### **Structure**

Threats are defined using:

* One `_meta` tab of type `threats`
* One `_content` tab listing individual threats

Each threat includes:

* A `ref_id`
* A name
* A description (optional)
* Annotations (optional)

Threats are usually referenced from framework requirements using their URN.

{% hint style="info" %}
A library may contain **only threats**, without any framework. This is a common pattern when building shared threat catalogs reused across multiple frameworks.
{% endhint %}

***

### 4.7 Reference Controls

Reference controls describe **controls or safeguards** that can mitigate threats or help fulfill requirements.

They are typically used to:

* Document expected controls
* Link requirements to best practices
* Support evidence collection and audits

Examples:

* Access control policy
* Backup procedures
* Network segmentation
* Incident response process

#### **Structure**

Reference controls are defined using:

* One `_meta` tab of type `reference_controls`
* One `_content` tab listing individual controls

Each control include:

* A `ref_id`
* A name
* A description (optional)
* A category (policy, process, technical, physical, procedure) (optional)
* An CSF function mapping (optional)
* Annotations (optional)

{% hint style="info" %}
Reference controls can be defined **independently** of any framework and packaged in their own library, exactly like threats.
{% endhint %}

### 4.8 Risk Matrices

Risk matrices are used to model **risk evaluation logic**, typically combining probability and impact into a resulting risk level.

They define **how risk is calculated**, not how compliance is assessed.

#### **Typical usage**

Risk matrices are usually:

* Independent from frameworks
* Shared across multiple projects
* Maintained separately from compliance libraries

For this reason, they are most often packaged **alone in their own library**, without any framework.

#### **Structure**

A risk matrix is defined using:

* One `_meta` tab of type `risk_matrix`
* One `_content` tab describing:
  * Probability levels
  * Impact levels
  * Risk levels
  * The risk grid mapping probability × impact to risk

The grid defines the logical relationship between values.\
The visual rendering (orientation, colors, layout) is handled by the CISO Assistant interface.

#### **Important Note: Use Existing Examples**

Risk matrices are **not trivial to design correctly**, especially the grid logic.

For this reason, we strongly recommend starting from one of the existing examples available in [`tools/excel/matrix`](https://github.com/intuitem/ciso-assistant-community/tree/main/tools/excel/matrix).

These examples:

* Are already valid and tested
* Follow best practices
* Can be adapted to your own risk model

Risk matrices can be converted and imported using the same tools as other library objects.

***

## 5. Using the Tools

All tools described below are located in the [`/tools`](https://github.com/intuitem/ciso-assistant-community/tree/main/tools) directory of the community repository.

These tools are designed to:

* Reduce human errors
* Enforce the CISO Assistant data model
* Make libraries easier to maintain over time

You do **not** need to use all tools in every project. Each tool addresses a **specific user intent**, described below.

### Prerequisites

Before using any of the conversion or preparation tools, make sure your environment is correctly set up.

You will need:

* **Python 3.12 or higher and pip (included with Python)**
* A local copy of the community repository

In the `/tools` directory, run the following commands:

{% code title="Install Python requirements" %}
```shell
pip install -r requirements.txt
```
{% endcode %}

This installs all required Python dependencies needed to run the tools.

{% hint style="info" %}
This setup only needs to be done once.
{% endhint %}

***

### 5.1 Creating a Framework Skeleton (Recommended Starting Point)

**Tool:** [`prepare_framework_v2.py`](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/prepare_framework_v2.py)

This tool helps you create a **clean and valid Excel file** that already follows the v2 format rules.

#### Typical use cases

* Creating a framework from scratch
* Avoiding mistakes in `_meta` and `_content` tabs
* Standardizing framework creation across teams
* Speeding up initial setup

#### What this tool does

* Generates a fully structured Excel file
* Creates required `_meta` and `_content` tabs
* Adds metadata and columns directly inside Excel cells
* Prevents common structural errors

#### Recommended usage (simple)

{% code title="Generate skeleton" %}
```shell
python3 prepare_framework_v2.py
```
{% endcode %}

By default, the tool uses a configuration file named `prepare_framework_v2_config.xlsx`, which:

* Is self-documented
* Can be edited directly
* Avoids complex command-line arguments

#### Advanced usage

You may also use a YAML configuration file:

{% code title="YAML-driven configuration" %}
```shell
python3 prepare_framework_v2.py -i prepare_framework_v2_config.yaml
```
{% endcode %}

This is intended for advanced users who prefer YAML-driven configuration.

{% hint style="info" %}
After running this tool, the `library_meta` tab and the framework `_meta` tab usually do **not** need to be modified again, except if you want to:

* Add translations
* Add advanced objects (scores, answers, IGs)
{% endhint %}

***

### 5.2 Converting an Excel file to a Library (Main conversion step)

**Tool:** [`convert_library_v2.py`](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/convert_library_v2.py)

This is the **most frequently used tool**.

It converts one or more Excel files into **CISO Assistant-compatible YAML libraries**.

#### Typical use cases

* Generating a YAML file from an Excel framework
* Validating Excel consistency
* Importing libraries into CISO Assistant
* Updating an existing framework

#### Basic usage (recommended for most users)

{% code title="Convert a framework" %}
```shell
python3 convert_library_v2.py my_framework.xlsx
```
{% endcode %}

This will:

* Validate the Excel file
* Generate `my_framework.yaml`
* Report clear errors if something is wrong

In most situations, **this command is sufficient**.

#### Verbose mode (recommended during troubleshooting)

{% code title="Verbose mode" %}
```shell
python3 convert_library_v2.py my_framework.xlsx --verbose
```
{% endcode %}

Verbose mode:

* Explains what the tool is doing
* Helps understand validation errors
* Is very useful during early framework design

#### Bulk mode (multiple frameworks)

{% code title="Bulk conversion" %}
```shell
python3 convert_library_v2.py path/to/folder --bulk
```
{% endcode %}

This will:

* Convert all `.xlsx` files in the folder
* Generate one YAML file per Excel file

Optional output directory:

{% code title="Bulk conversion with output dir" %}
```shell
python3 convert_library_v2.py path/to/folder --bulk --output-dir out_folder
```
{% endcode %}

#### Compatibility modes (advanced users)

Compatibility modes exist **only for legacy or special cases**.

{% hint style="info" %}
If you are unsure, **do not** use compatibility modes.
{% endhint %}

* `--compat 0` (default):\
  Recommended for all new libraries
* `--compat 1`:\
  Used only to maintain libraries created **before v1.9.20**
* `--compat 2`:\
  Prevents URN cleaning (advanced / niche use cases)

***

### 5.3 Migrating Legacy Frameworks (v1 → v2)

**Tool:** [`convert_v1_to_v2.py`](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/convert_v1_to_v2.py)

This tool helps migrate **old v1 frameworks** to the **v2** format, as the **v1** Excel format is **deprecated**.

#### Typical use cases

* Updating legacy frameworks
* Preserving historical identifiers
* Preparing old content for long-term maintenance

#### Usage

{% code title="Migrate v1 to v2" %}
```shell
python3 convert_v1_to_v2.py old_framework.xlsx
```
{% endcode %}

This produces a new v2-compatible file.

{% hint style="danger" %}
If you use `convert_library_v2.py` on an Excel file converted into v2, the YAML structure may be completely different from your original YAML file and break your audits if you import it into CISO Assistant!

You can use the `convert_v1_to_v2.py` script if you created your framework using the v1 format and provided that you **HAVE NOT YET** imported your framework into CISO Assistant.

You can also use it if you notice that the URNs in the YAML file created with the v2 version of your framework are identical to the URNs in the YAML file of the v1 version of your framework. You can also try using the script's compatibility modes to recover the old structure.
{% endhint %}

{% hint style="warning" %}
The result must be reviewed manually. Migration fixes Excel structure, not design quality. In some cases, you should still simplify and clean legacy content afterward.
{% endhint %}

***

## 6. Creating Mappings between Frameworks

Mappings describe how requirements from two frameworks relate to each other.

They are used for:

* Compliance translation
* Framework comparison
* Cross-standard reporting

{% stepper %}
{% step %}
### Generate a Mapping Excel file

**Tool:** [`prepare_mapping_v2.py`](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/prepare_mapping_v2.py)

Usage:

{% code title="Generate mapping skeleton" %}
```shell
python prepare_mapping_v2.py source.yaml target.yaml
```
{% endcode %}

This tool:

* Reads both frameworks
* Generates an Excel mapping file
* Lists all source and target requirements

You then manually define:

* Mapping between the two frameworks
* Relationship type (equal, subset, superset, intersect)
* Optional rationale and strength
{% endstep %}

{% step %}
### Convert the Mapping to YAML

Once the Excel file is completed:

{% code title="Convert mapping to YAML" %}
```shell
python convert_library_v2.py mapping.xlsx
```
{% endcode %}

The conversion tool will:

* Validate the mapping
* Generate a YAML mapping library
* Automatically create reverse mappings
{% endstep %}
{% endstepper %}

***

## 7. Importing a Custom Library into CISO Assistant

Once your Excel file has been successfully converted into a YAML file, the final step is to **import the library into CISO Assistant**.

This operation is performed directly from the CISO Assistant interface and does not require any additional tooling.

### 7.1 Prerequisites

Before importing your library, make sure that:

* Your Excel file has been successfully converted using `convert_library_v2.py`
* The resulting `.yaml` file contains no validation errors

### 7.2 Importing the Library

{% stepper %}
{% step %}
### **Open CISO Assistant**


{% endstep %}

{% step %}
### In the left navigation menu, go to:

Governance → Libraries
{% endstep %}

{% step %}
### Click on the <img src="../.gitbook/assets/image (11) (1).png" alt="Purple button with a white file in it and a &#x22;+&#x22; sign" data-size="line"> button


{% endstep %}

{% step %}
### Select your generated `.yaml` file


{% endstep %}

{% step %}
### Confirm the upload


{% endstep %}
{% endstepper %}

If the file is valid:

* The import will be accepted immediately
* The library will be added to your available libraries

### 7.3 After import: Where to find your Framework

Once the library is imported, go to **Compliance → Frameworks.**

Your custom framework will appear in the list (you can search it in the search bar). It can now be used in audits if it's a framework, or used as mapping of it's a mapping

### 7.4 Common import errors

If the import fails, CISO Assistant will display an explicit error message.

Common causes include:

* Missing mandatory fields in `library_meta`
* Invalid or duplicated URNs
* Inconsistent framework hierarchy
* Invalid references to threats, controls, or IGs

In most cases:

* Fix the issue in Excel
* Re-run `convert_library_v2.py`
* Re-import the updated YAML file

### 7.5 Testing your Framework after import

After importing a framework, it is strongly recommended to:

* Create a test audit using the framework
* Verify:
  * Hierarchy rendering
  * Assessable requirements
  * Questions and answers
  * Scores and implementation groups

This validation step ensures that:

* The framework behaves as expected
* No structural or logical issues remain

***

## 8. Updating and Maintaining Libraries

### 8.1 Version Management

Always increment `version` in the `library_meta` sheet.

If the version is unchanged, CISO Assistant will ignore the update.

### 8.2 URN Stability

Never change:

* `urn_prefix`
* `ref_id` of existing nodes

Changing URNs breaks:

* Mappings
* Historical assessments
* References

### 8.3 Best Practices

* Start small, then extend
* Test with minimal frameworks
* Avoid deep hierarchies
* Use Implementation Groups early (if necessary)
* Keep Excel files clean and ordered

***

## 9. Common Pitfalls

* Forgetting to increment the version
* Using v1 format instead of v2 format
* Changing `ref_id` on existing nodes
* Overusing advanced fields too early
* Creating overly deep hierarchies

***

## 10. Final Notes

For advanced or low-level options, always refer to the [dedicated README on GitHub](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/README.md).

***

## (Old) Videos

{% hint style="danger" %}
**IMPORTANT NOTICE**: The following sections contain information that is no longer up to date, but some parts are still useful today. Please consult them with caution.
{% endhint %}

### Testing your custom framework

{% embed url="https://vimeo.com/948010642?fe=cm&fl=pl" %}

### Full guide (French)

{% embed url="https://youtu.be/Ze8fp4_F0I4" %}
