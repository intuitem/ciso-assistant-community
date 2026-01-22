"""
Domain Events for Questionnaire Bounded Context
"""

from core.domain.events import DomainEvent


# Questionnaire Events
class QuestionnaireCreated(DomainEvent):
    """Raised when a questionnaire is created"""
    pass


class QuestionnairePublished(DomainEvent):
    """Raised when a questionnaire is published"""
    pass


class QuestionnaireArchived(DomainEvent):
    """Raised when a questionnaire is archived"""
    pass


class QuestionnaireCloned(DomainEvent):
    """Raised when a questionnaire is cloned"""
    pass


class QuestionnaireQuestionsReordered(DomainEvent):
    """Raised when questionnaire questions are reordered"""
    pass


# Question Events
class QuestionCreated(DomainEvent):
    """Raised when a question is created"""
    pass


class QuestionUpdated(DomainEvent):
    """Raised when a question is updated"""
    pass


class QuestionDeleted(DomainEvent):
    """Raised when a question is deleted"""
    pass


class QuestionAddedToQuestionnaire(DomainEvent):
    """Raised when a question is added to a questionnaire"""
    pass


class QuestionRemovedFromQuestionnaire(DomainEvent):
    """Raised when a question is removed from a questionnaire"""
    pass


# Answer Events
class AnswerSubmitted(DomainEvent):
    """Raised when an answer is submitted"""
    pass


class AnswerUpdated(DomainEvent):
    """Raised when an answer is updated"""
    pass


class QuestionnaireRunStarted(DomainEvent):
    """Raised when a questionnaire run is started"""
    pass


class QuestionnaireRunCompleted(DomainEvent):
    """Raised when a questionnaire run is completed"""
    pass


class QuestionnaireRunScored(DomainEvent):
    """Raised when a questionnaire run is scored"""
    pass
