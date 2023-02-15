# coding:utf-8
from playwright.sync_api import *
from playwright.async_api import *
from playwright import *
import urlpatterns

def test_asf001(page):
	# Test case: ASF-001
	# Step # | action | expected
	step = 0
	# 1 | Go to the url  | Opening of the login page | 
	step = 1
	def log_response(intercepted_response):
		# print("a response was received:", intercepted_response.status, intercepted_response.status_text)
		assert intercepted_response.status != 500 and intercepted_response.status != 404, "Step "+str(step)+": not Ok"
	page.on("response", log_response)
	page.goto(urlpatterns.url)
	assert page.url == urlpatterns.loginfirst, "Step "+str(step)+": not Ok"
	# 2 | Enter a wrong username, a wrong password and click on “Log in” | Error message: “Please enter the correct username and password”
	step = 2	
	page.fill("id=id_username", "user")
	page.fill("id=id_password", "pass")
	page.click("id=login")
	assert page.url == urlpatterns.loginfirst, "Step "+str(step)+": not Ok"
	message = page.locator("ul.errorlist.nonfield")
	assert message.is_visible() == True, "Step "+str(step)+": not Ok"
	# 3 | Enter admin username and password of a basic account and click on “Log in” | Error message: “Please enter the correct username and password”	
	step = 3	
	page.fill("id=id_username", "root")
	page.fill("id=id_password", "rootroot")
	page.click("id=login")
	assert page.url == urlpatterns.loginfirst, "Step "+str(step)+": not Ok"
	assert message.is_visible() == True, "Step "+str(step)+": not Ok"
	# 4 | Enter admin password and username of a basic account and click on “Log in” | Error message: “Please enter the correct username and password”	
	step = 4	
	page.fill("id=id_username", "root2@gmail.com")
	page.fill("id=id_password", "root")
	page.click("id=login")
	assert page.url == urlpatterns.loginfirst, "Step "+str(step)+": not Ok"
	assert message.is_visible() == True, "Step "+str(step)+": not Ok"
	# 5 | Enter valid username and password | Go on home page	
	step = 5	
	page.fill('id=id_username', 'root@gmail.com')
	page.fill('id=id_password', 'root')
	page.click('id=login')
	assert page.url == urlpatterns.url, "Step "+str(step)+": not Ok"