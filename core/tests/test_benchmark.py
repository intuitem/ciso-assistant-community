import timeit

# Create your tests here.

setup_code = '''
from core.models import Analysis
from general.models import Project
from django.shortcuts import get_object_or_404
'''

statement = '''
analyses = []
batch_size = 2500
for i in range(10000):
    analysis = Analysis()
    project = Project.objects.get(id=1)
    analysis.project = project
    analysis.comments = "Lorem ipsum dolor sir amet..."
    analyses.append(analysis)
Analysis.objects.bulk_create(analyses, batch_size)
'''

s2 =  '''
analysis = Analysis.objects.filter(is_draft=True)
'''

print(f'Execution time is: {timeit.timeit(setup=setup_code, stmt=statement, number=1)}')
print(f'Execution time is: {timeit.timeit(setup=setup_code, stmt=s2, number=1)}')

# def analysis_bulk_create_test(n, b):
#     analyses = []
#     batch_size = 500
#     for i in range(1000):
#         analysis = Analysis()
#         analysis.project = get_object_or_404(Project, id=1)
#         analysis.comments = "Lorem ipsum dolor sir amet..."
#         analyses.append(analysis)
#     Analysis.objects.bulk_create(analyses, batch_size)