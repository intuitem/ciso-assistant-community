---
description: How to submit a framework, matrix or catalog to the community repository
---

# Submit a library (Framework)

**If you are familiar with Github and Git, the submission is pretty straightforward:**

* fork the git repo and make sure it's sync-ed up
* add the excel sheet under the `tools` folder,
* &#x20;you can also add the generated yaml (assuming you have tested it) under `backend/library/libraries`&#x20;
* open a pull request and make sure you accept the CLA

and we'll take it from there :thumbsup:



**If you're not familiar with Github and the handling Git, you can follow these simplified steps using just the UI :**\


* create your excel sheet based on one of the samples in `tools` folder
* convert it to yaml using the `convert_library.py` tool

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.15.09 (1).png" alt=""><figcaption></figcaption></figure>

* Test it to make sure it can be parsed by the app and matches what you are expecting

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.16.43.png" alt=""><figcaption></figcaption></figure>

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.18.01.png" alt=""><figcaption></figcaption></figure>

* sign up on github to create an account and head to ciso assistant repository
* create your fork of the repository

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.21.17.png" alt=""><figcaption></figcaption></figure>

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.23.09 (1).png" alt=""><figcaption></figcaption></figure>



* if it's not your first time, make sure your fork is up to date



<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.24.19.png" alt=""><figcaption></figcaption></figure>

* go to the `tools` folder

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.36.12.png" alt=""><figcaption></figcaption></figure>

* click `Add file` and click `Upload files`&#x20;

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.37.38.png" alt=""><figcaption></figcaption></figure>

* drag and drop the excel file you've prepared or pull it from your filesystem.
* add a commit message, something like "Submitting framework x"&#x20;

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.38.45.png" alt=""><figcaption></figcaption></figure>

* commit the changes

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.39.47.png" alt=""><figcaption></figcaption></figure>

* if everything went well, you should see a message indicating that you're 1 commit ahead.

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.40.23.png" alt=""><figcaption></figcaption></figure>

* Optional: you can repeat this process to add the yaml file as well but on the `backend/library/libraries/` folder instead.
* You can now open the pull request:

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.40.57.png" alt=""><figcaption></figcaption></figure>

<figure><img src="../.gitbook/assets/scsh-2024-12-31-17.41.54.png" alt=""><figcaption></figcaption></figure>

There are of course other ways to achieve this in a much cleaner approach, but this is intended for a beginer discovering git and GitHub :wink:
