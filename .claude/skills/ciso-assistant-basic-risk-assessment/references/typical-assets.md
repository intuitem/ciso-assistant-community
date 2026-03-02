# Typical Assets by Industry and Organization Size

Use this reference when users cannot identify their assets. Suggest relevant assets based on context gathered during the assessment.

## Primary Assets (PR) - Business Data and Processes

### Universal (All Industries)
- Customer/Client Personal Data
- Employee Personal Data
- Financial Records
- Intellectual Property / Trade Secrets
- Business Contracts and Agreements
- Corporate Communications (Email)

### Healthcare
- Patient Health Records (PHI/EHR)
- Medical Device Data
- Clinical Trial Data
- Prescription/Medication Records
- Insurance Claims Data

### Financial Services
- Transaction Records
- Account Information
- Trading Algorithms
- Credit Scoring Models
- Regulatory Reports
- Customer Financial Profiles

### E-commerce / Retail
- Payment Card Data
- Customer Purchase History
- Inventory Data
- Pricing Information
- Supplier Contracts

### Technology / SaaS
- Source Code Repositories
- API Keys and Secrets
- Customer Usage Data
- Product Roadmaps
- Service Configuration Data

### Manufacturing
- Product Designs / CAD Files
- Manufacturing Processes
- Supply Chain Data
- Quality Control Records
- Equipment Maintenance Logs

### Government / Public Sector
- Citizen Records
- Policy Documents
- Classified Information
- Grant/Funding Data
- Regulatory Enforcement Data

## Supporting Assets (SP) - Infrastructure

### By Organization Size

#### Small (1-50 employees)
- Cloud Email (Microsoft 365 / Google Workspace)
- Cloud Storage (OneDrive / Google Drive / Dropbox)
- Accounting Software
- CRM System
- Company Website
- Employee Laptops/Workstations
- Mobile Devices (BYOD)
- Network Router/Firewall

#### Medium (50-500 employees)
*All from Small, plus:*
- ERP System
- HR Information System (HRIS)
- Cloud Infrastructure (AWS / Azure / GCP)
- VPN / Remote Access
- Identity Provider (SSO)
- Backup Systems
- Database Servers
- Development/Test Environments
- Endpoint Protection Platform
- Security Monitoring Tools

#### Large (500+ employees)
*All from Medium, plus:*
- Data Center Infrastructure
- Mainframe Systems
- SIEM Platform
- Data Lake / Data Warehouse
- API Gateway
- Container Orchestration (Kubernetes)
- CI/CD Pipeline
- Service Desk / ITSM Platform
- Privileged Access Management
- Network Segmentation Infrastructure

### SaaS-Heavy Organizations
- Identity Provider (Okta, Azure AD)
- Collaboration Tools (Slack, Teams)
- Project Management (Jira, Asana)
- Design Tools (Figma, Adobe CC)
- Analytics Platforms
- Marketing Automation
- Customer Support Platform
- Video Conferencing
- Document Signing Services

### Regulated Environment Additions
- Audit Trail / Logging Systems
- Compliance Management Platform
- Data Loss Prevention (DLP)
- Encryption Key Management
- Access Review Systems
- Policy Management Platform

## Threat-Asset Relevance Matrix

Use this to suggest which threats from the INTUITEM Common Catalog are most relevant to specific assets:

| Asset Category | Most Relevant Threats (ref_id) |
|---------------|-------------------------------|
| Customer Data | ICT-001, ICT-002, ICT-005, ICT-019 |
| Source Code | ICT-003, ICT-004, ICT-005, ICT-019 |
| Cloud Infrastructure | ICT-001, ICT-015, ICT-018, ICT-022 |
| Employee Devices | ICT-002, ICT-009, ICT-017, ICT-020 |
| Web Applications | ICT-004, ICT-007, ICT-012, ICT-018 |
| Financial Data | ICT-001, ICT-002, ICT-005, ICT-013 |
| IoT/OT Systems | ICT-016, ICT-003, ICT-022 |
| AI/ML Systems | ICT-014, ICT-003, ICT-019 |
| Third-Party Services | ICT-003, ICT-015, ICT-022 |
| All Assets | ICT-008, ICT-021, ICT-023 |

## Threat Catalog Reference

The built-in threat catalog (`urn:intuitem:risk:library:intuitem-common-catalog`) contains:

| Ref ID | Threat Name |
|--------|-------------|
| ICT-001 | Ransomware |
| ICT-002 | Phishing and Spear Phishing |
| ICT-003 | Third-Party / Supply Chain Attacks |
| ICT-004 | Zero-Day Exploits |
| ICT-005 | Insider Threats |
| ICT-006 | Advanced Persistent Threats (APTs) |
| ICT-007 | DoS / DDoS |
| ICT-008 | Social Engineering |
| ICT-009 | Malware and Spyware |
| ICT-010 | Cryptojacking |
| ICT-011 | DNS Spoofing and Hijacking |
| ICT-012 | Password Attacks (Brute Force) |
| ICT-013 | Deepfake and Synthetic Identity Fraud |
| ICT-014 | AI Threats and Model Manipulation |
| ICT-015 | Cloud Security Threats |
| ICT-016 | IoT Vulnerabilities |
| ICT-017 | Mobile Device Threats |
| ICT-018 | API Security Threats |
| ICT-019 | Data Breach, Leak and Shadow IT |
| ICT-020 | Physical Security Threats |
| ICT-021 | Disinformation and Reputation Attacks |
| ICT-022 | System Outage (Failures, Bugs, Errors) |
| ICT-023 | Regulatory Non-Compliance |
