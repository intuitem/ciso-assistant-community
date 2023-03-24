# coding:utf-8
from playwright.sync_api import *
from playwright.async_api import *
from playwright import *
import time
import urlpatterns

def test_ASF003(page):
    # Test case: ASF-003
    # Step # | action | expected
    step = 0
    # 1 | Go to the url and login | Opening of home page | 
    step = 1
    def log_response(intercepted_response):
        print("a response was received:", intercepted_response.status, intercepted_response.status_text)
        assert intercepted_response.status != 500 and intercepted_response.status != 404, "Step "+str(step)+": not Ok"
    page.on("response", log_response)
    page.goto(urlpatterns.url)
    message = page.locator('id=hellothere')
    assert message.is_visible() == True, "Step "+str(step)+": not Ok"
    page.fill('id=id_username', 'root')
    page.fill('id=id_password', 'root')
    page.click('id=login')
    assert page.url == urlpatterns.url, "Step "+str(step)+": not Ok"
    # 2 | Click on composer | Opening of "Composer" page
    step = 2
    page.click("id=composer")
    assert page.url == urlpatterns.composer, "Step "+str(step)+": not Ok"
    # 3 | Select the first project (if it exists or skip) and click on “Process” | Opening of the first analysis | 
    step = 3
    page.click('id=overview')
    if page.locator('id=analysis').inner_text() != '0':
        page.click("id=composer")
        page.click("id=openmenu")
        page.click("id=option")
        page.click("id=closemenu")
        page.click("id=process")
        assert page.url == urlpatterns.composer +"?analysis=1", "Step "+str(step)+": not Ok"
    else:
        page.click("id=composer")
        assert page.url == urlpatterns.composer, "Step "+str(step)+": not Ok"
        title = page.locator('id=title')
        assert title.is_visible() == True, "Step "+str(step)+": not Ok"
    # 4 | Click on “Calendar” | Opening of the Calendar | 
    step = 4
    page.click("id=calendar")
    assert page.url == urlpatterns.calendar, "Step "+str(step)+": not Ok"
    # 5 | Click on “My projects” | Opening of "My projects" |
    step = 5
    page.click("id=myprojects") 
    assert page.url == urlpatterns.myprojects, "Step "+str(step)+": not Ok"
    time.sleep(1)
    title = page.locator('id=message')
    assert title.is_visible() == True, "Step "+str(step)+": not Ok"
    # 6 | Click on "Overview" | Opening of "Overview" |
    step = 6
    page.click("id=overview")
    assert page.url == urlpatterns.overview, "Step "+str(step)+": not Ok"
    time.sleep(1)
    header = page.locator('id=header')
    assert header.is_visible() == True, "Step "+str(step)+": not Ok"
