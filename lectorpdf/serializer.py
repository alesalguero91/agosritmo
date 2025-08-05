# pdfparser/serializers.py
# serializer.py

from rest_framework import serializers

class PDFUploadSerializer(serializers.Serializer):
    pdf_file = serializers.FileField(required=True)
    additional_data = serializers.CharField(required=True)
    excel_file = serializers.FileField(required=True)

    class Meta:
        fields = ['pdf_file', 'additional_data', 'excel_file']



class PDFTextResponseSerializer(serializers.Serializer):
    text = serializers.CharField()

class ExcelUploadSerializer(serializers.Serializer):
    excel_file = serializers.FileField()

from rest_framework import serializers


