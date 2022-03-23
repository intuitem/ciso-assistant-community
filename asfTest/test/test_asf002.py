# coding:utf-8
from playwright.sync_api import *
from playwright.async_api import *
from playwright import *
import time
import urlpatterns
import pytest

@pytest.mark.skip(reason="waiting new back-office")
def test_ASF002(page):
    # Test case: ASF-002
	# Step # | action | expected
	step = 0
	# 1 | Go to the url | Go on login page
	step = 1
	def log_response(intercepted_response):
		print("a response was received:", intercepted_response.status, intercepted_response.status_text)
		assert intercepted_response.status != 500 and intercepted_response.status != 404, "Step "+str(step)+": not Ok"
	page.on("response", log_response)
	page.goto(urlpatterns.url)
	message = page.locator('id=hellothere')
	assert message.is_visible() == True, "Step 1: not Ok"
	# 2 | Enter an admin username and a password, then click on "Login" | Open home page
	step = 2
	page.fill("id=id_username", "root")
	page.fill("id=id_password", "root")
	page.click('id=login')
	assert page.url == urlpatterns.url, "Step "+str(step)+": not Ok"
	# 3 | Click on "Edit" | Open admin page
	step = 3
	page.click('id=edit')
	assert page.url == urlpatterns.admin, "Step "+str(step)+": not Ok"
	# 4 | Click on “Log out” | Come back on login page
	step = 4
	page.click("i.fa.fa-angle-down.user-area-toggler")
	page.click("a.logout")
	assert page.url == urlpatterns.login, "Step "+str(step)+": not Ok"
	assert message.is_visible() == True, "Step "+str(step)+": not Ok"
	# 5 | Enter a username and a password, then click on "Login" | Open home page
	step = 5
	page.fill("id=id_username", "root2")
	page.fill("id=id_password", "rootroot")
	page.click('id=login')
	assert page.url == urlpatterns.url, "Step "+str(step)+": not Ok"
	# 6 | Click on "Edit" | Open admin login page with error message
	step = 6
	page.remove_listener("response", log_response)
	page.click('id=edit')
	assert page.url == urlpatterns.adminregistration, "Step "+str(step)+": not Ok"
	time.sleep(0.1)
	error = page.locator('p.errornote')
	assert error.is_visible() == True, "Step "+str(step)+": not Ok"
	# 7 | Login and logout | Come back on login page
	step = 7
	page.on("response", log_response)
	page.fill("id=id_username", "root")
	page.fill("id=id_password", "root")
	page.click('text=Log in')
	page.click("i.fa.fa-angle-down.user-area-toggler")
	page.click("a.logout")
	assert page.url == urlpatterns.login, "Step "+str(step)+": not Ok"
	assert message.is_visible() == True, "Step "+str(step)+": not Ok"
