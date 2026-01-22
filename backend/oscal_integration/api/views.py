"""
OSCAL Integration API Views

Django REST Framework views for OSCAL import/export and FedRAMP validation.
"""

import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.core.files.base import ContentFile

from ..services.oscal_importer import OSCALImporter
from ..services.oscal_exporter import OSCALExporter
from ..services.fedramp_validator import FedRAMPValidator
from ..services.ssp_generator import SSPGenerator


class OSCALImportViewSet(viewsets.ViewSet):
    """ViewSet for OSCAL import operations"""

    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.importer = OSCALImporter()

    @action(detail=False, methods=['post'])
    def import_file(self, request):
        """Import OSCAL file"""
        try:
            file_obj = request.FILES.get('file')
            if not file_obj:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Read file content
            file_content = file_obj.read().decode('utf-8')

            # Detect format
            format_type = self.importer.detect_format(file_content)
            if not format_type:
                return Response(
                    {'error': 'Unable to detect OSCAL format'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate content
            validation = self.importer.validate_oscal_content(file_content)
            if not validation['valid']:
                return Response({
                    'error': 'Invalid OSCAL content',
                    'validation_errors': validation['errors']
                }, status=status.HTTP_400_BAD_REQUEST)

            # Import the file
            import_result = self.importer.import_file(file_content, format_type)

            # Convert to CISO Assistant entities
            entities = self.importer.convert_to_ciso_assistant_entities(import_result)

            return Response({
                'message': 'OSCAL file imported successfully',
                'format_detected': format_type,
                'import_result': import_result,
                'entities_created': entities,
                'validation': validation
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate OSCAL content"""
        try:
            content = request.data.get('content')
            if not content:
                return Response(
                    {'error': 'No content provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            validation = self.importer.validate_oscal_content(content)

            return Response({
                'valid': validation['valid'],
                'errors': validation['errors'],
                'warnings': validation['warnings'],
                'oscal_version': validation['oscal_version'],
                'format_detected': validation['format_detected']
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OSCALExportViewSet(viewsets.ViewSet):
    """ViewSet for OSCAL export operations"""

    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exporter = OSCALExporter()

    @action(detail=True, methods=['get'])
    def ssp(self, request, pk=None):
        """Export compliance assessment as OSCAL SSP"""
        try:
            oscal_ssp = self.exporter.export_compliance_assessment(pk)

            # Validate export
            validation = self.exporter.validate_export(oscal_ssp)

            response = HttpResponse(
                oscal_ssp,
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="ssp_{pk}.json"'

            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def catalog(self, request, pk=None):
        """Export framework as OSCAL catalog"""
        try:
            oscal_catalog = self.exporter.export_framework_as_catalog(pk)

            response = HttpResponse(
                oscal_catalog,
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="catalog_{pk}.json"'

            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def assessment_plan(self, request, pk=None):
        """Export assessment as OSCAL assessment plan"""
        try:
            oscal_plan = self.exporter.export_assessment_plan(pk)

            response = HttpResponse(
                oscal_plan,
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="assessment_plan_{pk}.json"'

            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def assessment_results(self, request, pk=None):
        """Export assessment results as OSCAL"""
        try:
            oscal_results = self.exporter.export_assessment_results(pk)

            response = HttpResponse(
                oscal_results,
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="assessment_results_{pk}.json"'

            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def poam(self, request, pk=None):
        """Export POA&M as OSCAL"""
        try:
            oscal_poam = self.exporter.export_poam(pk)

            response = HttpResponse(
                oscal_poam,
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="poam_{pk}.json"'

            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FedRAMPValidationViewSet(viewsets.ViewSet):
    """ViewSet for FedRAMP validation operations"""

    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validator = FedRAMPValidator()

    @action(detail=False, methods=['post'])
    def validate_ssp(self, request):
        """Validate OSCAL SSP against FedRAMP baseline"""
        try:
            ssp_content = request.data.get('ssp_content')
            baseline = request.data.get('baseline', 'moderate')

            if not ssp_content:
                return Response(
                    {'error': 'SSP content is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            validation_result = self.validator.validate_ssp(ssp_content, baseline)

            return Response({
                'baseline': baseline,
                'validation_passed': validation_result.get('validation_passed', False),
                'errors': validation_result.get('errors', []),
                'warnings': validation_result.get('warnings', []),
                'svrl_report': validation_result.get('svrl_report'),
                'html_report': validation_result.get('html_report'),
                'compliance_summary': self.validator._generate_compliance_summary(validation_result)
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def generate_report(self, request):
        """Generate comprehensive FedRAMP validation report"""
        try:
            ssp_content = request.data.get('ssp_content')
            baseline = request.data.get('baseline', 'moderate')

            if not ssp_content:
                return Response(
                    {'error': 'SSP content is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            report = self.validator.generate_fedramp_report(ssp_content, baseline)

            return Response(report)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def baselines(self, request):
        """List available FedRAMP baselines"""
        try:
            baselines = self.validator.list_available_baselines()
            baseline_info = {}

            for baseline in baselines:
                baseline_info[baseline] = self.validator.get_baseline_requirements(baseline)

            return Response({
                'baselines': baselines,
                'baseline_info': baseline_info
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def validate_baseline_compatibility(self, request):
        """Validate SSP compatibility across all baselines"""
        try:
            ssp_content = request.data.get('ssp_content')

            if not ssp_content:
                return Response(
                    {'error': 'SSP content is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            compatibility = self.validator.validate_baseline_compatibility(ssp_content)

            return Response({
                'compatibility_results': compatibility
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SSPGenerationViewSet(viewsets.ViewSet):
    """ViewSet for SSP document generation"""

    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generator = SSPGenerator()

    @action(detail=True, methods=['post'])
    def generate_appendix_a(self, request, pk=None):
        """Generate FedRAMP SSP Appendix A Word document"""
        try:
            baseline = request.data.get('baseline', 'moderate')

            word_document = self.generator.generate_appendix_a(pk, baseline)

            response = HttpResponse(
                word_document,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="SSP_Appendix_A_{pk}_{baseline}.docx"'

            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def generate_with_customizations(self, request, pk=None):
        """Generate SSP Appendix A with customizations"""
        try:
            baseline = request.data.get('baseline', 'moderate')
            customizations = request.data.get('customizations', {})

            word_document = self.generator.generate_appendix_a_with_customizations(
                pk, baseline, customizations
            )

            response = HttpResponse(
                word_document,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="SSP_Appendix_A_Custom_{pk}_{baseline}.docx"'

            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def validate_for_generation(self, request, pk=None):
        """Validate SSP readiness for document generation"""
        try:
            baseline = request.query_params.get('baseline', 'moderate')

            validation = self.generator.validate_ssp_for_baseline(pk, baseline)

            return Response(validation)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def preview_content(self, request, pk=None):
        """Preview SSP content before generation"""
        try:
            baseline = request.query_params.get('baseline', 'moderate')

            preview = self.generator.preview_ssp_content(pk, baseline)

            return Response(preview)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def supported_baselines(self, request):
        """List supported FedRAMP baselines"""
        try:
            baselines = self.generator.get_supported_baselines()
            baseline_info = {}

            for baseline in baselines:
                baseline_info[baseline] = self.generator.get_baseline_info(baseline)

            return Response({
                'supported_baselines': baselines,
                'baseline_info': baseline_info
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def generated_documents(self, request, pk=None):
        """List previously generated documents for an assessment"""
        try:
            documents = self.generator.list_generated_documents(pk)

            return Response({
                'assessment_id': pk,
                'generated_documents': documents
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # IMPORT ENDPOINTS

    @action(detail=False, methods=['post'])
    def import_docx(self, request):
        """Import SSP from uploaded Word document"""
        try:
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate file extension
            if not uploaded_file.name.lower().endswith('.docx'):
                return Response(
                    {'error': 'Only .docx files are supported'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Import the document
            import_result = self.generator.import_ssp_from_upload(uploaded_file)

            if not import_result.get('success'):
                return Response({
                    'error': import_result.get('error', 'Import failed'),
                    'filename': uploaded_file.name
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'message': 'SSP document imported successfully',
                'filename': uploaded_file.name,
                'import_result': import_result,
                'oscal_ssp': import_result.get('oscal_ssp'),
                'ciso_entities': import_result.get('ciso_entities'),
                'validation': import_result.get('validation'),
                'document_info': import_result.get('import_metadata')
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def validate_docx(self, request):
        """Validate DOCX file for SSP import"""
        try:
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save temporarily for validation
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            try:
                # Validate the file
                validation_result = self.generator.validate_docx_for_import(temp_file_path)

                return Response({
                    'filename': uploaded_file.name,
                    'valid': validation_result.get('valid', False),
                    'errors': validation_result.get('errors', []),
                    'warnings': validation_result.get('warnings', []),
                    'document_info': validation_result.get('document_info', {})
                })

            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def convert_import_to_assessment(self, request):
        """Convert imported SSP data to a compliance assessment"""
        try:
            import_result = request.data.get('import_result')
            assessment_name = request.data.get('assessment_name')

            if not import_result:
                return Response(
                    {'error': 'import_result is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            conversion_result = self.generator.convert_imported_ssp_to_assessment(
                import_result, assessment_name
            )

            if not conversion_result.get('success'):
                return Response({
                    'error': conversion_result.get('error', 'Conversion failed')
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'message': 'SSP converted to assessment successfully',
                'assessment_data': conversion_result.get('assessment_data'),
                'warnings': conversion_result.get('import_warnings', []),
                'document_info': conversion_result.get('document_info', {})
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def import_capabilities(self, request):
        """Get information about SSP import capabilities"""
        try:
            capabilities = self.generator.get_import_statistics()

            return Response({
                'import_capabilities': capabilities,
                'supported_operations': [
                    'DOCX file upload and parsing',
                    'OSCAL SSP conversion',
                    'CISO Assistant entity creation',
                    'Compliance assessment generation',
                    'Validation and error reporting'
                ],
                'file_requirements': {
                    'format': 'Microsoft Word (.docx)',
                    'max_size': '50MB',
                    'content': 'FedRAMP SSP format preferred'
                }
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
