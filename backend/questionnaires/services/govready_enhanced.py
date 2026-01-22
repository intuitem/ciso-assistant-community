"""
GovReady-Q Inspired Questionnaire Enhancements

Enhanced questionnaire capabilities inspired by GovReady-Q patterns:
- Conditional logic engine for dynamic question flows
- Module repository for reusable compliance modules
- Statement generator for control implementation statements
- Output document generation from answers
"""

import json
import logging
import uuid
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ConditionOperator(Enum):
    """Operators for conditional logic evaluation"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    MATCHES = "matches"  # Regex match
    IN = "in"  # Value in list
    NOT_IN = "not_in"


@dataclass
class ConditionResult:
    """Result of condition evaluation"""
    satisfied: bool
    question_id: str
    condition: Dict[str, Any]
    actual_value: Any
    expected_value: Any


@dataclass
class QuestionVisibility:
    """Visibility state for a question"""
    question_id: str
    visible: bool
    reason: str = ""
    imputed_value: Any = None  # If auto-answered


@dataclass
class ModuleSpec:
    """Specification for a questionnaire module"""
    module_id: str
    title: str
    description: str
    version: str
    questions: List[Dict[str, Any]]
    output_documents: List[Dict[str, Any]]
    control_mappings: Dict[str, List[str]]  # question_id -> control_ids
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedStatement:
    """Generated control implementation statement"""
    control_id: str
    statement_text: str
    source_questions: List[str]
    confidence: float  # 0.0 - 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)


class ConditionalLogicEngine:
    """
    Engine for evaluating conditional question logic.

    Supports:
    - Show/hide conditions based on other answers
    - Impute conditions (auto-answer based on context)
    - Complex boolean logic (AND, OR, NOT)
    - Nested conditions
    """

    def __init__(self):
        """Initialize the conditional logic engine"""
        self.operators = {
            ConditionOperator.EQUALS: self._eval_equals,
            ConditionOperator.NOT_EQUALS: self._eval_not_equals,
            ConditionOperator.CONTAINS: self._eval_contains,
            ConditionOperator.NOT_CONTAINS: self._eval_not_contains,
            ConditionOperator.GREATER_THAN: self._eval_greater_than,
            ConditionOperator.LESS_THAN: self._eval_less_than,
            ConditionOperator.GREATER_OR_EQUAL: self._eval_greater_or_equal,
            ConditionOperator.LESS_OR_EQUAL: self._eval_less_or_equal,
            ConditionOperator.IS_EMPTY: self._eval_is_empty,
            ConditionOperator.IS_NOT_EMPTY: self._eval_is_not_empty,
            ConditionOperator.MATCHES: self._eval_matches,
            ConditionOperator.IN: self._eval_in,
            ConditionOperator.NOT_IN: self._eval_not_in,
        }

    def evaluate_visibility(
        self,
        question: Dict[str, Any],
        answers: Dict[str, Any]
    ) -> QuestionVisibility:
        """
        Evaluate whether a question should be visible.

        Args:
            question: Question data with conditional_logic
            answers: Current answers dictionary

        Returns:
            QuestionVisibility result
        """
        question_id = question.get('id', '')
        conditional_logic = question.get('conditional_logic', {})

        # Default to visible if no conditions
        if not conditional_logic:
            return QuestionVisibility(
                question_id=question_id,
                visible=True,
                reason="No conditions"
            )

        # Check show_if conditions
        show_if = conditional_logic.get('show_if')
        if show_if:
            result = self._evaluate_condition(show_if, answers)
            if not result.satisfied:
                return QuestionVisibility(
                    question_id=question_id,
                    visible=False,
                    reason=f"show_if condition not satisfied"
                )

        # Check hide_if conditions
        hide_if = conditional_logic.get('hide_if')
        if hide_if:
            result = self._evaluate_condition(hide_if, answers)
            if result.satisfied:
                return QuestionVisibility(
                    question_id=question_id,
                    visible=False,
                    reason=f"hide_if condition satisfied"
                )

        return QuestionVisibility(
            question_id=question_id,
            visible=True,
            reason="All conditions satisfied"
        )

    def evaluate_impute(
        self,
        question: Dict[str, Any],
        answers: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Any]:
        """
        Evaluate whether a question should be auto-answered (imputed).

        Args:
            question: Question data with impute conditions
            answers: Current answers dictionary
            context: Additional context data

        Returns:
            Tuple of (should_impute, imputed_value)
        """
        conditional_logic = question.get('conditional_logic', {})
        impute_conditions = conditional_logic.get('impute_conditions', [])

        if not impute_conditions:
            return False, None

        for impute_rule in impute_conditions:
            condition = impute_rule.get('condition', {})
            value = impute_rule.get('value')

            if condition:
                result = self._evaluate_condition(condition, answers, context)
                if result.satisfied:
                    return True, value
            else:
                # No condition means always impute
                return True, value

        return False, None

    def _evaluate_condition(
        self,
        condition: Dict[str, Any],
        answers: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ConditionResult:
        """Evaluate a single condition or compound condition"""
        context = context or {}

        # Handle compound conditions (AND, OR, NOT)
        if 'and' in condition:
            sub_conditions = condition['and']
            all_satisfied = all(
                self._evaluate_condition(sub, answers, context).satisfied
                for sub in sub_conditions
            )
            return ConditionResult(
                satisfied=all_satisfied,
                question_id='compound_and',
                condition=condition,
                actual_value=None,
                expected_value=None
            )

        if 'or' in condition:
            sub_conditions = condition['or']
            any_satisfied = any(
                self._evaluate_condition(sub, answers, context).satisfied
                for sub in sub_conditions
            )
            return ConditionResult(
                satisfied=any_satisfied,
                question_id='compound_or',
                condition=condition,
                actual_value=None,
                expected_value=None
            )

        if 'not' in condition:
            sub_condition = condition['not']
            sub_result = self._evaluate_condition(sub_condition, answers, context)
            return ConditionResult(
                satisfied=not sub_result.satisfied,
                question_id='compound_not',
                condition=condition,
                actual_value=sub_result.actual_value,
                expected_value=sub_result.expected_value
            )

        # Simple condition
        question_id = condition.get('question_id', condition.get('field'))
        operator_str = condition.get('operator', 'equals')
        expected_value = condition.get('value')

        # Get actual value from answers or context
        actual_value = answers.get(question_id)
        if actual_value is None and context:
            actual_value = context.get(question_id)

        # Convert operator string to enum
        try:
            operator = ConditionOperator(operator_str)
        except ValueError:
            operator = ConditionOperator.EQUALS

        # Evaluate
        eval_func = self.operators.get(operator, self._eval_equals)
        satisfied = eval_func(actual_value, expected_value)

        return ConditionResult(
            satisfied=satisfied,
            question_id=question_id,
            condition=condition,
            actual_value=actual_value,
            expected_value=expected_value
        )

    # Operator implementations
    def _eval_equals(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return expected is None
        return str(actual).lower() == str(expected).lower()

    def _eval_not_equals(self, actual: Any, expected: Any) -> bool:
        return not self._eval_equals(actual, expected)

    def _eval_contains(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        if isinstance(actual, list):
            return expected in actual
        return str(expected).lower() in str(actual).lower()

    def _eval_not_contains(self, actual: Any, expected: Any) -> bool:
        return not self._eval_contains(actual, expected)

    def _eval_greater_than(self, actual: Any, expected: Any) -> bool:
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False

    def _eval_less_than(self, actual: Any, expected: Any) -> bool:
        try:
            return float(actual) < float(expected)
        except (TypeError, ValueError):
            return False

    def _eval_greater_or_equal(self, actual: Any, expected: Any) -> bool:
        try:
            return float(actual) >= float(expected)
        except (TypeError, ValueError):
            return False

    def _eval_less_or_equal(self, actual: Any, expected: Any) -> bool:
        try:
            return float(actual) <= float(expected)
        except (TypeError, ValueError):
            return False

    def _eval_is_empty(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return True
        if isinstance(actual, (list, dict, str)):
            return len(actual) == 0
        return False

    def _eval_is_not_empty(self, actual: Any, expected: Any) -> bool:
        return not self._eval_is_empty(actual, expected)

    def _eval_matches(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        try:
            return bool(re.match(str(expected), str(actual)))
        except re.error:
            return False

    def _eval_in(self, actual: Any, expected: Any) -> bool:
        if not isinstance(expected, list):
            expected = [expected]
        return actual in expected

    def _eval_not_in(self, actual: Any, expected: Any) -> bool:
        return not self._eval_in(actual, expected)

    def get_visible_questions(
        self,
        questions: List[Dict[str, Any]],
        answers: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get list of currently visible questions.

        Args:
            questions: All questions in questionnaire
            answers: Current answers

        Returns:
            List of visible questions
        """
        visible = []
        for question in questions:
            visibility = self.evaluate_visibility(question, answers)
            if visibility.visible:
                visible.append(question)
        return visible


class ModuleRepository:
    """
    Repository for reusable questionnaire modules.

    Provides pre-built assessment modules for common compliance frameworks:
    - FedRAMP (Low, Moderate, High)
    - NIST 800-53
    - GDPR
    - ISO 27001
    - SOC 2
    - HIPAA
    - PCI-DSS
    """

    def __init__(self):
        """Initialize module repository"""
        self._modules: Dict[str, ModuleSpec] = {}
        self._load_builtin_modules()

    def _load_builtin_modules(self):
        """Load built-in compliance modules"""
        # FedRAMP Low Baseline Module
        self._modules['fedramp-low'] = ModuleSpec(
            module_id='fedramp-low',
            title='FedRAMP Low Baseline Assessment',
            description='Assessment questionnaire for FedRAMP Low baseline controls',
            version='1.0',
            questions=self._get_fedramp_low_questions(),
            output_documents=[
                {'type': 'control_statement', 'format': 'oscal'},
                {'type': 'ssp_section', 'format': 'docx'},
            ],
            control_mappings=self._get_fedramp_low_mappings(),
            metadata={'baseline': 'low', 'framework': 'fedramp'}
        )

        # FedRAMP Moderate Baseline Module
        self._modules['fedramp-moderate'] = ModuleSpec(
            module_id='fedramp-moderate',
            title='FedRAMP Moderate Baseline Assessment',
            description='Assessment questionnaire for FedRAMP Moderate baseline controls',
            version='1.0',
            questions=self._get_fedramp_moderate_questions(),
            output_documents=[
                {'type': 'control_statement', 'format': 'oscal'},
                {'type': 'ssp_section', 'format': 'docx'},
            ],
            control_mappings=self._get_fedramp_moderate_mappings(),
            metadata={'baseline': 'moderate', 'framework': 'fedramp'}
        )

        # NIST 800-53 Assessment Module
        self._modules['nist-800-53'] = ModuleSpec(
            module_id='nist-800-53',
            title='NIST SP 800-53 Assessment',
            description='Security control assessment based on NIST SP 800-53',
            version='1.0',
            questions=self._get_nist_800_53_questions(),
            output_documents=[
                {'type': 'control_statement', 'format': 'text'},
                {'type': 'assessment_report', 'format': 'docx'},
            ],
            control_mappings=self._get_nist_800_53_mappings(),
            metadata={'framework': 'nist-800-53', 'revision': '5'}
        )

        # GDPR Assessment Module
        self._modules['gdpr'] = ModuleSpec(
            module_id='gdpr',
            title='GDPR Data Protection Assessment',
            description='Assessment for GDPR compliance requirements',
            version='1.0',
            questions=self._get_gdpr_questions(),
            output_documents=[
                {'type': 'dpia', 'format': 'docx'},
                {'type': 'compliance_report', 'format': 'pdf'},
            ],
            control_mappings={},
            metadata={'framework': 'gdpr', 'region': 'eu'}
        )

        # ISO 27001 Assessment Module
        self._modules['iso-27001'] = ModuleSpec(
            module_id='iso-27001',
            title='ISO 27001 ISMS Assessment',
            description='Information Security Management System assessment',
            version='1.0',
            questions=self._get_iso_27001_questions(),
            output_documents=[
                {'type': 'soa', 'format': 'xlsx'},
                {'type': 'gap_analysis', 'format': 'docx'},
            ],
            control_mappings=self._get_iso_27001_mappings(),
            metadata={'framework': 'iso-27001', 'version': '2022'}
        )

    def get_module(self, module_id: str) -> Optional[ModuleSpec]:
        """Get a module by ID"""
        return self._modules.get(module_id)

    def list_modules(self, framework: Optional[str] = None) -> List[ModuleSpec]:
        """List all available modules, optionally filtered by framework"""
        modules = list(self._modules.values())
        if framework:
            modules = [m for m in modules if m.metadata.get('framework') == framework]
        return modules

    def register_module(self, module: ModuleSpec) -> bool:
        """Register a custom module"""
        if module.module_id in self._modules:
            return False
        self._modules[module.module_id] = module
        return True

    def get_module_questions(self, module_id: str) -> List[Dict[str, Any]]:
        """Get questions for a specific module"""
        module = self.get_module(module_id)
        if module:
            return module.questions
        return []

    def get_control_mapping(self, module_id: str, question_id: str) -> List[str]:
        """Get control IDs mapped to a question"""
        module = self.get_module(module_id)
        if module:
            return module.control_mappings.get(question_id, [])
        return []

    # Module question definitions (simplified examples)

    def _get_fedramp_low_questions(self) -> List[Dict[str, Any]]:
        """Get FedRAMP Low baseline questions"""
        return [
            {
                'id': 'ac-1-policy',
                'text': 'Does your organization have a documented access control policy?',
                'question_type': 'yes_no',
                'help_text': 'This policy should define access control procedures for the system.',
                'is_required': True,
                'control_id': 'AC-1',
            },
            {
                'id': 'ac-1-review-frequency',
                'text': 'How often is the access control policy reviewed?',
                'question_type': 'single_choice',
                'options': [
                    {'value': 'annually', 'label': 'Annually', 'score': 3},
                    {'value': 'biannually', 'label': 'Every 2 years', 'score': 2},
                    {'value': 'as-needed', 'label': 'As needed', 'score': 1},
                    {'value': 'never', 'label': 'Never', 'score': 0},
                ],
                'conditional_logic': {
                    'show_if': {'question_id': 'ac-1-policy', 'operator': 'equals', 'value': 'yes'}
                },
                'control_id': 'AC-1',
            },
            {
                'id': 'ac-2-account-types',
                'text': 'Which account types does your system support?',
                'question_type': 'multiple_choice',
                'options': [
                    {'value': 'individual', 'label': 'Individual User Accounts'},
                    {'value': 'group', 'label': 'Group Accounts'},
                    {'value': 'system', 'label': 'System Accounts'},
                    {'value': 'service', 'label': 'Service Accounts'},
                    {'value': 'guest', 'label': 'Guest Accounts'},
                ],
                'is_required': True,
                'control_id': 'AC-2',
            },
            {
                'id': 'ia-2-mfa',
                'text': 'Is multi-factor authentication enabled for all users?',
                'question_type': 'single_choice',
                'options': [
                    {'value': 'yes-all', 'label': 'Yes, for all users', 'score': 3},
                    {'value': 'yes-privileged', 'label': 'Yes, for privileged users only', 'score': 2},
                    {'value': 'partial', 'label': 'Partially implemented', 'score': 1},
                    {'value': 'no', 'label': 'No', 'score': 0},
                ],
                'is_required': True,
                'control_id': 'IA-2(1)',
            },
            {
                'id': 'au-2-events',
                'text': 'Which events are logged in the system?',
                'question_type': 'multiple_choice',
                'options': [
                    {'value': 'login-success', 'label': 'Successful logins'},
                    {'value': 'login-failure', 'label': 'Failed login attempts'},
                    {'value': 'privilege-use', 'label': 'Use of privileged functions'},
                    {'value': 'data-access', 'label': 'Access to sensitive data'},
                    {'value': 'config-changes', 'label': 'Configuration changes'},
                    {'value': 'security-events', 'label': 'Security-relevant events'},
                ],
                'is_required': True,
                'control_id': 'AU-2',
            },
        ]

    def _get_fedramp_low_mappings(self) -> Dict[str, List[str]]:
        """Get control mappings for FedRAMP Low questions"""
        return {
            'ac-1-policy': ['AC-1'],
            'ac-1-review-frequency': ['AC-1'],
            'ac-2-account-types': ['AC-2'],
            'ia-2-mfa': ['IA-2', 'IA-2(1)'],
            'au-2-events': ['AU-2'],
        }

    def _get_fedramp_moderate_questions(self) -> List[Dict[str, Any]]:
        """Get FedRAMP Moderate baseline questions (extends Low)"""
        questions = self._get_fedramp_low_questions()
        questions.extend([
            {
                'id': 'cm-2-baseline',
                'text': 'Does your organization maintain baseline configurations?',
                'question_type': 'yes_no',
                'is_required': True,
                'control_id': 'CM-2',
            },
            {
                'id': 'ir-4-incident-handling',
                'text': 'Describe your incident handling capability:',
                'question_type': 'single_choice',
                'options': [
                    {'value': 'full', 'label': 'Full 24/7 incident response team', 'score': 3},
                    {'value': 'partial', 'label': 'Business hours incident handling', 'score': 2},
                    {'value': 'minimal', 'label': 'Ad-hoc incident response', 'score': 1},
                    {'value': 'none', 'label': 'No formal capability', 'score': 0},
                ],
                'is_required': True,
                'control_id': 'IR-4',
            },
            {
                'id': 'sc-7-boundary',
                'text': 'How is the system authorization boundary protected?',
                'question_type': 'multiple_choice',
                'options': [
                    {'value': 'firewall', 'label': 'Network firewall'},
                    {'value': 'waf', 'label': 'Web application firewall'},
                    {'value': 'ids', 'label': 'Intrusion detection system'},
                    {'value': 'dmz', 'label': 'DMZ architecture'},
                    {'value': 'vpn', 'label': 'VPN for remote access'},
                ],
                'is_required': True,
                'control_id': 'SC-7',
            },
        ])
        return questions

    def _get_fedramp_moderate_mappings(self) -> Dict[str, List[str]]:
        """Get control mappings for FedRAMP Moderate questions"""
        mappings = self._get_fedramp_low_mappings()
        mappings.update({
            'cm-2-baseline': ['CM-2'],
            'ir-4-incident-handling': ['IR-4'],
            'sc-7-boundary': ['SC-7'],
        })
        return mappings

    def _get_nist_800_53_questions(self) -> List[Dict[str, Any]]:
        """Get NIST 800-53 assessment questions"""
        return [
            {
                'id': 'nist-family-selection',
                'text': 'Which control families are applicable to your system?',
                'question_type': 'multiple_choice',
                'options': [
                    {'value': 'AC', 'label': 'Access Control (AC)'},
                    {'value': 'AT', 'label': 'Awareness and Training (AT)'},
                    {'value': 'AU', 'label': 'Audit and Accountability (AU)'},
                    {'value': 'CA', 'label': 'Assessment, Authorization, and Monitoring (CA)'},
                    {'value': 'CM', 'label': 'Configuration Management (CM)'},
                    {'value': 'CP', 'label': 'Contingency Planning (CP)'},
                    {'value': 'IA', 'label': 'Identification and Authentication (IA)'},
                    {'value': 'IR', 'label': 'Incident Response (IR)'},
                    {'value': 'MA', 'label': 'Maintenance (MA)'},
                    {'value': 'MP', 'label': 'Media Protection (MP)'},
                    {'value': 'PE', 'label': 'Physical and Environmental Protection (PE)'},
                    {'value': 'PL', 'label': 'Planning (PL)'},
                    {'value': 'PM', 'label': 'Program Management (PM)'},
                    {'value': 'PS', 'label': 'Personnel Security (PS)'},
                    {'value': 'RA', 'label': 'Risk Assessment (RA)'},
                    {'value': 'SA', 'label': 'System and Services Acquisition (SA)'},
                    {'value': 'SC', 'label': 'System and Communications Protection (SC)'},
                    {'value': 'SI', 'label': 'System and Information Integrity (SI)'},
                    {'value': 'SR', 'label': 'Supply Chain Risk Management (SR)'},
                ],
                'is_required': True,
            },
            {
                'id': 'nist-impact-level',
                'text': 'What is the system impact level?',
                'question_type': 'single_choice',
                'options': [
                    {'value': 'low', 'label': 'Low'},
                    {'value': 'moderate', 'label': 'Moderate'},
                    {'value': 'high', 'label': 'High'},
                ],
                'is_required': True,
            },
        ]

    def _get_nist_800_53_mappings(self) -> Dict[str, List[str]]:
        """Get control mappings for NIST 800-53 questions"""
        return {
            'nist-family-selection': [],
            'nist-impact-level': [],
        }

    def _get_gdpr_questions(self) -> List[Dict[str, Any]]:
        """Get GDPR assessment questions"""
        return [
            {
                'id': 'gdpr-data-processing',
                'text': 'What is the lawful basis for processing personal data?',
                'question_type': 'multiple_choice',
                'options': [
                    {'value': 'consent', 'label': 'Consent'},
                    {'value': 'contract', 'label': 'Contract performance'},
                    {'value': 'legal', 'label': 'Legal obligation'},
                    {'value': 'vital', 'label': 'Vital interests'},
                    {'value': 'public', 'label': 'Public interest'},
                    {'value': 'legitimate', 'label': 'Legitimate interests'},
                ],
                'is_required': True,
            },
            {
                'id': 'gdpr-dpo',
                'text': 'Has a Data Protection Officer been appointed?',
                'question_type': 'yes_no',
                'is_required': True,
            },
            {
                'id': 'gdpr-dpia',
                'text': 'Has a Data Protection Impact Assessment been conducted?',
                'question_type': 'yes_no',
                'is_required': True,
            },
            {
                'id': 'gdpr-data-subjects',
                'text': 'What rights are provided to data subjects?',
                'question_type': 'multiple_choice',
                'options': [
                    {'value': 'access', 'label': 'Right of access'},
                    {'value': 'rectification', 'label': 'Right to rectification'},
                    {'value': 'erasure', 'label': 'Right to erasure'},
                    {'value': 'portability', 'label': 'Right to data portability'},
                    {'value': 'object', 'label': 'Right to object'},
                    {'value': 'restrict', 'label': 'Right to restrict processing'},
                ],
                'is_required': True,
            },
        ]

    def _get_iso_27001_questions(self) -> List[Dict[str, Any]]:
        """Get ISO 27001 assessment questions"""
        return [
            {
                'id': 'iso-isms-scope',
                'text': 'Has the ISMS scope been defined?',
                'question_type': 'yes_no',
                'is_required': True,
            },
            {
                'id': 'iso-risk-assessment',
                'text': 'Has a comprehensive risk assessment been conducted?',
                'question_type': 'single_choice',
                'options': [
                    {'value': 'yes-recent', 'label': 'Yes, within the last year', 'score': 3},
                    {'value': 'yes-old', 'label': 'Yes, but over a year ago', 'score': 2},
                    {'value': 'partial', 'label': 'Partially completed', 'score': 1},
                    {'value': 'no', 'label': 'No', 'score': 0},
                ],
                'is_required': True,
            },
            {
                'id': 'iso-soa',
                'text': 'Is there a Statement of Applicability?',
                'question_type': 'yes_no',
                'is_required': True,
            },
            {
                'id': 'iso-internal-audit',
                'text': 'How often are internal ISMS audits conducted?',
                'question_type': 'single_choice',
                'options': [
                    {'value': 'annually', 'label': 'Annually'},
                    {'value': 'biannually', 'label': 'Every 2 years'},
                    {'value': 'never', 'label': 'Never'},
                ],
                'is_required': True,
            },
        ]

    def _get_iso_27001_mappings(self) -> Dict[str, List[str]]:
        """Get control mappings for ISO 27001 questions"""
        return {
            'iso-isms-scope': ['4.3'],
            'iso-risk-assessment': ['6.1.2', '8.2'],
            'iso-soa': ['6.1.3'],
            'iso-internal-audit': ['9.2'],
        }


class StatementGenerator:
    """
    Generator for control implementation statements.

    Generates control statements from questionnaire answers
    using templates and natural language patterns.
    """

    def __init__(self):
        """Initialize statement generator"""
        self.templates: Dict[str, str] = {}
        self._load_templates()

    def _load_templates(self):
        """Load statement templates"""
        self.templates = {
            # Access Control
            'AC-1': "The organization has {policy_status} an access control policy that is reviewed {review_frequency}.",
            'AC-2': "The system supports the following account types: {account_types}.",
            'AC-2-review': "User accounts are reviewed {review_frequency}.",

            # Identification and Authentication
            'IA-2': "Users are authenticated using {auth_method}.",
            'IA-2(1)': "Multi-factor authentication is {mfa_status} for {mfa_scope}.",

            # Audit and Accountability
            'AU-2': "The system logs the following events: {event_types}.",
            'AU-6': "Audit logs are reviewed {review_frequency}.",

            # Configuration Management
            'CM-2': "Baseline configurations {baseline_status} maintained for the system.",
            'CM-6': "System configuration settings are {config_status}.",

            # Incident Response
            'IR-4': "The organization has {ir_capability} incident handling capability.",

            # System and Communications Protection
            'SC-7': "The system boundary is protected by {boundary_controls}.",
            'SC-13': "Cryptographic protections include {crypto_methods}.",
        }

    def generate_statement(
        self,
        control_id: str,
        answers: Dict[str, Any],
        question_mappings: Dict[str, str]
    ) -> GeneratedStatement:
        """
        Generate a control implementation statement.

        Args:
            control_id: Control identifier
            answers: Questionnaire answers
            question_mappings: Mapping of template variables to question IDs

        Returns:
            GeneratedStatement
        """
        template = self.templates.get(control_id)
        if not template:
            return GeneratedStatement(
                control_id=control_id,
                statement_text=f"Implementation details for {control_id} are documented.",
                source_questions=[],
                confidence=0.3
            )

        # Build parameters from answers
        parameters = {}
        source_questions = []
        answered_count = 0
        total_params = len(re.findall(r'\{(\w+)\}', template))

        for var_name in re.findall(r'\{(\w+)\}', template):
            question_id = question_mappings.get(var_name)
            if question_id and question_id in answers:
                value = answers[question_id]
                parameters[var_name] = self._format_value(value)
                source_questions.append(question_id)
                answered_count += 1
            else:
                parameters[var_name] = '[Not specified]'

        # Generate statement
        try:
            statement_text = template.format(**parameters)
        except KeyError:
            statement_text = f"Implementation details for {control_id} are documented."

        # Calculate confidence based on answered parameters
        confidence = answered_count / total_params if total_params > 0 else 0.5

        return GeneratedStatement(
            control_id=control_id,
            statement_text=statement_text,
            source_questions=source_questions,
            confidence=confidence,
            parameters=parameters
        )

    def generate_statements_for_module(
        self,
        module: ModuleSpec,
        answers: Dict[str, Any]
    ) -> List[GeneratedStatement]:
        """
        Generate statements for all controls in a module.

        Args:
            module: Module specification
            answers: Questionnaire answers

        Returns:
            List of generated statements
        """
        statements = []
        processed_controls = set()

        for question_id, control_ids in module.control_mappings.items():
            for control_id in control_ids:
                if control_id not in processed_controls:
                    # Build question mapping for this control
                    question_mapping = self._build_question_mapping(
                        control_id, question_id, answers
                    )

                    statement = self.generate_statement(
                        control_id, answers, question_mapping
                    )
                    statements.append(statement)
                    processed_controls.add(control_id)

        return statements

    def _build_question_mapping(
        self,
        control_id: str,
        question_id: str,
        answers: Dict[str, Any]
    ) -> Dict[str, str]:
        """Build variable to question mapping based on control and answers"""
        # Default mappings based on common patterns
        mappings = {
            'policy_status': question_id if 'policy' in question_id else None,
            'review_frequency': question_id if 'frequency' in question_id or 'review' in question_id else None,
            'account_types': question_id if 'account' in question_id else None,
            'mfa_status': question_id if 'mfa' in question_id else None,
            'mfa_scope': question_id if 'mfa' in question_id else None,
            'auth_method': question_id if 'auth' in question_id else None,
            'event_types': question_id if 'event' in question_id else None,
            'baseline_status': question_id if 'baseline' in question_id else None,
            'config_status': question_id if 'config' in question_id else None,
            'ir_capability': question_id if 'incident' in question_id else None,
            'boundary_controls': question_id if 'boundary' in question_id else None,
            'crypto_methods': question_id if 'crypto' in question_id else None,
        }

        return {k: v for k, v in mappings.items() if v is not None}

    def _format_value(self, value: Any) -> str:
        """Format an answer value for statement inclusion"""
        if isinstance(value, list):
            if len(value) == 0:
                return "none specified"
            elif len(value) == 1:
                return str(value[0])
            else:
                return ", ".join(str(v) for v in value[:-1]) + f" and {value[-1]}"
        elif isinstance(value, bool):
            return "implemented" if value else "not implemented"
        elif value == 'yes':
            return "established and documented"
        elif value == 'no':
            return "not established"
        else:
            return str(value)


class OutputDocumentGenerator:
    """
    Generator for output documents from questionnaire answers.

    Generates various document types:
    - Control implementation statements (OSCAL/text)
    - SSP sections (DOCX)
    - Gap analysis reports
    - Compliance scorecards
    """

    def __init__(self):
        """Initialize output document generator"""
        self.statement_generator = StatementGenerator()

    def generate_oscal_statements(
        self,
        module: ModuleSpec,
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate OSCAL-formatted control statements.

        Args:
            module: Module specification
            answers: Questionnaire answers

        Returns:
            OSCAL-compatible structure
        """
        statements = self.statement_generator.generate_statements_for_module(
            module, answers
        )

        implemented_requirements = []
        for stmt in statements:
            impl_req = {
                'control-id': stmt.control_id,
                'uuid': str(uuid.uuid4()),
                'statements': [
                    {
                        'statement-id': f"{stmt.control_id}_stmt",
                        'uuid': str(uuid.uuid4()),
                        'description': stmt.statement_text
                    }
                ],
                'props': [
                    {
                        'name': 'implementation-status',
                        'value': 'implemented' if stmt.confidence > 0.7 else 'partially-implemented'
                    },
                    {
                        'name': 'confidence',
                        'value': str(stmt.confidence)
                    }
                ]
            }
            implemented_requirements.append(impl_req)

        return {
            'control-implementation': {
                'description': f'Control implementations from {module.title}',
                'implemented-requirements': implemented_requirements
            },
            'metadata': {
                'title': f'Generated from {module.title}',
                'generated': datetime.now().isoformat(),
                'module_id': module.module_id,
                'module_version': module.version
            }
        }

    def generate_gap_analysis(
        self,
        module: ModuleSpec,
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate gap analysis from questionnaire answers.

        Args:
            module: Module specification
            answers: Questionnaire answers

        Returns:
            Gap analysis structure
        """
        statements = self.statement_generator.generate_statements_for_module(
            module, answers
        )

        gaps = []
        compliant = []
        partial = []

        for stmt in statements:
            entry = {
                'control_id': stmt.control_id,
                'statement': stmt.statement_text,
                'confidence': stmt.confidence,
                'source_questions': stmt.source_questions
            }

            if stmt.confidence >= 0.8:
                compliant.append(entry)
            elif stmt.confidence >= 0.5:
                partial.append(entry)
            else:
                gaps.append(entry)

        total_controls = len(statements)
        compliance_score = (len(compliant) / total_controls * 100) if total_controls > 0 else 0

        return {
            'summary': {
                'total_controls': total_controls,
                'compliant': len(compliant),
                'partial': len(partial),
                'gaps': len(gaps),
                'compliance_score': round(compliance_score, 2)
            },
            'compliant_controls': compliant,
            'partial_controls': partial,
            'gap_controls': gaps,
            'recommendations': self._generate_recommendations(gaps, partial),
            'generated': datetime.now().isoformat()
        }

    def _generate_recommendations(
        self,
        gaps: List[Dict[str, Any]],
        partial: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on gaps"""
        recommendations = []

        if gaps:
            recommendations.append(
                f"Address {len(gaps)} control gaps before authorization"
            )
            gap_controls = [g['control_id'] for g in gaps[:5]]
            recommendations.append(
                f"Priority gaps to address: {', '.join(gap_controls)}"
            )

        if partial:
            recommendations.append(
                f"Complete implementation of {len(partial)} partially implemented controls"
            )

        if not gaps and not partial:
            recommendations.append(
                "All controls appear to be implemented. Schedule a formal assessment."
            )

        return recommendations
