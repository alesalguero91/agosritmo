# pdfparser/serializers.py
# serializer.py

from rest_framework import serializers

class PDFUploadSerializer(serializers.Serializer):
    pdf_file = serializers.FileField()
    additional_data = serializers.CharField(required=False, allow_blank=True)

class PDFTextResponseSerializer(serializers.Serializer):
    text = serializers.CharField()

class ExcelUploadSerializer(serializers.Serializer):
    excel_file = serializers.FileField()
