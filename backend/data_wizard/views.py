import io
import logging
import sys
import pandas as pd
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser
from django.core import management
import json
from .serializers import LoadFileSerializer

logger = logging.getLogger(__name__)


class LoadFileView(APIView):
    parser_classes = (FileUploadParser,)
    serializer_class = LoadFileSerializer

    def process_excel_file(self, request, excel_data):
        # Parse Excel data
        model_type = request.META.get("HTTP_X_MODEL_TYPE")
        folder_id = request.META.get("HTTP_X_FOLDER_ID")
        perimeter_id = request.META.get("HTTP_X_PERIMETER_ID")

        logger.info(
            f"Processing file with model: {model_type}, folder: {folder_id}, perimeter: {perimeter_id}"
        )
        try:
            # Read Excel file into a pandas DataFrame
            df = pd.read_excel(excel_data)
            processed_data = self.convert_excel_to_db_format(df)

        except Exception as e:
            logger.error("Error parsing Excel file", exc_info=e)
            return Response(
                {"error": "ExcelParsingFailed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "File loaded successfully"}, status=status.HTTP_200_OK
        )

    def convert_excel_to_db_format(self, dataframe):
        records = dataframe.to_dict(orient="records")
        print(records)
        logger.warning("I am here")

        formatted_data = []
        for record in records:
            model_data = {
                "model": "yourapp.yourmodel",
                "pk": None,  # You might need to generate or extract this
                "fields": record,
            }
            formatted_data.append(model_data)

        return json.dumps(formatted_data)

    def post(self, request, *args, **kwargs):
        # if not request.user.has_file_permission:
        #     logger.error("Unauthorized user tried to load a file", user=request.user)
        #     return Response({}, status=status.HTTP_403_FORBIDDEN)

        if not request.data:
            logger.error("Request has no data")
            return Response(
                {"error": "fileLoadNoData"}, status=status.HTTP_400_BAD_REQUEST
            )

        file_obj = request.data.get("file")
        if not file_obj:
            logger.error("No file provided")
            return Response(
                {"error": "noFileProvided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the file is an Excel file
        file_extension = file_obj.name.split(".")[-1].lower()
        if file_extension not in ["xlsx", "xls"]:
            logger.error(f"Unsupported file format: {file_extension}")
            return Response(
                {"error": "unsupportedFileFormat"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Read the file content
        file_data = file_obj.read()

        # Process the Excel file
        return self.process_excel_file(request, io.BytesIO(file_data))
