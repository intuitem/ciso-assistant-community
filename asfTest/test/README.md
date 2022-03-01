# **Running Test Guide**

## **Dependencies**

* Install [Playwright for Python](https://playwright.dev/python/docs/intro)
* Install [Pytest Plugin](https://playwright.dev/python/docs/test-runners)
> You can find all documentation on Playwright and pytest-playwright with those links

## **Running**

* **Run all tests**

```sh
$ python3 -m pytest  
```

* **Run a specific test**

```sh
$ python3 -m pytest <testName>.py
```

* **Run in headed mode**

```sh
$ python3 -m pytest <testName>.py --headed --slowmo 300
# it's recommended to use --slowmo otherwise the execution is too fast
```

To see others interesting commands please refer to [Pytest Plugin Documentation](https://playwright.dev/python/docs/test-runners).

## **Errors**

* An error can occured if you have multiple Python installations on your system. Try these command lines to fix this problem:
```sh
$ python3 -m pip install playwright
$ python3 -m playwright install
$ python3 -m pytest
```