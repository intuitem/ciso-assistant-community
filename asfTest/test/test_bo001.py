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
    # 2 | Log in the back-office
	step = 2
	page.click('id=edit')
	message = page.locator('id=title')
	assert message.is_visible() == True, "Step "+str(step)+": not Ok"
	# 3 | Create a threat and a security function
	step = 3
	threatName = 'Threat Test'
	security_functionName = 'SecurityFunction Test'
	page.click('id=threats')
	page.click('id=newThreat')
	page.fill('id=id_threat_title', threatName)
	page.click('id=save_threat')
	threats = re.findall(r'id="scenario([0-9]+)"', page.content(), re.MULTILINE)
	for threatId in threats:		
		threat = page.locator('id=scenario'+threatId).inner_text()
		if threat == threatName:
			break
	assert threat == threatName, "Step "+str(step)+": not Ok"
	page.click('id=securityFunctions')
	page.click('id=newSecurityFunction')
	page.fill('id=id_security_function_name', security_functionName)
	page.fill('id=id_security_function_provider', 'us')
	page.click('id=save')
	functions = re.findall(r'id="function([0-9]+)"', page.content(), re.MULTILINE)
	for functionId in functions:		
		function = page.locator('id=function'+functionId).inner_text()
		if function == security_functionName:
			break
	assert function == security_functionName, "Step "+str(step)+": not Ok"
	# 4 | Create a project domain
	step = 4
	domainName = 'Domain Test'
	department = 'Test Department'
	page.click('id=projectsdomains')
	page.click('id=modal')
	page.fill('id=id_projectsgroup_name', domainName)
	page.fill('id=id_projectsgroup_department', department)
	page.click('id=save')
	domains = re.findall(r'id="domain([0-9]+)"', page.content(), re.MULTILINE)
	for id in domains:		
		domain = page.locator('id=domain'+id).inner_text()
		if domain == domainName:
			break
	assert domain == domainName, "Step "+str(step)+": not Ok"
	# 5 | Create a test project inside the new domain
	step = 5
	page.click('id=domain'+id)
	assert page.locator('id=page_title').inner_text() == domainName, "Step "+str(step)+": not Ok"
	projectName = "Project Test"
	page.click('id=newProjectModal')
	page.fill('id=id_project_name', projectName)
	page.fill('id=id_project_internal_id', 'TST')
	page.select_option('id=id_project_parent_group', id)
	page.select_option('id=id_project_lc_status', "in_dev")
	page.click('id=save')
	projects = re.findall(r'id="project([0-9]+)"', page.content(), re.MULTILINE)
	for projectId in projects:		
		project = page.locator('id=project'+projectId).inner_text()
		if project == projectName:
			break
	assert project == projectName, "Step "+str(step)+": not Ok"
	# 6 | Create a risk analysis inside the test project
	step = 6
	page.click('id=project'+projectId)
	assert page.locator('id=page_title').inner_text() == projectName, "Step "+str(step)+": not Ok"
	page.click('id=newRiskAnalysisModal')
	page.select_option('id=id_analysis_project', projectId)
	page.select_option('id=id_analysis_auditor', label="root")
	page.select_option('id=id_analysis_rating_matrix', "critical")
	page.fill('id=id_analysis_comments', "Test")
	page.set_checked('id=id_is_draft', checked=False)
	page.click('id=analysis_save')
	analysisName = "Project Test, version 0.1"
	analyses = re.findall(r'id="analysis([0-9]+)"', page.content(), re.MULTILINE)
	for analysisId in analyses:		
		analysis = page.locator('id=analysis'+analysisId).inner_text()
		if analysisName in analysis:
			break
	assert analysisName in analysis, "Step "+str(step)+": not Ok"
	# 7 | Create a risk scenario inside the test risk analysis
	step = 7
	page.click('id=analysis'+analysisId)
	assert page.locator('id=page_title').inner_text() == "RA-"+ analysisId + ": " + analysisName, "Step "+str(step)+": not Ok"
	page.click("id=newRiskScenario")
	assert page.locator('id=page_title').inner_text() == "New risk scenario", "Step "+str(step)+": not Ok"
	page.fill('id=id_riskscenario_title', 'Scenario Test')
	page.select_option('id=id_riskscenario_threat', label=threatName)
	page.fill('id=id_riskscenario_scenario', 'scenario test')
	page.select_option('id=id_riskscenario_current_impact', 'M')
	page.select_option('id=id_riskscenario_current_proba', 'L')
	page.fill('id=id_riskscenario_existing_measures', 'test measures')
	page.select_option('id=id_riskscenario_residual_proba', 'VL')
	page.select_option('id=id_riskscenario_residual_impact', 'M')
	page.select_option('id=id_riskscenario_treatment', 'mitigated')
	page.fill('id=id_riskscenario_comments', 'test comments')
	page.click('id=submit')
	scenarioName = 'Scenario Test'
	scenarios = re.findall(r'id="scenario([0-9]+)"', page.content(), re.MULTILINE)
	for scenarioId in scenarios:		
		scenario = page.locator('id=scenario'+scenarioId).inner_text()
		if scenarioName in scenario:
			break
	assert scenarioName in scenario, "Step "+str(step)+": not Ok"
	# 8 | Create a mesure in side the test scenario
	step = 8
	page.click('id=scenario'+scenarioId)
	assert page.locator('id=page_title').inner_text() == "Project Test: Scenario Test", "Step "+str(step)+": not Ok"
	page.click('id=newMeasures')
	page.select_option('id=id_security_function_risk_scenario', label='Project Test: Scenario Test')
	page.select_option('id=id_security_function_security_function', label='SecurityFunction Test')
	page.fill('id=id_security_function_description', 'test description')
	page.select_option('id=id_security_function_type', 'technical')
	page.select_option('id=id_security_function_status', 'in_progress')
	page.type('id=id_security_function_eta', '01012023')
	page.select_option('id=id_security_function_effort', 'M')
	page.click('id=save')
	# clear |
	page.click('id=projectsdomains')
	page.click('id=action'+id)
	page.click('id=deleteAction'+id)
	page.click('id=delete'+id)
	page.click('id=threats')
	page.click('id=action'+threatId)
	page.click('id=deleteAction'+threatId)
	page.click('id=delete'+threatId)
	page.click('id=securityFunctions')
	page.click('id=action'+functionId)
	page.click('id=deleteAction'+functionId)
	page.click('id=delete'+functionId)