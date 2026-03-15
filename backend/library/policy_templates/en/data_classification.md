---
title: Data Classification Policy
description: Framework for classifying and handling organizational data based on sensitivity
---

# Data Classification Policy

## 1. Purpose

This policy establishes a framework for classifying organizational data based on its sensitivity, value, and criticality. Proper classification ensures that data receives an appropriate level of protection throughout its lifecycle.

## 2. Scope

This policy applies to all data created, collected, processed, stored, or transmitted by or on behalf of the organization, regardless of format (digital or physical) or storage location.

## 3. Classification Levels

### 3.1 Public
- Information intended for public disclosure
- No adverse impact if disclosed
- Examples: marketing materials, published reports, public website content

### 3.2 Internal
- Information intended for general use within the organization
- Minor impact if disclosed externally
- Examples: internal announcements, organizational charts, general procedures

### 3.3 Confidential
- Sensitive business information requiring restricted access
- Significant impact if disclosed to unauthorized parties
- Examples: financial data, business plans, employee records, contracts

### 3.4 Restricted
- Highly sensitive information requiring the strictest controls
- Severe impact if disclosed, including legal, financial, or reputational harm
- Examples: trade secrets, PII/PHI, authentication credentials, encryption keys

## 4. Classification Responsibilities

### 4.1 Data Owners
- Classify data based on the definitions in this policy
- Review classifications periodically (at least annually)
- Approve access to data under their ownership
- Ensure appropriate handling throughout the data lifecycle

### 4.2 Data Custodians
- Implement technical controls appropriate to the classification level
- Manage storage, backup, and recovery of classified data
- Report any unauthorized access or handling of classified data

### 4.3 All Users
- Handle data according to its classification level
- Report any suspected misclassification or mishandling
- Apply appropriate labels and markings to data

## 5. Handling Requirements

| Requirement | Public | Internal | Confidential | Restricted |
|------------|--------|----------|--------------|------------|
| Encryption at rest | Optional | Optional | Required | Required |
| Encryption in transit | Optional | Recommended | Required | Required |
| Access control | None | Basic | Role-based | Need-to-know |
| Labeling | Not required | Recommended | Required | Required |
| Sharing externally | Permitted | With caution | With NDA/approval | Prohibited without executive approval |
| Disposal | Standard | Standard | Secure deletion | Certified destruction |

## 6. Labeling and Marking

- Confidential and Restricted data shall be clearly labeled with its classification
- Electronic documents shall include classification in the header or footer
- Emails containing Confidential or Restricted data shall include classification in the subject line
- Physical documents shall be marked on each page

## 7. Data Lifecycle

### 7.1 Creation
- Data shall be classified at the point of creation
- Default classification is Internal unless otherwise determined

### 7.2 Storage
- Data shall be stored in approved locations appropriate for its classification
- Restricted data shall not be stored on portable devices without encryption

### 7.3 Transmission
- Data shall be transmitted using methods appropriate for its classification
- Confidential and Restricted data shall be encrypted during transmission

### 7.4 Retention
- Data shall be retained in accordance with the data retention schedule
- Classification may change over time; periodic reviews shall address this

### 7.5 Disposal
- Data shall be disposed of using methods appropriate for its classification
- Restricted data shall be disposed of using certified destruction methods
- Disposal records shall be maintained

## 8. Exceptions

Exceptions to this policy must be approved in writing by the Information Security Officer and documented with:
- Business justification
- Risk assessment
- Compensating controls
- Review date

## 9. Policy Review

This policy shall be reviewed at least annually. Classification levels and handling requirements shall be updated to reflect changes in regulatory requirements, business needs, or threat landscape.
