from collections import OrderedDict
import datetime
import itertools
import json
import logging
import os
import zipstream

from .query import SampleQuery
from .util import val_or_empty
from .otu import SampleContext

logger = logging.getLogger('rainbow')


def generate_biom_file(query):
    otu_to_row = {}
    sample_to_column = {}

    otus = otu_rows(query, otu_to_row)
    samples = sample_columns(query, sample_to_column)
    abundance_table = abundance_tbl(query, otu_to_row, sample_to_column)
    shape = (str(len(x)) for x in (otu_to_row, sample_to_column))

    return itertools.chain(
        biom_header(),
        wrap('"rows": [', otus, '],\n'),
        wrap('"columns": [', samples, '],\n'),
        wrap('"shape": [', shape, '],\n'),
        wrap('"data": [', abundance_table, ']}\n'))


def biom_zip_file_generator(params, timestamp):
    zf = zipstream.ZipFile(mode='w', compression=zipstream.ZIP_DEFLATED)
    with SampleQuery(params) as query:
        zf.write_iter("BiomExport-{}.biom".format(timestamp), (s.encode('utf8') for s in generate_biom_file(query)))
    return zf


def save_biom_zip_file(params, dir='/data'):
    timestamp = datetime.datetime.now().replace(microsecond=0).isoformat().replace(':', '')

    filename = os.path.join(dir, 'BiomExport-{}.biom.zip'.format(timestamp))
    zf = biom_zip_file_generator(params, timestamp)
    with open(filename, 'wb') as f:
        for data in zf:
            f.write(data)
    return filename


def biom_header():
    '''
    Write out the JSON file header first
    '''
    biom_file = OrderedDict((
        ('id', None),
        ('format', '1.0.0'),
        ('format_url', 'http://biom-format.org'),
        ('type', 'OTU table'),
        ('generated_by', 'Bioplatforms Australia'),
        ('date', datetime.datetime.now().replace(microsecond=0).isoformat()),
        ('matrix_type', 'sparse'),
        ('matrix_element_type', 'int')))

    headers = ',\n'.join(k_v(k, v) for k, v in biom_file.items())

    biom_header = '{%s,\n' % headers

    yield biom_header


def otu_rows(query, otu_to_row):
    q = query.matching_otus()
    taxonomy_fields = ('kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species')

    for idx, otu in enumerate(q.yield_per(50)):
        def get_value(attr):
            if attr == 'class':
                attr = 'klass'
            return val_or_empty(getattr(otu, attr))

        otu_to_row[otu.id] = idx
        taxonomy_array = [get_value(f) for f in taxonomy_fields]
        yield '{"id": "%s","metadata": {%s,%s}}' % (
            otu.code,
            k_v('amplicon', get_value('amplicon')),
            k_v('taxonomy', taxonomy_array))


def sample_columns(query, sample_to_column):
    def empty_to_none(v):
        # FIXME: push this back in the core metadata handling
        if v == '':
            return None
        return v

    def get_context_value(sample, field):
        return empty_to_none(getattr(sample, field))

    all_fields = [k.name for k in SampleContext.__table__.columns if k.name != 'id']
    non_empty = set()

    # do a first pass through and determine the relevant metadata fields for this export
    for sample in query.matching_samples():
        for field in all_fields:
            if get_context_value(sample, field) is not None:
                non_empty.add(field)

    fields = list(non_empty)
    fields.sort()

    # This is a cached query so all results are returned. Just iterate through without chunking.
    for idx, sample in enumerate(s for s in query.matching_samples() if s.id not in sample_to_column):
        sample_to_column[sample.id] = idx
        metadata = ','.join(k_v(f, get_context_value(sample, f)) for f in fields)
        sample_data = '{"id": "102.100.100/%s","metadata": {%s}}' % (sample.id, metadata)

        yield sample_data


def abundance_tbl(query, otu_to_row, sample_to_column):
    q = query.matching_sample_otus()

    for otu, sampleotu, samplecontext in q.yield_per(50):
        # a little messy, but this is our busiest bit of code in the
        # entire BIOM output process
        yield '[' + \
            str(otu_to_row[sampleotu.otu_id]) + \
            ',' + \
            str(sample_to_column[sampleotu.sample_id]) + \
            ',' + \
            str(sampleotu.count) + \
            ']'


def k_v(k, v):
    if isinstance(v, datetime.date):
        v = str(v)
    return json.dumps(k) + ':' + json.dumps(v)


def wrap(pre, it, post, sep=','):
    yield pre

    for x in interpose(it, sep):
        yield x

    yield post


def interpose(it, sep=','):
    try:
        yield next(it)
    except StopIteration:
        return
    for x in it:
        yield sep
        yield x
