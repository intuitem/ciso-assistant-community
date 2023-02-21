# coding: utf-8
""" encoding UTF-8 """

from playwright.sync_api import *
from playwright.async_api import *
from playwright import *
import urlpatterns

def test_asf001(page):
	"""
	Test case: ASF-001
	Login test with different username and password combination
	# Step n | action | expected
	"""
	test = 1
	# 1 | Go to the url  | Opening of the login page
	step = 1
	def log_response(intercepted_response):
		# print("a response was received:", intercepted_response.status, intercepted_response.status_text)
		assert intercepted_response.status not in (500, 404), "Test "+str(test)+" Step "+str(step)+": not Ok"
	page.on("response", log_response)
	page.goto(urlpatterns.URL)
	assert page.url == urlpatterns.LOGINFIRST, "Test "+str(test)+" Step "+str(step)+": not Ok"
	# 2 | Enter a wrong username, a wrong password and click on “Log in” | Error message: “Please enter the correct username and password”
	step += 1
	page.fill("id=id_username", "user")
	page.fill("id=id_password", "pass")
	page.click("id=login")
	assert page.url == urlpatterns.LOGINFIRST, "Test "+str(test)+" Step "+str(step)+": not Ok"
	message = page.locator("ul.errorlist.nonfield")
	assert message.is_visible() is True, "Test "+str(test)+" Step "+str(step)+": not Ok"
	# 3 | Enter admin username and password of a basic account and click on “Log in” | Error message: “Please enter the correct username and password”
	step += 1
	page.fill("id=id_username", "root")
	page.fill("id=id_password", "rootroot")
	page.click("id=login")
	assert page.url == urlpatterns.LOGINFIRST, "Test "+str(test)+" Step "+str(step)+": not Ok"
	assert message.is_visible() is True, "Test "+str(test)+" Step "+str(step)+": not Ok"
	# 4 | Enter admin password and username of a basic account and click on “Log in” | Error message: “Please enter the correct username and password”
	step += 1
	page.fill("id=id_username", "root2@gmail.com")
	page.fill("id=id_password", "root")
	page.click("id=login")
	assert page.url == urlpatterns.LOGINFIRST, "Test "+str(test)+" Step "+str(step)+": not Ok"
	assert message.is_visible() is True, "Test "+str(test)+" Step "+str(step)+": not Ok"
	# 5 | Enter valid username and password | Go on home page
	step += 1
	page.fill('id=id_username', 'root@gmail.com')
	page.fill('id=id_password', 'root')
	page.click('id=login')
	assert page.url == urlpatterns.URL, "Test "+str(test)+" Step "+str(step)+": not Ok"

def test_asf002(page):
	"""
	Test case: ASF-002
	Login, create an user and logout
	Step n | action | expected
	"""
	test = 2
	# 1 | Go to the url | Go on login page
	step = 1
	def log_response(intercepted_response):
		print("a response was received:", intercepted_response.status, intercepted_response.status_text)
		assert intercepted_response.status not in (500, 404), "Test "+str(test)+" Step "+str(step)+": not Ok"
	page.on("response", log_response)
	page.goto(urlpatterns.URL)
	message = page.locator('id=hellothere')
	assert message.is_visible(), "Test "+str(test)+" Step "+str(step)+": not Ok"
	# 2 | Enter an admin username and a password, then click on "Login" | Open home page
	step += 1
	page.fill("id=id_username", "root@gmail.com")
	page.fill("id=id_password", "root")
	page.click('id=login')
	assert page.url == urlpatterns.URL, "Test "+str(test)+" Step "+str(step)+": not Ok"
	# 3 | Create a new user | Send a mail to the user
	step += 1
	page.click("id=users_tab")
	page.click("id=user_create")
	page.fill("id=id_user_email", "root2@gmail.com")
	page.keyboard.press("Enter")
	toast = page.locator("id=success-toast")
	user = page.locator("id=users").element_handles()[-1]
	assert toast.is_visible(), "Test "+str(test)+" Step "+str(step)+": not Ok"
	assert user.inner_text() == "root2@gmail.com", "Test "+str(test)+" Step "+str(step)+": not Ok"
	# 4 | Logout | Come back on login page
	step += 1
	page.click("id=my_menu")
	page.click("id=logout")
	assert page.url == urlpatterns.LOGIN, "Test "+str(test)+" Step "+str(step)+": not Ok"
	assert message.is_visible(), "Test "+str(test)+" Step "+str(step)+": not Ok"
	# 5 | Create password for the new account | Come back on Login page
	step += 1
	page.goto()
	#  | Enter new user's username and password | Login successfully
	# step += 1
	# page.fill("id=id_username", "root2@gmail.com")
	# page.fill("id=id_password", "rootroot")
	# page.click('id=login')
	# assert page.url == urlpatterns.url, "Test "+str(test)+" Step "+str(step)+": not Ok"
