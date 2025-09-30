from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Union
import httpx
import requests
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
import uvicorn
import logging
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(".mcp.env")

app = FastAPI(title="CISO Assistant MCP Web Wrapper", version="1.0.0")

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Configuration
API_URL = os.getenv("API_URL", "")
TOKEN = os.getenv("TOKEN", "")
VERIFY_CERTIFICATE = os.getenv("VERIFY_CERTIFICATE", "true").lower() in (
    "true", "1", "yes", "on"
)

# Pydantic models for request/response
class MCPMessage(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Dict] = None
    error: Optional[Dict] = None

class CISOAssistantMCPWrapper:
    """Wrapper class to handle MCP-like functionality via web API"""
    
    def __init__(self):
        self.tools = [
            {
                "name": "get_risk_scenarios", 
                "description": "Get risks scenarios from CISO Assistant Risk Registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_applied_controls",
                "description": "Get applied controls from CISO Assistant combined action plan", 
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_audits_progress",
                "description": "Get the audits progress from CISO Assistant compliance engine",
                "inputSchema": {
                    "type": "object", 
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_evidence",
                "description": "Get evidence from CISO Assistant Evidence Registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_evidence_by_id",
                "description": "Get specific evidence by ID including attached documents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "evidence_id": {
                            "type": "string",
                            "description": "The UUID of the evidence to retrieve"
                        }
                    },
                    "required": ["evidence_id"]
                }
            },
            {
                "name": "get_evidence_with_ids",
                "description": "Get evidence with their IDs from CISO Assistant Evidence Registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "review_evidence_by_id",
                "description": "Review specific evidence by ID including document analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "evidence_id": {
                            "type": "string",
                            "description": "The UUID of the evidence to review"
                        }
                    },
                    "required": ["evidence_id"]
                }
            },
            {
                "name": "review_all_evidence",
                "description": "Review all evidence with detailed analysis including attached documents",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_policies",
                "description": "Get policies from CISO Assistant Policy Registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_policies_with_ids",
                "description": "Get policies with their IDs from CISO Assistant Policy Registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "review_policy_by_id",
                "description": "Review a specific policy by ID including policy document if available",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "policy_id": {
                            "type": "string",
                            "description": "The UUID of the policy to review"
                        }
                    },
                    "required": ["policy_id"]
                }
            },
            {
                "name": "review_all_policies",
                "description": "Review all policies with detailed analysis including policy documents",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
    
    async def get_risk_scenarios(self):
        """Get risks scenarios - Query CISO Assistant Risk Registry"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/risk-scenarios/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                    
                if not data.get("results"):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "No risk scenarios found"
                            }
                        ]
                    }
                    
                scenarios = [
                    f"|{rs.get('name', 'N/A')}|{rs.get('description', 'N/A')}|{rs.get('current_level', 'N/A')}|{rs.get('residual_level', 'N/A')}|{rs.get('folder', 'N/A')}|"
                    for rs in data["results"]
                ]
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "|name|description|current_level|residual_level|domain|\n"
                                + "|---|---|---|---|---|\n"
                                + "\n".join(scenarios)
                            )
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"Error in get_risk_scenarios: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

    async def get_policies(self):
        """Get policies - Query CISO Assistant Policy Registry"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/policies/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                    
                if not data.get("results"):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "No policies found"
                            }
                        ]
                    }
                    
                policies = [
                    f"|{rs.get('name', 'N/A')}|{rs.get('description', 'N/A')}|{rs.get('start_date', 'N/A')}|{rs.get('expiry_date', 'N/A')}|{rs.get('status', 'N/A')}|{rs.get('is_published', 'N/A')}|{rs.get('reference_control', 'N/A')}|{rs.get('priority', 'N/A')}|{rs.get('category', 'N/A')}|{rs.get('evidences', 'N/A')}|{rs.get('control_impact', 'N/A')}|{rs.get('cost', 'N/A')}|{rs.get('assets', 'N/A')}|{rs.get('ranking_score', 'N/A')}|{rs.get('state', 'N/A')}|{rs.get('findings', 'N/A')}|"
                    for rs in data["results"]
                ]
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "|name|description|start_date|expiry_date|status|is_published|reference_control|priority|category|evidences|control_impact|cost|assets|ranking_score|state|findings|\n"
                                + "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
                                + "\n".join(policies)
                            )
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"Error in get_policies: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

    async def get_policies_with_ids(self):
        """Get policies with their IDs from CISO Assistant Policy Registry"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/policies/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                    
                if not data.get("results"):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "No policies found"
                            }
                        ]
                    }
                    
                policies = [
                    f"|{rs.get('id', 'N/A')}|{rs.get('name', 'N/A')}|{rs.get('description', 'N/A')}|{rs.get('start_date', 'N/A')}|{rs.get('expiry_date', 'N/A')}|{rs.get('status', 'N/A')}|{rs.get('is_published', 'N/A')}|"
                    for rs in data["results"]
                ]
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "|id|name|description|start_date|expiry_date|status|is_published|\n"
                                + "|---|---|---|---|---|---|---|\n"
                                + "\n".join(policies)
                            )
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"Error in get_policies_with_ids: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

    async def review_policy_by_id(self, policy_id: str):
        """Review a specific policy by ID including policy document if available"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/policies/{policy_id}/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 404:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Policy with ID {policy_id} not found"
                            }
                        ]
                    }
                elif response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                
                policy_data = response.json()
                
                # Format the policy review
                review_text = self._format_policy_review(policy_data)
                
                # Try to get associated policy document if available
                document_text = ""
                if policy_data.get('attachment'):
                    document_text = await self._get_policy_document(policy_data['attachment'])
                
                full_review = review_text
                if document_text:
                    full_review += f"\n\n**Policy Document Content:**\n{document_text}"
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": full_review
                        }
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error in review_policy_by_id: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

    async def review_all_policies(self):
        """Review all policies with detailed analysis including policy documents"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/policies/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                    
                if not data.get("results"):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "No policies found"
                            }
                        ]
                    }
                
                # Review each policy in detail
                policy_reviews = []
                for policy in data["results"]:
                    policy_id = policy.get('id')
                    if policy_id:
                        # Get detailed policy information
                        detailed_response = await client.get(f"{API_URL}/policies/{policy_id}/", headers=headers)
                        if detailed_response.status_code == 200:
                            detailed_policy = detailed_response.json()
                            review = self._format_policy_review(detailed_policy)
                            
                            # Try to get policy document if available
                            document_text = ""
                            if detailed_policy.get('attachment'):
                                document_text = await self._get_policy_document(detailed_policy['attachment'])
                            
                            if document_text:
                                review += f"\n**Document Analysis:** {document_text[:500]}{'...' if len(document_text) > 500 else ''}"
                            
                            policy_reviews.append(review)
                
                full_review = "# Comprehensive Policy Review\n\n" + "\n\n---\n\n".join(policy_reviews)
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": full_review
                        }
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error in review_all_policies: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

    def _format_policy_review(self, policy_data: dict) -> str:
        """Format a comprehensive policy review"""
        name = policy_data.get('name', 'Unnamed Policy')
        description = policy_data.get('description', 'No description provided')
        status = policy_data.get('status', 'Status not specified')
        start_date = policy_data.get('start_date', 'Not specified')
        expiry_date = policy_data.get('expiry_date', 'Not specified')
        is_published = policy_data.get('is_published', False)
        priority = policy_data.get('priority', 'Not specified')
        category = policy_data.get('category', 'Not specified')
        
        # Assessment and recommendations
        issues = []
        recommendations = []
        
        # Check for lifecycle management issues
        if not start_date or start_date == 'Not specified':
            issues.append("Missing start date")
            recommendations.append("Set a clear policy effective date")
        
        if not expiry_date or expiry_date == 'Not specified':
            issues.append("Missing expiry/review date")
            recommendations.append("Establish regular review cycles (typically annual or bi-annual)")
        
        if status == '--' or status == 'Status not specified':
            issues.append("Undefined policy status")
            recommendations.append("Activate policy or clearly define its current state")
        
        if not description or description == 'No description provided':
            issues.append("Missing policy description")
            recommendations.append("Add clear policy description and purpose")
        
        if not is_published:
            issues.append("Policy not published")
            recommendations.append("Publish policy to make it available to stakeholders")
        
        # Format the review
        review = f"## {name}\n\n"
        review += f"**Description:** {description}\n"
        review += f"**Status:** {status}\n"
        review += f"**Effective Date:** {start_date}\n"
        review += f"**Expiry/Review Date:** {expiry_date}\n"
        review += f"**Published:** {'Yes' if is_published else 'No'}\n"
        review += f"**Priority:** {priority}\n"
        review += f"**Category:** {category}\n\n"
        
        if issues:
            review += "**Issues Identified:**\n"
            for issue in issues:
                review += f"- {issue}\n"
            review += "\n"
        
        if recommendations:
            review += "**Recommendations:**\n"
            for rec in recommendations:
                review += f"- {rec}\n"
            review += "\n"
        
        # Overall assessment
        if len(issues) == 0:
            review += "**Overall Assessment:** ✅ Policy appears well-managed\n"
        elif len(issues) <= 2:
            review += "**Overall Assessment:** ⚠️ Minor improvements needed\n"
        else:
            review += "**Overall Assessment:** ❌ Significant improvements required\n"
        
        return review

    async def _get_policy_document(self, attachment_data: dict) -> str:
        """Attempt to retrieve and analyze policy document content"""
        try:
            if isinstance(attachment_data, dict) and 'url' in attachment_data:
                # This would need to be implemented based on how CISO Assistant stores documents
                # For now, return a placeholder indicating document is available
                return f"Policy document available: {attachment_data.get('name', 'Document')}"
            return ""
        except Exception as e:
            logger.error(f"Error retrieving policy document: {str(e)}")
            return ""

    async def get_evidence(self):
        """Get evidence - Query CISO Assistant Evidence Registry"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/evidences/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                    
                if not data.get("results"):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "No evidence found"
                            }
                        ]
                    }
                    
                evidences = [
                    f"|{rs.get('name', 'N/A')}|{rs.get('description', 'N/A')}|{rs.get('is_published', 'N/A')}|{rs.get('requirement_assessments', 'N/A')}|{rs.get('applied_controls', 'N/A')}|{rs.get('filtering_labels', 'N/A')}|"
                    for rs in data["results"]
                ]
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "|name|description|is_published|requirement_assessments|applied_controls|filtering_labels|\n"
                                + "|---|---|---|---|---|---|\n"
                                + "\n".join(evidences)
                            )
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"Error in get_evidence: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

    async def get_evidence_with_ids(self):
        """Get evidence with their IDs from CISO Assistant Evidence Registry"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/evidences/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                    
                if not data.get("results"):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "No evidence found"
                            }
                        ]
                    }
                    
                evidences = [
                    f"|{rs.get('id', 'N/A')}|{rs.get('name', 'N/A')}|{rs.get('description', 'N/A')}|{rs.get('is_published', 'N/A')}|{rs.get('created_at', 'N/A')}|{rs.get('updated_at', 'N/A')}|{len(rs.get('applied_controls', []))}|{len(rs.get('requirement_assessments', []))}|"
                    for rs in data["results"]
                ]
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "|id|name|description|is_published|created_at|updated_at|linked_controls|linked_requirements|\n"
                                + "|---|---|---|---|---|---|---|---|\n"
                                + "\n".join(evidences)
                            )
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"Error in get_evidence_with_ids: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

    async def get_evidence_by_id(self, evidence_id: str):
        """Get specific evidence by ID including attached documents"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/evidences/{evidence_id}/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 404:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Evidence with ID {evidence_id} not found"
                            }
                        ]
                    }
                elif response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                
                evidence_data = response.json()
                
                # Format evidence details
                result_text = self._format_evidence_details(evidence_data)
                
                # Try to get attached document content
                document_content = await self._get_evidence_document_content(evidence_data, client, headers)
                if document_content:
                    result_text += f"\n\n**Document Content:**\n{document_content}"
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error in get_evidence_by_id: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

    async def review_evidence_by_id(self, evidence_id: str):
        """Review specific evidence by ID including document analysis"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/evidences/{evidence_id}/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 404:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Evidence with ID {evidence_id} not found"
                            }
                        ]
                    }
                elif response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                
                evidence_data = response.json()
                
                # Format comprehensive evidence review
                review_text = self._format_evidence_review(evidence_data)
                
                # Get document analysis
                document_analysis = await self._analyze_evidence_document(evidence_data, client, headers)
                if document_analysis:
                    review_text += f"\n\n**Document Analysis:**\n{document_analysis}"
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": review_text
                        }
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error in review_evidence_by_id: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

    async def review_all_evidence(self):
        """Review all evidence with detailed analysis including attached documents"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/evidences/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                    
                if not data.get("results"):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "No evidence found"
                            }
                        ]
                    }
                
                # Review each evidence item in detail
                evidence_reviews = []
                for evidence in data["results"]:
                    evidence_id = evidence.get('id')
                    if evidence_id:
                        # Get detailed evidence information
                        detailed_response = await client.get(f"{API_URL}/evidences/{evidence_id}/", headers=headers)
                        if detailed_response.status_code == 200:
                            detailed_evidence = detailed_response.json()
                            review = self._format_evidence_review(detailed_evidence)
                            
                            # Try to get document analysis if available
                            document_analysis = await self._analyze_evidence_document(detailed_evidence, client, headers)
                            if document_analysis:
                                review += f"\n**Document Summary:** {document_analysis[:300]}{'...' if len(document_analysis) > 300 else ''}"
                            
                            evidence_reviews.append(review)
                
                full_review = "# Comprehensive Evidence Review\n\n" + "\n\n---\n\n".join(evidence_reviews)
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": full_review
                        }
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error in review_all_evidence: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

    def _format_evidence_details(self, evidence_data: dict) -> str:
        """Format evidence details for display"""
        name = evidence_data.get('name', 'Unnamed Evidence')
        description = evidence_data.get('description', 'No description provided')
        is_published = evidence_data.get('is_published', False)
        created_at = evidence_data.get('created_at', 'Unknown')
        updated_at = evidence_data.get('updated_at', 'Unknown')
        
        # Get linked controls and requirements
        applied_controls = evidence_data.get('applied_controls', [])
        requirement_assessments = evidence_data.get('requirement_assessments', [])
        
        # Get attachment info
        attachment = evidence_data.get('attachment')
        
        result = f"## Evidence: {name}\n\n"
        result += f"**Description:** {description}\n"
        result += f"**Published:** {'Yes' if is_published else 'No'}\n"
        result += f"**Created:** {created_at}\n"
        result += f"**Updated:** {updated_at}\n"
        result += f"**Linked Controls:** {len(applied_controls)}\n"
        result += f"**Linked Requirements:** {len(requirement_assessments)}\n"
        
        if attachment:
            result += f"**Document Attached:** Yes - {attachment.get('name', 'Unknown filename')}\n"
            result += f"**File Size:** {attachment.get('size', 'Unknown')} bytes\n"
        else:
            result += f"**Document Attached:** No\n"
        
        if applied_controls:
            result += f"\n**Applied Controls:**\n"
            for control in applied_controls[:5]:  # Show first 5
                if isinstance(control, dict):
                    result += f"- {control.get('str', control.get('name', 'Unknown'))}\n"
                else:
                    result += f"- {str(control)}\n"
            if len(applied_controls) > 5:
                result += f"... and {len(applied_controls) - 5} more\n"
        
        return result

    def _format_evidence_review(self, evidence_data: dict) -> str:
        """Format a comprehensive evidence review"""
        name = evidence_data.get('name', 'Unnamed Evidence')
        description = evidence_data.get('description', 'No description provided')
        is_published = evidence_data.get('is_published', False)
        created_at = evidence_data.get('created_at', 'Unknown')
        updated_at = evidence_data.get('updated_at', 'Unknown')
        
        # Get linked data
        applied_controls = evidence_data.get('applied_controls', [])
        requirement_assessments = evidence_data.get('requirement_assessments', [])
        attachment = evidence_data.get('attachment')
        
        # Assessment and recommendations
        issues = []
        recommendations = []
        strengths = []
        
        # Check for evidence quality issues
        if not description or description == 'No description provided':
            issues.append("Missing evidence description")
            recommendations.append("Add clear description of what this evidence demonstrates")
        
        if not is_published:
            issues.append("Evidence not published")
            recommendations.append("Publish evidence to make it available for compliance assessments")
        
        if not attachment:
            issues.append("No document attached")
            recommendations.append("Attach supporting documentation to substantiate the evidence")
        else:
            strengths.append("Has attached documentation")
        
        if not applied_controls and not requirement_assessments:
            issues.append("Evidence not linked to any controls or requirements")
            recommendations.append("Link evidence to relevant controls or compliance requirements")
        else:
            if applied_controls:
                strengths.append(f"Linked to {len(applied_controls)} control(s)")
            if requirement_assessments:
                strengths.append(f"Linked to {len(requirement_assessments)} requirement(s)")
        
        # Check for freshness
        if updated_at and updated_at != 'Unknown':
            try:
                # Basic freshness check (this would need proper date parsing)
                if '2024' not in str(updated_at) and '2025' not in str(updated_at):
                    issues.append("Evidence may be outdated")
                    recommendations.append("Review and update evidence documentation")
                else:
                    strengths.append("Recently updated")
            except:
                pass
        
        # Format the review
        review = f"## {name}\n\n"
        review += f"**Description:** {description}\n"
        review += f"**Status:** {'Published' if is_published else 'Draft'}\n"
        review += f"**Created:** {created_at}\n"
        review += f"**Last Updated:** {updated_at}\n"
        review += f"**Controls Linked:** {len(applied_controls)}\n"
        review += f"**Requirements Linked:** {len(requirement_assessments)}\n"
        review += f"**Document Attached:** {'Yes' if attachment else 'No'}\n\n"
        
        if strengths:
            review += "**Strengths:**\n"
            for strength in strengths:
                review += f"- {strength}\n"
            review += "\n"
        
        if issues:
            review += "**Issues Identified:**\n"
            for issue in issues:
                review += f"- {issue}\n"
            review += "\n"
        
        if recommendations:
            review += "**Recommendations:**\n"
            for rec in recommendations:
                review += f"- {rec}\n"
            review += "\n"
        
        # Overall assessment
        if len(issues) == 0:
            review += "**Overall Assessment:** ✅ Evidence appears well-documented and linked\n"
        elif len(issues) <= 2:
            review += "**Overall Assessment:** ⚠️ Minor improvements needed\n"
        else:
            review += "**Overall Assessment:** ❌ Significant improvements required\n"
        
        return review

    async def _get_evidence_document_content(self, evidence_data: dict, client: httpx.AsyncClient, headers: dict) -> str:
        """Retrieve and return evidence document content"""
        try:
            attachment = evidence_data.get('attachment')
            if not attachment:
                return ""
            
            # Check if attachment has a URL or file reference
            if isinstance(attachment, dict):
                file_url = attachment.get('url') or attachment.get('file')
                file_name = attachment.get('name', 'Unknown')
                
                if file_url:
                    # Try to fetch the document content
                    try:
                        # Handle relative URLs
                        if file_url.startswith('/'):
                            file_url = f"{API_URL.rstrip('/')}{file_url}"
                        elif not file_url.startswith('http'):
                            file_url = f"{API_URL.rstrip('/')}/{file_url}"
                        
                        doc_response = await client.get(file_url, headers=headers)
                        if doc_response.status_code == 200:
                            content_type = doc_response.headers.get('content-type', '').lower()
                            
                            if 'text' in content_type or 'json' in content_type:
                                return doc_response.text[:2000]  # Limit to first 2000 chars
                            elif 'pdf' in content_type:
                                return f"PDF document: {file_name} ({attachment.get('size', 'Unknown')} bytes)"
                            elif any(img_type in content_type for img_type in ['image', 'jpeg', 'png', 'gif']):
                                return f"Image file: {file_name} ({attachment.get('size', 'Unknown')} bytes)"
                            else:
                                return f"Binary document: {file_name} (Type: {content_type}, Size: {attachment.get('size', 'Unknown')} bytes)"
                        else:
                            return f"Document available but could not be retrieved: {file_name}"
                    except Exception as e:
                        logger.error(f"Error fetching document content: {str(e)}")
                        return f"Document: {file_name} (Content unavailable: {str(e)})"
                else:
                    return f"Document reference: {file_name}"
            
            return ""
        except Exception as e:
            logger.error(f"Error processing evidence document: {str(e)}")
            return f"Error accessing document: {str(e)}"

    async def _analyze_evidence_document(self, evidence_data: dict, client: httpx.AsyncClient, headers: dict) -> str:
        """Analyze evidence document and provide insights"""
        try:
            document_content = await self._get_evidence_document_content(evidence_data, client, headers)
            if not document_content:
                return "No document available for analysis"
            
            # Basic document analysis
            attachment = evidence_data.get('attachment', {})
            file_name = attachment.get('name', 'Unknown')
            file_size = attachment.get('size', 0)
            
            analysis = f"**Document:** {file_name}\n"
            analysis += f"**Size:** {file_size} bytes\n"
            
            if len(document_content) < 100:
                analysis += f"**Content Preview:** {document_content}\n"
            else:
                analysis += f"**Content Preview:** {document_content[:200]}...\n"
            
            # Basic content analysis
            if 'policy' in document_content.lower():
                analysis += "**Content Type:** Appears to be policy-related documentation\n"
            elif 'procedure' in document_content.lower():
                analysis += "**Content Type:** Appears to be procedural documentation\n"
            elif 'audit' in document_content.lower():
                analysis += "**Content Type:** Appears to be audit-related documentation\n"
            elif 'config' in document_content.lower():
                analysis += "**Content Type:** Appears to be configuration documentation\n"
            else:
                analysis += "**Content Type:** General documentation\n"
            
            # Check for key compliance indicators
            compliance_keywords = ['iso 27001', 'nist', 'gdpr', 'compliance', 'security control', 'risk assessment']
            found_keywords = [kw for kw in compliance_keywords if kw in document_content.lower()]
            if found_keywords:
                analysis += f"**Compliance Indicators:** {', '.join(found_keywords)}\n"
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing evidence document: {str(e)}")
            return f"Error during document analysis: {str(e)}"

    async def get_applied_controls(self):
        """Get applied controls - Query CISO Assistant combined action plan"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/applied-controls/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                    
                if not data.get("results"):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "No applied controls found"
                            }
                        ]
                    }
                    
                items = []
                for item in data["results"]:
                    folder_str = "N/A"
                    if item.get('folder') and isinstance(item['folder'], dict):
                        folder_str = item['folder'].get('str', 'N/A')
                    elif item.get('folder'):
                        folder_str = str(item['folder'])
                    
                    items.append(
                        f"|{item.get('name', 'N/A')}|{item.get('description', 'N/A')}|{item.get('status', 'N/A')}|{item.get('eta', 'N/A')}|{folder_str}|"
                    )
                
                return {
                    "content": [
                        {
                            "type": "text", 
                            "text": (
                                "|name|description|status|eta|domain|\n"
                                + "|---|---|---|---|---|\n"
                                + "\n".join(items)
                            )
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"Error in get_applied_controls: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }
    
    async def get_audits_progress(self):
        """Get the audits progress - Query CISO Assistant compliance engine for audits progress"""
        headers = {"Authorization": f"Token {TOKEN}"}
        url = f"{API_URL}/compliance-assessments/"
        
        try:
            async with httpx.AsyncClient(verify=VERIFY_CERTIFICATE) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if response.status_code != 200:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Check credentials or API endpoint. Status: {response.status_code}"
                            }
                        ]
                    }
                    
                if not data.get("results"):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "No audits found"
                            }
                        ]
                    }
                    
                items = []
                for item in data["results"]:
                    framework_str = "N/A"
                    folder_str = "N/A"
                    
                    if item.get('framework') and isinstance(item['framework'], dict):
                        framework_str = item['framework'].get('str', 'N/A')
                    elif item.get('framework'):
                        framework_str = str(item['framework'])
                    
                    if item.get('folder') and isinstance(item['folder'], dict):
                        folder_str = item['folder'].get('str', 'N/A')
                    elif item.get('folder'):
                        folder_str = str(item['folder'])
                    
                    items.append(
                        f"|{item.get('name', 'N/A')}|{framework_str}|{item.get('status', 'N/A')}|{item.get('progress', 'N/A')}|{folder_str}|"
                    )
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "|name|framework|status|progress|domain|\n"
                                + "|---|---|---|---|---|\n"
                                + "\n".join(items)
                            )
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"Error in get_audits_progress: {str(e)}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request failed: {str(e)}"
                    }
                ]
            }

# Initialize the wrapper
mcp_wrapper = CISOAssistantMCPWrapper()

# FIXED: Add POST endpoint for /sse to handle MCP client connection
@app.post("/sse")
async def sse_post_endpoint(request: Request):
    """Handle POST requests to /sse (MCP client connection)"""
    try:
        # Get raw JSON to handle different ID types
        body = await request.body()
        message_data = json.loads(body.decode('utf-8'))
        
        logger.info(f"Received SSE POST message: {message_data}")
        
        method = message_data.get('method')
        message_id = message_data.get('id')
        params = message_data.get('params', {})
        
        if method == 'initialize':
            # Return server capabilities
            response = {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "ciso-assistant",
                        "version": "1.0.0"
                    }
                }
            }
            logger.info(f"Sending initialize response: {response}")
            return JSONResponse(content=response)
        
        elif method == 'tools/list':
            # Return available tools
            response = {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "tools": mcp_wrapper.tools
                }
            }
            logger.info(f"Sending tools list: {response}")
            return JSONResponse(content=response)
        
        elif method == 'tools/call':
            # Execute tool
            tool_name = params.get('name')
            tool_arguments = params.get('arguments', {})
            logger.info(f"Executing tool: {tool_name} with arguments: {tool_arguments}")
            
            if hasattr(mcp_wrapper, tool_name):
                # Execute the corresponding method
                method_func = getattr(mcp_wrapper, tool_name)
                
                # Check if the method requires arguments
                if tool_arguments:
                    result = await method_func(**tool_arguments)
                else:
                    result = await method_func()
                
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": result
                }
                logger.info(f"Tool execution result: {response}")
                return JSONResponse(content=response)
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
                return JSONResponse(content=response)
        
        else:
            response = {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown method: {method}"
                }
            }
            return JSONResponse(content=response)
            
    except Exception as e:
        logger.error(f"Error handling SSE POST message: {str(e)}")
        response = {
            "jsonrpc": "2.0",
            "id": message_data.get("id") if 'message_data' in locals() else None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        return JSONResponse(content=response, status_code=500)

@app.get("/sse")
async def sse_endpoint():
    """Server-Sent Events endpoint for MCP communication"""
    async def event_generator():
        # Send initial connection message
        yield f"data: {json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'})}\n\n"
        
        # Keep connection alive with periodic pings
        while True:
            yield f"data: {json.dumps({'type': 'ping'})}\n\n"
            await asyncio.sleep(30)  # Send ping every 30 seconds
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.post("/messages")
async def handle_message(request: Request):
    """Handle MCP protocol messages"""
    try:
        # Get raw JSON to handle different ID types
        body = await request.body()
        message_data = json.loads(body.decode('utf-8'))
        
        logger.info(f"Received message: {message_data}")
        
        method = message_data.get('method')
        message_id = message_data.get('id')
        params = message_data.get('params', {})
        
        if method == 'initialize':
            # Return server capabilities
            response = {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "ciso-assistant",
                        "version": "1.0.0"
                    }
                }
            }
            logger.info(f"Sending initialize response: {response}")
            return JSONResponse(content=response)
        
        elif method == 'tools/list':
            # Return available tools
            response = {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "tools": mcp_wrapper.tools
                }
            }
            logger.info(f"Sending tools list: {response}")
            return JSONResponse(content=response)
        
        elif method == 'tools/call':
            # Execute tool
            tool_name = params.get('name')
            tool_arguments = params.get('arguments', {})
            logger.info(f"Executing tool: {tool_name} with arguments: {tool_arguments}")
            
            if hasattr(mcp_wrapper, tool_name):
                # Execute the corresponding method
                method_func = getattr(mcp_wrapper, tool_name)
                
                # Check if the method requires arguments
                if tool_arguments:
                    result = await method_func(**tool_arguments)
                else:
                    result = await method_func()
                
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": result
                }
                logger.info(f"Tool execution result: {response}")
                return JSONResponse(content=response)
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
                return JSONResponse(content=response)
        
        else:
            response = {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown method: {method}"
                }
            }
            return JSONResponse(content=response)
            
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        response = {
            "jsonrpc": "2.0",
            "id": message_data.get("id") if 'message_data' in locals() else None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        return JSONResponse(content=response, status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ciso-assistant-mcp"}

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "CISO Assistant MCP Web Wrapper",
        "version": "1.0.0", 
        "endpoints": {
            "sse": "/sse (GET for SSE stream, POST for MCP messages)",
            "messages": "/messages",
            "health": "/health"
        },
        "tools": [tool["name"] for tool in mcp_wrapper.tools]
    }

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)