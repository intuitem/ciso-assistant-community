# coding:utf-8
from playwright.sync_api import *
from playwright.async_api import *
from playwright import *
import time
import urlpatterns

def test_ASF007(page):
	# Test case: ASF-007
	# Step # | action | expected
	step = 0
	def log_response(intercepted_response):
		#print("a response was received:", intercepted_response.status, intercepted_response.status_text)
		assert intercepted_response.status != 500 and intercepted_response.status != 404, "Step "+str(step)+": not Ok"
	page.on("response", log_response)
	# 1 | Go to the url and login | Opening of  home page |
	step = 1
	page.goto(urlpatterns.url)
	message = page.locator('id=hellothere')
	assert message.is_visible() == True, "Step "+str(step)+": not Ok"
	page.fill('id=id_username', 'root')
	page.fill('id=id_password', 'root')
	page.click('id=login')
	# 2 | Click on "More", and choose "Français" in language | Loading of French traduction |
	step = 2
	page.click('id=more')
	page.locator('id=language').select_option('fr')
	title = page.locator('id=title').inner_text()
	tabs = [
		page.locator('id=edit').inner_text().strip(),
		page.locator('id=overview').inner_text().strip(),
		page.locator('id=myprojects').inner_text().strip(),
		page.locator('id=calendar').inner_text().strip(),
		page.locator('id=composer').inner_text().strip(),
		page.locator('id=more').inner_text().strip()
	]
	tabsfr = [
		"Modifier",
		"Analyse",
		"Mes Projets",
		"Calendrier",
		"Composition",
		"Plus"
		
	]
	for tab in tabsfr:
		assert tab in tabs, "Step "+str(step)+": not Ok"
	assert title == "Registre des analyses", "Step "+str(step)+": not Ok"
	# 3 | Click on "More", and choose "English" in language | Loading of English traduction |
	step = 3
	page.click('id=more')
	page.locator('id=language').select_option('en')
	title = page.locator('id=title').inner_text()
	tabs = [
		page.locator('id=edit').inner_text().strip(),
		page.locator('id=overview').inner_text().strip(),
		page.locator('id=myprojects').inner_text().strip(),
		page.locator('id=calendar').inner_text().strip(),
		page.locator('id=composer').inner_text().strip(),
		page.locator('id=more').inner_text().strip()
	]
	tabsen = [
		"Edit",
		"Analytics",
		"My projects",
		"Calendar",
		"Composer",
		"More"
		
	]
	for tab in tabsen:
		assert tab in tabs, "Step "+str(step)+": not Ok"
	assert title == "Analysis registry", "Step "+str(step)+": not Ok"

