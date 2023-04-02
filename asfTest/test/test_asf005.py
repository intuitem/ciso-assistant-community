# coding:utf-8
from playwright.sync_api import *
from playwright.async_api import *
from playwright import *

import time
import urlpatterns
import re

def test_ASF005(page):
    # Test case: ASF-005
    # Step # | action | expected
    step = 0
    # 1 | Go to the url, click on the first link | Opening of RA-1
    step = 1
    def log_response(intercepted_response):
        print("a response was received:", intercepted_response.status, intercepted_response.status_text)
        assert intercepted_response.status != 500 and intercepted_response.status != 404, "Step "+str(step)+": not Ok"
    page.on("response", log_response)
    page.goto(urlpatterns.URL)
    assert page.url == urlpatterns.LOGINFIRST, "Step "+str(step)+": not Ok"
    message = page.locator('id=hellothere')
    assert message.is_visible() == True, "Step "+str(step)+": not Ok" 
    page.fill("id=id_username", "root2")
    page.fill("id=id_password", "rootroot")
    page.click('id=login')
    time.sleep(0.1)
    if page.locator('id=analysis1').is_visible():
        page.click('id=analysis1')
        assert page.url == urlpatterns.ra + "1/", "Step "+str(step)+": not Ok"
        print(page.locator('id=analysis1'))
        # 2 | Click on MIRA | Come back on home page
        step = 2
        page.click("id=homepage")
        assert page.url == urlpatterns.URL, "Step "+str(step)+": not Ok"
        assert page.locator('id=pagenum').is_visible() == True, "Step "+str(step)+": not Ok"
        next = 1
        step = 3
        countAnalyses = 0
        while next != 0:
            analyses = re.findall(r'id="analysis([0-9]+)"', page.content(), re.MULTILINE)
            for id in analyses:
                # 3.1 | Click on the next link “id” | Opening of RA-id
                if page.locator('id=analysis'+ str(id)).is_visible():
                    step = 3.1
                    page.click('id=analysis'+ str(id))
                    assert page.url == urlpatterns.ra + str(id) + "/", "Step "+str(step)+": not Ok"
                    # 3.2 | Go to the previous page “p” | 	Opening of page number “p”
                    step = 3.2
                    page.goto(urlpatterns.URL + "?page=" + str(next))
                    assert page.url == urlpatterns.URL + "?page=" + str(next), "Step "+str(step)+": not Ok"
                    countAnalyses += 1
            # 3.3 | Click on next page if necessary | Go to the next page
            if page.locator("id=next").is_visible():
                step = 3.3
                page.click("id=next")
                next += 1
                print(next)
                assert page.url == urlpatterns.URL + "?page=" + str(next), "Step "+str(step)+": not Ok"
            # 4 | Click on MIRA | Come back on home page
            else:
                step = 4
                next = 0
                page.click("id=homepage")
                assert page.url == urlpatterns.URL, "Step "+str(step)+": not Ok"
        page.click('id=overview')
        assert page.locator('id=analysis').inner_text() == str(countAnalyses), "Step "+str(step)+": not Ok"
    else:
        time.sleep(0.1)
        assert page.locator('id=pagenum').is_visible() == True, "Step "+str(step)+": not Ok"
        page.click('id=overview')
        assert page.locator('id=analysis').inner_text() == '0', "Step "+str(step)+": not Ok"