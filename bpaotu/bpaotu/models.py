from django.db import models
from django.contrib.postgres.fields import ArrayField

import os
import logging
logger = logging.getLogger("rainbow")


class ImportMetadata(models.Model):
    methodology = models.CharField(max_length=32)
    revision_date = models.DateField(null=False)
    imported_at = models.DateField(null=False)
    otu_count = models.BigIntegerField(null=False)
    sampleotu_count = models.BigIntegerField(null=False)
    samplecontext_count = models.BigIntegerField(null=False)
    uuid = models.CharField(max_length=36, null=False)


class ImportFileLog(models.Model):
    filename = models.CharField(max_length=300, primary_key=True)
    file_type = models.CharField(max_length=300)
    file_size = models.BigIntegerField()
    rows_imported = models.BigIntegerField()
    rows_skipped = models.BigIntegerField()

    class Meta:
        ordering = ['file_type', 'filename']

    @classmethod
    def make_file_log(cls, filename, **defaults):
        defaults['file_size'] = os.stat(filename).st_size
        ImportFileLog.objects.get_or_create(
            filename=os.path.basename(filename),
            defaults=defaults)


class ImportOntologyLog(models.Model):
    environment = models.CharField(max_length=300)
    ontology_name = models.CharField(max_length=300)
    invalid_values = ArrayField(models.TextField())

    class Meta:
        ordering = ['environment', 'ontology_name']

    def __str__(self):
        return self.ontology_name


class ImportSamplesMissingMetadataLog(models.Model):
    reason = models.CharField(max_length=32, unique=True)
    samples = ArrayField(models.TextField())
