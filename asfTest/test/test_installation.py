# coding:utf-8
from playwright.sync_api import *
from playwright.async_api import *
from playwright import *
import urlpatterns

def test_ASF002(page):
    # Test case: installation
	# Step # | action | expected
	step = 0
	# 1 | Go to the url | Go on login page
	step = 1
	def log_response(intercepted_response):
		print("a response was received:", intercepted_response.status, intercepted_response.status_text)
		assert intercepted_response.status not in (500, 404), "Step "+str(step)+": not Ok"
	page.on("response", log_response)
	page.goto(urlpatterns.url)
	message = page.locator('id=hellothere')
	assert message.is_visible() is True, "Step 1: not Ok"
	# 2 | Enter an admin username and a password, then click on "Login" | Open home page
	step = 2
	page.fill("id=id_username", "root@gmail.com")
	page.fill("id=id_password", "root")
	page.click('id=login')
	assert page.url == urlpatterns.url, "Step "+str(step)+": not Ok"
