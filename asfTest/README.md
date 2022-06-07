# **Functional Test Book for MIRA**

* This project is a [Django](https://docs.djangoproject.com/en/4.0/) web application for risk assessment and management.
* The purpose of this test book is to delimit the functional test environment of this application.
* Please refer to this document for any required information.
* The entire test process needs to be reported here, as well as any modifications in its route.

## **Details**

* **Test perimeter**

  * Don't get any [error reporting](https://docs.djangoproject.com/fr/4.0/howto/error-reporting/).
  * A simple user/client cannot have any [administrator rigths](https://docs.djangoproject.com/fr/4.0/topics/auth/default/).
  * A simple user cannot access the client part.
  * A client can login, and logout succesfully.
  * Front-end ⇌ back-end.

* **Test environment**

  * Records are made with [Playwright](https://playwright.dev/python/).
  * All tests are written in [python](https://playwright.dev/python/docs/intro) scripts.
  * We run tests with [pytest](https://playwright.dev/python/docs/test-runners) plugin.
  * One python test file for each test sheet.

* **Test cover**
  
  * We want to reach a [statement coverage](https://en.wikipedia.org/wiki/Code_coverage).

## **Running Tests**

Check out our [Running Test Guide](/asfTest/test/README.md) to see how to run tests.

## **Tests List**

* **Test sheet 1**
 
  * *Name: User Rights Test*
  * *Goal: Check that simple user and client rights are well-configured*
  * *Test Case: [ASF-001](/test/test_asf001.py)*
  
  | Num | Action                                                                           | Expected                                                        | Result |
  | :-: | :------------------------------------------------------------------------------- | :-------------------------------------------------------------- | :----: |
  |  1  | Go to the URL http://127.0.0.1:8000/                                             | Opening of the login page                                       |        |
  |  2  | Enter a wrong username, a wrong password and click on "Log in"                   | Error message: "Please enter the correct username and password" |        |
  |  3  | Enter admin username and password of a basic account and click on "Log in"       | Error message: "Please enter the correct username and password" |        |
  |  4  | Enter admin password and username of a basic account and click on "Log in" | Error message: "Please enter the correct username and password" |        |
  |  5  | Enter a valid username and password                                                | Go on home page                                                 |        |

* **Test sheet 2**
 
  * *Name: Login/out Test*
  * *Goal: Check that a user can: login, and logout*
  * *Test Case: [ASF-002](/test/test_asf002.py)*
  
  | Num | Action                                                        | Expected                                 | Result |
  | :-: | :------------------------------------------------------------ | :--------------------------------------- | :----: |
  |  1  | Go to the url http://127.0.0.1:8000/                          | Go on login page                         |        |
  |  2  | Enter an admin username and a password, then click on "Login" | Open home page                           |        |
  |  3  | Click on "Edit"                                               | Open admin page                          |        |
  |  4  | Click on "Logout"                                             | Come back on login page                  |        |
  |  5  | Enter a username and a password, then click on "Login"        | Open home page                           |        |
  |  6  | Click on "Edit"                                               | Open admin login page with error message |        |
  |  7  | Login and logout                                              | Come back on login page                  |        |
  
* **Test sheet 3**
 
  * *Name: Tabs Test*
  * *Goal: Check that all tabs are working*
  * *Test Case: [ASF-003](/test/test_asf003.py)*
  
  | Num | Action                                                                 | Expected                      | Result |
  | :-: | :--------------------------------------------------------------------- | :---------------------------- | :----: |
  |  1  | Go to the URL http://127.0.0.1:8000/ and login                         | Opening of home page          |        |
  |  2  | Click on composer                                                      | Opening of "Composer" page    |        |
  |  3  | Select the first project (if it exists or skips) and click on “Process” | Opening of the first analysis |        |
  |  4  | Click on “Calendar”                                                    | Opening of the Calendar       |        |
  |  5  | Click on “My projects”                                                 | Opening of "My projects"      |        |
  |  6  | Click on “Analytics”                                                   | Opening of "Analytics"        |        |
  
* **Test sheet 4**
 
  * *Name: "More" Menu Test*
  * *Goal: Check features in the menu "More"*
  * *Test Case: [ASF-004](/test/test_asf004.py)*

  | Num | Action                                         | Expected                                                  | Result |
  | :-: | :--------------------------------------------- | :-------------------------------------------------------- | :----: |
  |  1  | Go to the URL http://127.0.0.1:8000/ and login | Opening of home page                                      |        |
  |  2  | Click on the menu "More"                           | Opening of the menu with the message: "Hello, (username)" |        |
  |  3  | Click on "Scoring assistant"                   | Opening of "Scoring assistant" page                       |        |
  |  4  | Click on "Risk matrix"                         | Opening of "Risk matrix" page                             |        |
  |  5  | Click on "Sign-out"                            | Go back on login page                                     |        |
  |  6  | Click on "X-Rays (my projects)"                | Opening of admin registration page                        |        |
  
* **Test sheet 5**
 
  * *Name: Home page links test*
  * *Goal: Check links on home page (skip if there are no links)*
  * *Test Case: [ASF-005](/test/test_asf005.py)*

  | Num | Action                                                        | Expected                   | Result |
  | :-: | :------------------------------------------------------------ | :------------------------- | :----: |
  |  1  | Go to the URL http://127.0.0.1:8000/, click on the first link | Opening of RA-1            |        |
  |  2  | Click on "MIRA"                                               | Come back on home page     |        |
  | 3.1 | Click on the next link "id"                                   | Opening of RA-id           |        |
  | 3.2 | Go to the previous page "p"                                   | Opening of page number "p" |        |
  | 3.3 | Click on next page if necessary                               | Go to the next page        |        |
  |  4  | Click on "MIRA"                                               | Come back on home page     |        |
  

* **Test sheet 6**
 
  * *Name: Research test*
  * *Goal: Check that all links found by the search bar work*
  * *Test Case: [ASF-006](/test/test_asf006.py)*

  | Num | Action                                                         | Expected                                  | Result |
  | :-: | :------------------------------------------------------------- | :---------------------------------------- | :----: |
  |  1  | Go to the URL http://127.0.0.1:8000/ and login                 | Opening of home page                      |        |
  |  2  | Search "e" and submit                                          | Displays all matching results with an "e" |        |
  | 3.1 | Click on all links                                             | Opening of all links without errors       |        |
  | 3.2 | (no links) check-in "Analytics" there isn't any analysis, ... | Each counter should be '0'                |        |

* **Test sheet 7**
 
  * *Name: Traduction test*
  * *Goal: Check the traduction*
  * *Test Case: [ASF-007](/test/test_asf007.py)*

  | Num | Action                                             | Expected                      | Result |
  | :-: | :------------------------------------------------- | :---------------------------- | :----: |
  |  1  | Go to the URL and login                            | Opening of  home page         |        |
  |  2  | Click on "More", and choose "Français" in language | Loading of French traduction  |        |
  |  3  | Click on "More", and choose "English" in language  | Loading of English traduction |        |


