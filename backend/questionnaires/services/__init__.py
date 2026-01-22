"""
Questionnaire Services

This module provides services for questionnaire management:
- QuestionnaireService: Core questionnaire operations
- ConditionalLogicEngine: Evaluate conditional question visibility
- ModuleRepository: Pre-built compliance assessment modules
- StatementGenerator: Generate control implementation statements
- OutputDocumentGenerator: Generate documents from questionnaire answers
"""


def __getattr__(name):
    """Lazy import to avoid circular dependencies and optional dependency issues"""
    if name == 'QuestionnaireService':
        from backend.questionnaires.services.questionnaire_service import QuestionnaireService
        return QuestionnaireService
    elif name == 'ConditionalLogicEngine':
        from backend.questionnaires.services.govready_enhanced import ConditionalLogicEngine
        return ConditionalLogicEngine
    elif name == 'ModuleRepository':
        from backend.questionnaires.services.govready_enhanced import ModuleRepository
        return ModuleRepository
    elif name == 'StatementGenerator':
        from backend.questionnaires.services.govready_enhanced import StatementGenerator
        return StatementGenerator
    elif name == 'OutputDocumentGenerator':
        from backend.questionnaires.services.govready_enhanced import OutputDocumentGenerator
        return OutputDocumentGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'QuestionnaireService',
    'ConditionalLogicEngine',
    'ModuleRepository',
    'StatementGenerator',
    'OutputDocumentGenerator',
]
