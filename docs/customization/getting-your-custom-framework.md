# Getting your custom framework

CISO Assistant allows you to manage your custom frameworks. The format is a text-based YAML file that you can customize, but it can be tricky to maintain and debug. To manage this, we've introduced a simpler approach to convert Excel sheets using the `convert_library.py` utility available at the [`/tools`](https://github.com/intuitem/ciso-assistant-community/tree/main/tools) of the [Github](https://github.com/intuitem/ciso-assistant-community/) repository root.

### Structure

<figure><img src="../.gitbook/assets/image (11).png" alt=""><figcaption><p>Hierarchy-based file</p></figcaption></figure>

The first thing to consider is structuring your requirements into a hierarchy, as illustrated in the example above. Most standards, frameworks, and law documents are already organized this way. This is the depth concept and CISO Assistant has been tested with nodes up to the 8th level depth (documents beyond 6 are mostly hard to read anyway)

Then, the other vital aspect to think about will be which items are actually assessable. For instance, the categories, sections, and subsections are for organization and, therefore, won't be assessable unlike the requirements.

Here is what a standard file should look like accordingly:

<figure><img src="../.gitbook/assets/image (12).png" alt=""><figcaption></figcaption></figure>

This is taken from the sample file available under `/tools/sample/sample.xlsx` and can be used as a reference.

Implementation groups are an optional argument that can be used to create subset of the requirements per level or a scope of applicability. They can be combined or isolated depending on the framework structure.

### File conversion steps

1. Clone the repo and make sure you are at its root
2. Make sure you have Python installed (including pip), version 3.11 or higher is recommended
3. cd to `/tools`
4. run\
   `pip install -r requirements.txt`\
   to install the script dependencies
5. copy the sample directory, including the file within, to a new directory at the same level, for instance, `myframework/my-custom-framework.xlsx`
6. Edit the first tab (`library_content`) to describe your framework metadata
   1. Implementation groups and score descriptions are optional, so if they don't apply, you can simply remove lines
7. Edit the Excel sheet according to the expected hierarchy.
   1. The order of the items is essential and will be used to build the tree on CISO Assistant. So make sure you're following the previously described structure
8. From the tools folder, run\
   \
   `python3 convert_library.py myframework/my-custom-framework.xlsx`\
   \
   to generate the yaml file, if a mandatory field is missing, you'll get an error explaining the issue.
9. If everything is good, you'll get a message confirming the generation of the file `generating myframework/my-custom-framework.yaml`

### importing

1. Open CISO Assistant. On the side menu, go to `Governance/Libraries` then to the `Libraries store` tab
2. Scroll down to get to `Upload your own library` section and select your file.
3. If the file is consistent and correct, you'll get a confirmation and it will get straight ahead to your imported frameworks under `Compliance/Frameworks` section

### testing your custom framework

We have simplified the steps of testing custom frameworks starting version 1.3.4 where you can experiment with the same flexibility for both on-premises and SaaS version:\
\\

{% embed url="https://vimeo.com/948010642" %}
Testing your custom framework
{% endembed %}

## NEW: Full guide (French)

{% embed url="https://www.youtube.com/live/Ze8fp4_F0I4" %}
