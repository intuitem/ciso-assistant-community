from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator

from django.views.generic import ListView
from core.models import Analysis, RiskInstance, Mitigation
from general.models import Project
from django.contrib.auth.views import LoginView
from .forms import LoginForm
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from .helpers import (mitigation_per_status, risk_per_status, p_risks, p_risks_2,
                      risks_count_per_level, mitigation_per_cur_risk, mitigation_per_solution,
                      mitigation_priority, risk_matrix, risks_per_project_groups,
                      get_counters, risk_status, risks_levels_per_prj_grp)

from django.template.loader import render_to_string
from weasyprint import HTML, CSS
import logging
import csv


class AnalysisListView(ListView):
    template_name = 'core/index.html'
    context_object_name = 'context'

    ordering = 'id'
    paginate_by = 10
    model = Analysis


class UserLogin(LoginView):
    template_name = 'registration/login.html'
    form_class = LoginForm


@method_decorator(login_required, name='dispatch')
class MitigationPlanView(ListView):
    template_name = 'core/mp.html'
    context_object_name = 'context'

    def get_queryset(self):
        self.analysis = get_object_or_404(Analysis, id=self.kwargs['analysis'])


def build_ri_clusters(analysis: Analysis):
    matrix_current = [[set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                      [set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                      [set(), set(), set(), set(), set()]]
    matrix_residual = [[set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                       [set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                       [set(), set(), set(), set(), set()]]
    map_impact = {'VH': 0, 'H': 1, 'M': 2, 'L': 3, 'VL': 4}
    map_proba = {'VL': 0, 'L': 1, 'M': 2, 'H': 3, 'VH': 4}
    for ri in RiskInstance.objects.filter(analysis=analysis).order_by('id'):
        matrix_current[map_impact[ri.current_impact]][map_proba[ri.current_proba]].add(ri.rid())
        matrix_residual[map_impact[ri.residual_impact]][map_proba[ri.residual_proba]].add(ri.rid())

    return {'current': matrix_current, 'residual': matrix_residual}


@method_decorator(login_required, name='dispatch')
class RiskAnalysisView(ListView):
    template_name = 'core/ra.html'
    context_object_name = 'context'

    def get_queryset(self):
        self.analysis = get_object_or_404(Analysis, id=self.kwargs['analysis'])
        return RiskInstance.objects.filter(analysis=self.analysis).order_by('id')

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # then Add in
        context['analysis'] = self.analysis
        context['ri_clusters'] = build_ri_clusters(self.analysis)
        return context


@login_required
def generate_ra_pdf(request, analysis):
    ra = get_object_or_404(Analysis, pk=analysis)
    context = RiskInstance.objects.filter(analysis=analysis).order_by('id')
    data = {'context': context, 'analysis': ra, 'ri_clusters': build_ri_clusters(ra)}

    html = render_to_string('core/ra_pdf.html', data)
    pdf_file = HTML(string=html).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="RA-{ra.id}-{ra.project}-v-{ra.version}.pdf"'

    return response


@login_required
def generate_mp_pdf(request, analysis):
    ra = get_object_or_404(Analysis, pk=analysis)
    context = RiskInstance.objects.filter(analysis=analysis).order_by('id')
    data = {'context': context, 'analysis': ra}

    html = render_to_string('core/mp_pdf.html', data)
    pdf_file = HTML(string=html).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="MP-{ra.id}-{ra.project}-v-{ra.version}.pdf"'

    return response


@method_decorator(login_required, name='dispatch')
class SearchResults(ListView):
    context_object_name = 'context'
    template_name = 'core/search_results.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        ri_list = RiskInstance.objects.filter(Q(title__icontains=query) | Q(parent_risk__title__icontains=query))[:10]
        mtg_list = Mitigation.objects.filter(Q(title__icontains=query) | Q(solution__name__icontains=query))[:10]
        ra_list = Analysis.objects.filter(Q(project__name__icontains=query))[:10]
        return {"Analysis": ra_list, "RiskInstance": ri_list, "Mitigation": mtg_list}


@method_decorator(login_required, name='dispatch')
class Browser(ListView):
    context_object_name = 'context'
    template_name = 'core/browser.html'

    map_rsk = {'0': "open", '1': "mitigated", '2': "accepted", '3': "blocker"}
    map_mtg = {'0': "open", '1': "in_progress", '2': "on_hold", '3': "done"}

    def get_queryset(self):

        rsk = self.request.GET.get('rsk')
        mtg = self.request.GET.get('mtg')
        if rsk:
            return {"type": "Risk Instances", "filter": self.map_rsk[rsk], "items": RiskInstance.objects.filter(treatment=self.map_rsk[rsk])}
        if mtg:
            return {"type": "Mitigations", "filter": self.map_mtg[mtg], "items": Mitigation.objects.filter(status=self.map_mtg[mtg])}



@login_required
def global_analytics(request):
    template = 'core/analytics.html'

    context = {
        "break_by_p_risks": p_risks(),
        "rose": p_risks_2(),
        "risks_level": risks_count_per_level(),
        "risk_status": risk_per_status(),
        "mitigation_status": mitigation_per_status(),
        "mitigation_per_cur_risk": mitigation_per_cur_risk(),
        "mitigation_per_solution": mitigation_per_solution(),
        "mitigation_priority": mitigation_priority(),
        "risk_matrix": risk_matrix(),
        "risks_per_project_groups": risks_per_project_groups(),
        "extra": risks_levels_per_prj_grp(),
        "counters": get_counters(),
    }

    return render(request, template, context)


@method_decorator(login_required, name='dispatch')
class MyProjectsListView(ListView):
    template_name = 'core/my_projects.html'
    context_object_name = 'context'
    model = Mitigation

    def get_queryset(self):
        agg_data = risk_status(Analysis.objects.filter(auditor=self.request.user))
        _tmp = Mitigation.objects.filter(risk_instance__analysis__auditor=self.request.user).exclude(status='done').order_by('eta')
        ord_mitigations = sorted(_tmp, key=lambda mtg: mtg.get_ranking_score(), reverse=True)
        # TODO: add date sorting as well
        return {'agg_data': agg_data,
                'mitigations': ord_mitigations}
        # for UI debug use:
        # return risk_status(Analysis.objects.all())


def compile_analysis_for_composer(analysis_list: list):
    analysis_objects = Analysis.objects.filter(id__in=analysis_list)

    current_level = list()
    residual_level = list()
    agg_risks = list()

    for lvl in RiskInstance.RATING_OPTIONS:
        count_c = RiskInstance.objects.filter(current_level=lvl[0]).filter(analysis__in=analysis_list).count()
        count_r = RiskInstance.objects.filter(residual_level=lvl[0]).filter(analysis__in=analysis_list).count()
        current_level.append({'name': lvl[1], 'value': count_c})
        residual_level.append({'name': lvl[1], 'value': count_r})

    untreated = RiskInstance.objects.filter(analysis__in=analysis_list).exclude(
        treatment__in=['mitigated', 'accepted']).count()
    untreated_h_vh = RiskInstance.objects.filter(analysis__in=analysis_list).exclude(
        treatment__in=['mitigated', 'accepted']).filter(current_level__in=['H', 'VH']).count()
    accepted = RiskInstance.objects.filter(analysis__in=analysis_list).filter(treatment='accepted').count()

    values = list()
    labels = list()
    color_map = {"open": "#fac858", "in_progress": "#5470c6", "on_hold": "#ee6666", "done": "#91cc75"}
    for st in Mitigation.MITIGATION_STATUS:
        count = Mitigation.objects.filter(status=st[0]).filter(risk_instance__analysis__in=analysis_list).count()
        v = {
            "value": count,
            "itemStyle": {"color": color_map[st[0]]}
        }
        values.append(v)
        labels.append(st[1])

    analysis_objects = list()

    for _ra in analysis_list:
        synth_table = list()
        for lvl in RiskInstance.RATING_OPTIONS:
            count_c = RiskInstance.objects.filter(current_level=lvl[0]).filter(analysis__id=_ra).count()
            count_r = RiskInstance.objects.filter(residual_level=lvl[0]).filter(analysis__id=_ra).count()
            synth_table.append({"lvl": lvl[1], "current": count_c, "residual": count_r})
        hvh_risks = RiskInstance.objects.filter(analysis__id=_ra).filter(current_level__in=['H', 'VH'])
        analysis_objects.append(
            {"analysis": get_object_or_404(Analysis, pk=_ra), "synth_table": synth_table, "hvh_risks": hvh_risks}
        )

    return {
        "analysis_objects": analysis_objects,
        "current_level": current_level,
        "residual_level": residual_level,
        "counters": {"untreated": untreated, "untreated_h_vh": untreated_h_vh, "accepted": accepted},
        "mitigation_status": {"labels": labels, "values": values},
    }


class ComposerListView(ListView):

    def get(self, request, *args, **kwargs):
        v = request.GET.get('analysis')
        if v:
            request_list = request.GET.getlist('analysis')[0]
            data = [int(item) for item in request_list.split(',')]
            # debug print(f"got {len(data)} analysis in {data}")
            context = {'context': compile_analysis_for_composer(data)}
            return render(request, 'core/composer.html', context)
        else:
            context = {'context': Analysis.objects.all()}
            return render(request, 'core/project_select.html', context)


def index(request):
    return HttpResponse("Hello, world. You're at the core index.")


@login_required
def export_risks_csv(request, analysis):
    ra = get_object_or_404(Analysis, pk=analysis)
    # TODO: check permissions

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="RA-{ra.id}-{ra.project}-v-{ra.version}.csv"'

    writer = csv.writer(response, delimiter=';')
    columns = ['rid', 'parent_risk', 'title', 'scenario',
               'existing_measures', 'current_level', 'mitigations', 'residual_level',
               'treatment']
    writer.writerow(columns)

    for ri in ra.riskinstance_set.all():
        mitigations = ''
        for mtg in ri.mitigation_set.all():
            mitigations += f"[{mtg.status}]{mtg.title} \n"
        row = [ri.rid(), ri.parent_risk, ri.title, ri.scenario,
               ri.existing_measures, ri.get_current_level_display(),
               mitigations, ri.get_residual_level_display(), ri.treatment,
               ]
        writer.writerow(row)

    return response


@login_required
def export_mp_csv(request, analysis):
    ra = get_object_or_404(Analysis, pk=analysis)
    # TODO: check permissions

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="MP-{ra.id}-{ra.project}-v-{ra.version}.csv"'

    writer = csv.writer(response, delimiter=';')
    columns = ['rid', 'risk_title',
               'mtg_id', 'mtg_title', 'mtg_desc', 'type', 'solution', 'eta', 'effort', 'link', 'status',
               ]
    writer.writerow(columns)

    for mtg in Mitigation.objects.filter(risk_instance__analysis=analysis):
        row = [mtg.risk_instance.rid(), mtg.risk_instance.title,
               mtg.id, mtg.title, mtg.description, mtg.type, mtg.solution, mtg.eta, mtg.effort, mtg.link, mtg.status,
               ]
        writer.writerow(row)

    return response


def scoring_assistant(request):
    template = 'core/scoring.html'
    context = {}
    return render(request, template, context)


def show_risk_matrix(request):
    template = 'core/risk_matrix.html'
    context = {}
    return render(request, template, context)