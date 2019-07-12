import csv
import datetime
import gzip
import logging
import os
import tempfile
import traceback
import uuid
import re
from collections import OrderedDict, defaultdict
from glob import glob
from hashlib import md5
from itertools import zip_longest

import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.sql.expression import text

from bpaingest.metadata import DownloadMetadata
from bpaingest.projects.amdb.contextual import \
    AustralianMicrobiomeSampleContextual
from bpaingest.projects.amdb.ingest import AccessAMDContextualMetadata

from .models import (ImportFileLog, ImportMetadata, ImportOntologyLog,
                     ImportSamplesMissingMetadataLog)
from .otu import (OTU, SCHEMA, Base, Environment, OTUAmplicon, OTUClass,
                  OTUFamily, OTUGenus, OTUKingdom, OTUOrder, OTUPhylum,
                  OTUSpecies, SampleAustralianSoilClassification, SampleColor,
                  SampleContext, SampleEcologicalZone,
                  SampleFAOSoilClassification, SampleHorizonClassification,
                  SampleLandUse, SampleOTU, SampleProfilePosition,
                  SampleStorageMethod, SampleTillage, SampleType,
                  SampleVegetationType, make_engine)

logger = logging.getLogger("rainbow")


class ImportException(Exception):
    pass


def try_int(s):
    try:
        return int(s)
    except ValueError:
        return None


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def otu_hash(code, amplicon_id):
    return md5('{},{}'.format(code, amplicon_id).encode('ascii')).digest()


class DataImporter:
    # note: some files have species, some don't
    amd_ontologies = OrderedDict([
        ('environment', Environment),
        ('sample_type', SampleType),
        ('horizon_classification', SampleHorizonClassification),
        ('soil_sample_storage_method', SampleStorageMethod),
        ('broad_land_use', SampleLandUse),
        ('detailed_land_use', SampleLandUse),
        ('general_ecological_zone', SampleEcologicalZone),
        ('vegetation_type', SampleVegetationType),
        ('profile_position', SampleProfilePosition),
        ('australian_soil_classification', SampleAustralianSoilClassification),
        ('fao_soil_classification', SampleFAOSoilClassification),
        ('immediate_previous_land_use', SampleLandUse),
        ('tillage', SampleTillage),
        ('color', SampleColor),
    ])

    def __init__(self, import_base, revision_date):
        self.amplicon_code_names = {}  # mapping from dirname to amplicon ontology
        self._clear_import_log()
        self._engine = make_engine()
        self._create_extensions()
        self._session = sessionmaker(bind=self._engine)()
        self._import_base = import_base
        self._revision_date = revision_date
        try:
            self._session.execute(DropSchema(SCHEMA, cascade=True))
        except sqlalchemy.exc.ProgrammingError:
            self._session.invalidate()
        self._session.execute(CreateSchema(SCHEMA))
        self._session.commit()
        Base.metadata.create_all(self._engine)
        self.ontology_init()

    def ontology_init(self):
        # set blank as an option for all ontologies, bar Environment
        all_cls = set(
            c for c
            in list(self.amd_ontologies.values())
            if c is not Environment)
        # Species is the only potentially blank taxonomy
        all_cls.add(OTUSpecies)
        for db_class in all_cls:
            instance = db_class(id=0, value='')
            self._session.add(instance)
        self._session.commit()

    def complete(self):
        self._write_metadata()
        self._session.close()
        self._analyze()

    def _write_metadata(self):
        ImportMetadata.objects.all().delete()
        meta = ImportMetadata(
            methodology='v1',
            revision_date=datetime.datetime.strptime(self._revision_date, "%Y-%m-%d").date(),
            imported_at=datetime.date.today(),
            uuid=str(uuid.uuid4()),
            sampleotu_count=self._session.query(SampleOTU).count(),
            samplecontext_count=self._session.query(SampleContext).count(),
            otu_count=self._session.query(OTU).count())
        meta.save()

    def _clear_import_log(self):
        logger.info("Clearing import log")
        for log_cls in (ImportSamplesMissingMetadataLog, ImportFileLog, ImportOntologyLog):
            log_cls.objects.all().delete()

    def _create_extensions(self):
        extensions = ('citext',)
        for extension in extensions:
            try:
                logger.info("creating extension: %s" % extension)
                self._engine.execute('CREATE EXTENSION %s;' % extension)
            except sqlalchemy.exc.ProgrammingError as e:
                if 'already exists' not in str(e):
                    logger.critical("couldn't create extension: %s (%s)" % (extension, e))

    def _analyze(self):
        logger.info("Completing ingest: analyze")
        self._engine.execute('ANALYZE;')

    def _build_ontology(self, db_class, vals):
        for val in sorted(vals):
            # this option is defined at import init
            if val == '':
                continue
            instance = db_class(value=val)
            self._session.add(instance)
        self._session.commit()
        return dict((t.value, t.id) for t in self._session.query(db_class).all())

    def _load_ontology(self, ontology_defn, row_iter, key_set=set()):
        # import the ontologies, and build a mapping from
        # permitted values into IDs in those ontologies
        by_class = defaultdict(list)
        for field, db_class in ontology_defn.items():
            by_class[db_class].append(field)

        vals = defaultdict(set)
        for row in row_iter:
            key_set.update(row.keys())
            for db_class, fields in by_class.items():
                for field in fields:
                    if field in row:
                        vals[db_class].add(row[field])

        # blow up if any of the ontologies hasn't worked
        for db_class, val_set in vals.items():
            if len(val_set) == 0:
                raise ImportException("empty ontology: {}".format(db_class))

        mappings = {}
        for db_class, fields in by_class.items():
            map_dict = self._build_ontology(db_class, vals[db_class])
            for field in fields:
                mappings[field] = map_dict
        return mappings

    @classmethod
    def classify_fields(cls, environment_lookup):
        # flip around to name -> id
        pl = dict((t[1], t[0]) for t in environment_lookup.items())

        soil_fields = set()
        marine_fields = set()
        for sheet_name, fields in AustralianMicrobiomeSampleContextual.field_specs.items():
            environment = AustralianMicrobiomeSampleContextual.environment_for_sheet(sheet_name)
            for field_info in fields:
                field_name = field_info[0]
                if field_name in DataImporter.amd_ontologies:
                    field_name += '_id'
                elif field_name == 'sample_id':
                    field_name = 'id'
                if environment == 'Soil':
                    soil_fields.add(field_name)
                else:
                    marine_fields.add(field_name)
        soil_only = soil_fields - marine_fields
        marine_only = marine_fields - soil_fields
        r = {}
        r.update((t, pl['Soil']) for t in soil_only)
        r.update((t, pl['Marine']) for t in marine_only)
        return r

    def amplicon_files(self, pattern):
        for fname in glob(self._import_base + '/*/' + pattern):
            amplicon = fname.split('/')[-2]
            yield amplicon, fname

    def load_taxonomies(self):
        # md5(otu code) -> otu ID, returned

        otu_lookup = {}
        taxonomy_fields = [
            'id', 'code',
            # order here must match `ontologies' below
            'kingdom_id', 'phylum_id', 'class_id', 'order_id', 'family_id', 'genus_id', 'species_id', 'amplicon_id']
        ontologies = OrderedDict([
            ('kingdom', OTUKingdom),
            ('phylum', OTUPhylum),
            ('class', OTUClass),
            ('order', OTUOrder),
            ('family', OTUFamily),
            ('genus', OTUGenus),
            ('species', OTUSpecies),
            ('amplicon', OTUAmplicon),
        ])

        def _taxon_rows_iter():
            code_re = re.compile(r'^[GATC]+')
            otu_header = '#OTU ID'
            amplicon_header = 'amplicon'
            for amplicon_code, fname in self.amplicon_files('*.taxonomy.gz'):
                logger.warning('reading taxonomy file: %s' % fname)
                amplicon = None
                with gzip.open(fname, 'rt') as fd:
                    reader = csv.reader(fd, dialect='excel-tab')
                    header = next(reader)
                    assert(header[0] == otu_header)
                    assert(header[-1] == amplicon_header)
                    taxo_header = header[1:-1]
                    for idx, row in enumerate(csv.reader(fd, dialect='excel-tab')):
                        code = row[0]
                        if not code_re.match(code) and not code.startswith('mxa_'):
                            raise Exception("invalid OTU code: {}".format(code))
                        obj = {
                            'amplicon': row[-1],
                            'otu': code,
                        }
                        if amplicon is None:
                            amplicon = obj['amplicon']
                        if amplicon != obj['amplicon']:
                            raise Exception(
                                'more than one amplicon in folder: {} vs {}'.format(amplicon, obj['amplicon']))
                        obj.update(zip(taxo_header, row[1:-1]))
                        yield obj
                self.amplicon_code_names[amplicon_code.lower()] = amplicon
                ImportFileLog.make_file_log(fname, file_type='Taxonomy', rows_imported=idx + 1, rows_skipped=0)

        logger.warning("loading taxonomies - pass 1, defining ontologies")
        mappings = self._load_ontology(ontologies, _taxon_rows_iter())

        logger.warning("loading taxonomies - pass 2, defining OTUs")
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir='/data', prefix='bpaotu-', delete=False) as temp_fd:
                fname = temp_fd.name
                os.chmod(fname, 0o644)
                logger.warning("writing out taxonomy data to CSV tempfile: %s" % fname)
                w = csv.writer(temp_fd)
                w.writerow(taxonomy_fields)
                for _id, row in enumerate(_taxon_rows_iter(), 1):
                    otu_key = otu_hash(row['otu'], row['amplicon'])
                    assert(otu_key not in otu_lookup)
                    otu_lookup[otu_key] = _id

                    otu_row = [_id, row['otu']]
                    for field in ontologies:
                        val = row.get(field, '')
                        otu_row.append(mappings[field][val])
                    w.writerow(otu_row)
            logger.warning("loading taxonomy data from temporary CSV file")
            self._engine.execute(
                text('''COPY otu.otu from :csv CSV header''').execution_options(autocommit=True),
                csv=fname)
        finally:
            os.unlink(fname)
        return otu_lookup

    def save_ontology_errors(self, environment_ontology_errors):
        if environment_ontology_errors is None:
            return
        for (environment, ontology_name), invalid_values in environment_ontology_errors.items():
            log = ImportOntologyLog(
                environment=environment,
                ontology_name=ontology_name,
                invalid_values=sorted(invalid_values))
            log.save()

    def contextual_rows(self, ingest_cls, name):
        # flatten contextual metadata into dicts
        metadata = defaultdict(dict)
        with DownloadMetadata(ingest_cls, path='/data/{}/'.format(name)) as dlmeta:
            for contextual_source in dlmeta.meta.contextual_metadata:
                self.save_ontology_errors(
                    getattr(contextual_source, "environment_ontology_errors", None))
                for sample_id in contextual_source.sample_ids():
                    metadata[sample_id]['sample_id'] = sample_id
                    metadata[sample_id].update(contextual_source.get(sample_id))

        def has_minimum_metadata(row):
            return 'latitude' in row and 'longitude' in row \
                and isinstance(row['latitude'], float) and isinstance(row['longitude'], float)

        # convert into a row-like structure
        return list([t for t in metadata.values() if has_minimum_metadata(t)])

    def contextual_row_context(self, metadata, ontologies, mappings, fields_used):
        for row in metadata:
            sample_id = row['sample_id']
            if sample_id is None:
                continue
            attrs = {
                'id': int(sample_id.split('/')[-1])
            }
            for field in ontologies:
                if field not in row:
                    continue
                attrs[field + '_id'] = mappings[field][row[field]]
            for field, value in row.items():
                if field in attrs or (field + '_id') in attrs or field == 'sample_id':
                    continue
                attrs[field] = value
            fields_used.update(set(attrs.keys()))
            yield SampleContext(**attrs)

    def load_contextual_metadata(self):
        # we have a bit of a broken window in the SampleContext class, so we
        # check whether or not we are using all the fields to assist us when
        # updating the code for new versions of the source spreadsheet
        utilised_fields = set()
        logger.warning("loading Soil contextual metadata")
        metadata = self.contextual_rows(AccessAMDContextualMetadata, name='amd-metadata')
        mappings = self._load_ontology(DataImporter.amd_ontologies, metadata)
        for obj in self.contextual_row_context(metadata, DataImporter.amd_ontologies, mappings, utilised_fields):
            self._session.add(obj)
            self._session.commit()
        self._session.commit()
        unused = set(t.name for t in SampleContext.__table__.columns) - utilised_fields
        if unused:
            logger.info("Unutilised fields:")
            for field in sorted(unused):
                logger.info(field)

    def _otu_abundance_rows(self, fd, amplicon_code, otu_lookup):
        reader = csv.reader(fd, dialect='excel-tab')
        header = next(reader)

        assert(header == ["#OTU ID", "Sample_only", "Abundance"])
        valid_sample_re = re.compile(r'^[0-9]+$')
        skipped_invalid = set()

        def _tuplerows():
            seen_invalid = set()
            seen_unknown = set()
            for otu_code, sample_id, count in reader:
                float_count = float(count)
                int_count = int(float_count)
                # make sure that fractional values don't creep in on a future ingest
                assert(int_count - float_count == 0)
                # strict conversion to integer, as we've got other things mixed in here
                if not valid_sample_re.match(sample_id):
                    if sample_id not in skipped_invalid:
                        logger.warning('skipped non-Bioplatforms sample ID: {}'.format(sample_id))
                        skipped_invalid.add(sample_id)
                    continue
                sample_id_int = int(sample_id)
                if sample_id_int is None:
                    if sample_id not in seen_invalid:
                        logger.info('skipping invalid sample ID: {}'.format(sample_id))
                        seen_invalid.add(sample_id)
                    continue
                otu_id = otu_lookup.get(otu_hash(otu_code, self.amplicon_code_names[amplicon_code.lower()]))
                if otu_id is None:
                    if otu_code not in seen_unknown:
                        logger.critical('skipping unknown OTU code: {}'.format(otu_code))
                        seen_unknown.add(otu_code)
                    continue
                yield otu_id, sample_id_int, int_count

        return _tuplerows()

    def _find_missing_sample_ids(self, otu_lookup):
        def _missing_sample_ids(amplicon_code, fname):
            have_sampleids = set([t[0] for t in self._session.query(SampleContext.id)])
            with gzip.open(fname, 'rt') as fd:
                entries = self._otu_abundance_rows(fd, amplicon_code, otu_lookup)
                sample_ids = set(t[1] for t in entries)
                for sample_id in sample_ids:
                    if sample_id not in have_sampleids:
                        yield sample_id

        missing_sample_ids = set()
        for amplicon_code, fname in self.amplicon_files('*.txt.gz'):
            logger.warning("first pass, reading from: %s" % (fname))
            missing_sample_ids |= set(_missing_sample_ids(amplicon_code, fname))
        return missing_sample_ids

    def load_otu_abundance(self, otu_lookup):
        def _make_sample_otus(fname, amplicon_code, skip_missing):
            with gzip.open(fname, 'rt') as fd:
                tuple_rows = self._otu_abundance_rows(fd, amplicon_code, otu_lookup)
                rows_skipped = 0
                for entry, (otu_id, sample_id, count) in enumerate(tuple_rows):
                    if sample_id in skip_missing:
                        rows_skipped += 1
                        continue
                    yield (sample_id, otu_id, count)
                ImportFileLog.make_file_log(
                    fname, file_type='Abundance', rows_imported=entry, rows_skipped=rows_skipped)

        logger.warning('Loading OTU abundance tables')

        missing_sample_ids = self._find_missing_sample_ids(otu_lookup)
        if missing_sample_ids:
            il = ImportSamplesMissingMetadataLog(samples_without_metadata=list(sorted(missing_sample_ids)))
            il.save()

        for amplicon_code, sampleotu_fname in self.amplicon_files('*.txt.gz'):
            try:
                logger.warning("second pass, reading from: %s" % (sampleotu_fname))
                with tempfile.NamedTemporaryFile(mode='w', dir='/data', prefix='bpaotu-', delete=False) as temp_fd:
                    fname = temp_fd.name
                    os.chmod(fname, 0o644)
                    logger.warning("writing out OTU abundance data to CSV tempfile: %s" % fname)
                    w = csv.writer(temp_fd)
                    w.writerow(['sample_id', 'otu_id', 'count'])
                    w.writerows(_make_sample_otus(sampleotu_fname, amplicon_code, missing_sample_ids))
                logger.warning("loading OTU abundance data from temporary CSV file")
                try:
                    self._engine.execute(
                        text('''COPY otu.sample_otu from :csv CSV header''').execution_options(autocommit=True),
                        csv=fname)
                except:  # noqa
                    logger.critical("unable to import %s" % (sampleotu_fname))
                    traceback.print_exc()
            finally:
                os.unlink(fname)
