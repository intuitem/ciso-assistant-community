# coding:utf-8
from playwright.sync_api import *
from playwright.async_api import *
from playwright import *
import time
import urlpatterns

def test_ASF004(page):
	# Test case: ASF-004
	# Step # | action | expected
	step = 0
	# 1 | Go to the url and login | Opening of home page | 
	step = 1
	def log_response(intercepted_response):
		print("a response was received:", intercepted_response.status, intercepted_response.status_text)
		assert intercepted_response.status != 500 and intercepted_response.status != 404, "Step "+str(step)+": not Ok"
	def log_response505(intercepted_response):
		print("a response was received:", intercepted_response.status, intercepted_response.status_text)
		assert intercepted_response.status != 500, "Step "+str(step)+": not Ok"
	page.on("response", log_response)
	page.goto(urlpatterns.url)
	message = page.locator('id=hellothere')
	assert message.is_visible() == True, "Step "+str(step)+": not Ok" 
	page.fill("id=id_username", "root2")
	page.fill("id=id_password", "rootroot")
	page.click('id=login')
	# 2 | Click on menu “More” | Opening of the menu with the message: “Hello, (username)”
	step = 2
	page.click("id=more")
	time.sleep(0.1)
	message = page.locator('text=Hello, Root2')
	assert message.is_visible() == True, "Step "+str(step)+": not Ok" 
	# 3 | Click on “Scoring assistant” | Opening of “Scoring assistant” page
	step = 3
	page.click("id=scoring")
	assert page.url == urlpatterns.scoringassistant, "Step "+str(step)+": not Ok"
	# 4 | Click on “Risk matrix” | Opening of “Risk matrix” page
	step = 4
	page.click("id=more")
	page.click("id=riskmatrix")
	assert page.url == urlpatterns.riskmatrix, "Step "+str(step)+": not Ok"
	# 5 | Click on “Sign-out” | Go back on login page
	step = 5
	page.click("id=more")
	page.click("id=signout")
	assert page.url == urlpatterns.login, "Step "+str(step)+": not Ok"
	message = page.locator('id=hellothere')
	assert message.is_visible() == True, "Step "+str(step)+": not Ok" 
	page.fill("id=id_username", "root2")
	page.fill("id=id_password", "rootroot")
	page.click('id=login')
	# 6 | Click on “X-Rays (my projects)” | Opening of admin registration page
	step = 6
	page.click("id=more")
	page.remove_listener("response", log_response)
	page.on("response", log_response505)
	page.click("id=xrays")
	assert page.url == urlpatterns.xrayslogin, "Step "+str(step)+": not Ok"
