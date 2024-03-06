from django.core.management.base import BaseCommand
from core.models import *
from iam.models import User, Folder


class Command(BaseCommand):
    help = "Displays instance status"

    def handle(self, *args, **kwargs):
        nb_users = User.objects.all().count()
        nb_first_login = User.objects.filter(first_login=True).count()
        nb_libraries = Library.objects.all().count()
        nb_domains = Folder.objects.filter(content_type="DO").count()
        nb_projects = Project.objects.all().count()
        nb_assets = Asset.objects.all().count()
        nb_threats = Threat.objects.all().count()
        nb_functions = ReferenceControl.objects.all().count()
        nb_measures = AppliedControl.objects.all().count()
        nb_evidences = Evidence.objects.all().count()
        nb_compliance_assessments = ComplianceAssessment.objects.all().count()
        nb_risk_assessments = RiskAssessment.objects.all().count()
        nb_risk_scenarios = RiskScenario.objects.all().count()
        nb_risk_acceptances = RiskAcceptance.objects.all().count()
        self.stdout.write(
            f"users={nb_users} first_logins={nb_first_login} libraries={nb_libraries} "
            + f"domains={nb_domains} projects={nb_projects} assets={nb_assets} "
            + f"threats={nb_threats} functions={nb_functions} measures={nb_measures} "
            + f"evidences={nb_evidences} compliance={nb_compliance_assessments} risk={nb_risk_assessments} "
            + f"scenarios={nb_risk_scenarios} acceptances={nb_risk_acceptances}"
        )
