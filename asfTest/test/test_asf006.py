# coding:utf-8
from playwright.sync_api import *
from playwright.async_api import *
from playwright import *
import urlpatterns

def test_ASF006(page):
	# Test case: ASF-006
	# Step # | action | expected
	step = 0
	# 1 | Go to the url and login| Opening of home page |
	step = 1
	def log_response(intercepted_response):
			#print("a response was received:", intercepted_response.status, intercepted_response.status_text)
		assert intercepted_response.status != 500 and intercepted_response.status != 404, "Step "+str(step)+": not Ok"
	page.on("response", log_response)
	page.goto(urlpatterns.URL)
	message = page.locator('id=hellothere')
	assert message.is_visible() == True, "Step "+str(step)+": not Ok"
	page.fill('id=id_username', 'root')
	page.fill('id=id_password', 'root')
	page.click('id=login')
	# 2 | Search "e" and submit | Displays all matching results with an "e" |
	step = 2
	page.fill("id=search", "e")
	page.click("id=submit")
	assert page.url == urlpatterns.search + "?q=e", "Step "+str(step)+": not Ok"
	step = 3
	# 3.1 | Click on all links | Opening of all likns without errors |
	step = 3.1
	riskanalysis_count = page.locator("id=riskanalysis").count()
	if riskanalysis_count > 0: 
		for i in range (riskanalysis_count):
			#print(page.locator("id=riskanalysis").element_handles()[i]) 
			link = page.locator("id=riskanalysis").element_handles()[i]
			link.click()
			name = page.locator('id=name')
			assert name.is_visible() == True, "Step "+str(step)+": not Ok"
			page.goto(urlpatterns.search + "?q=e")
	riskscenario_count = page.locator("id=riskscenario").count()
	if riskscenario_count > 0:
		for i in range (riskscenario_count):
			#print(page.locator("id=riskscenario").element_handles()[i]) 
			page.locator("id=riskscenario").element_handles()[i].click()
			name = page.locator('id=name')
			assert name.is_visible() == True, "Step "+str(step)+": not Ok"
			page.goto(urlpatterns.search + "?q=e")
	security_function_count = page.locator("id=security_function").count()
	if security_function_count > 0:
		for i in range (security_function_count):
			#print(page.locator("id=security_function").element_handles()[i]) 
			page.locator("id=security_function").element_handles()[i].click()
			name = page.locator('id='+str(i+1))
			assert name.is_visible() == True, "Step "+str(step)+": not Ok"
			page.goto(urlpatterns.search + "?q=e")
	# 3.2 | (no links) check in "Overview" there aren't any analysis, ... | Each counter should be '0' |
	step = 3.2
	if riskscenario_count == 0 and riskanalysis_count == 0 and security_function_count == 0:
		page.click('id=overview')
		assert page.locator('id=riskscenarios').inner_text() == '0', "Step "+str(step)+": not Ok"
		assert page.locator('id=security_functions').inner_text() == '0', "Step "+str(step)+": not Ok"
		assert page.locator('id=analysis').inner_text() == '0', "Step "+str(step)+": not Ok"