# coding:utf-8
from playwright.sync_api import *
from playwright.async_api import *
from playwright import *

import time
import urlpatterns
import re

def test_BO001(page):
	# Test case: BO-001
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
    # 2 |
	step = 2
	page.click('id=edit')
	message = page.locator('id=title')
	assert message.is_visible() == True, "Step "+str(step)+": not Ok"
	# 3 |
	step = 3
	name = 'Domain Test'
	department = 'Test Department'
	page.click('id=projectsdomains')
	page.click('id=modal')
	page.fill('id=id_name', name)
	page.fill('id=id_department', department)
	page.click('id=save')
	domains = re.findall(r'id="domain([0-9]+)"', page.content(), re.MULTILINE)
	for id in domains:		
		domain = page.locator('id=domain'+id).inner_text()
		if domain == name:
			break
	assert domain == name, "Step "+str(step)+": not Ok"
	# 4 |
	step = 4
	page.click('id=domain'+id)
	assert page.locator('id=page_title').inner_text() == name, "Step "+str(step)+": not Ok"
	projectName = "Project Test"
	page.click('id=newProjectModal')
	page.fill('id=id_project_name', projectName)
	page.fill('id=id_internal_id', 'TST')
	page.select_option('id=id_parent_group', id)
	page.select_option('id=id_lc_status', "in_dev")
	page.click('id=save')
	projects = re.findall(r'id="project([0-9]+)"', page.content(), re.MULTILINE)
	for projectId in projects:		
		project = page.locator('id=project'+projectId).inner_text()
		if project == projectName:
			break
	assert project == projectName, "Step "+str(step)+": not Ok"
	# 5 |
	step = 5
	page.click('id=project'+projectId)
	assert page.locator('id=page_title').inner_text() == projectName, "Step "+str(step)+": not Ok"
	page.click('id=newRiskAnalysisModal')
	page.select_option('id=id_project', projectId)
	page.select_option('id=id_auditor', "3")
	page.select_option('id=id_rating_matrix', "critical")
	page.fill('id=id_comments', "Test")
	page.set_checked('id=id_is_draft', checked=False)
	page.click('id=analysis_save')
	analysisName = "Project Test, version 0.1"
	analyses = re.findall(r'id="analysis([0-9]+)"', page.content(), re.MULTILINE)
	for analysisId in analyses:		
		analysis = page.locator('id=analysis'+analysisId).inner_text()
		if analysisName in analysis:
			break
	assert analysisName in analysis, "Step "+str(step)+": not Ok"
	# 6 |
	step = 6
	page.click('id=analysis'+analysisId)
	assert page.locator('id=page_title').inner_text() == "RA-"+ analysisId + ": " + analysisName, "Step "+str(step)+": not Ok"
	# clear |
	page.click('id=projectsdomains')
	page.click('id=action'+id)
	page.click('id=deleteAction'+id)
	page.click('id=delete'+id)