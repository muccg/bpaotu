from collections import defaultdict, OrderedDict
import csv
import datetime
import hmac
import io
import json
import logging
import os
import re
import time
import traceback

from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView
from django.http import JsonResponse, StreamingHttpResponse, Http404, HttpResponse

from .ckan_auth import require_CKAN_auth
from .importer import DataImporter
from .spatial import spatial_query
from .otu import (
    Environment,
    SampleContext,
    OTUAmplicon)
from .query import (
    OTUQueryParams,
    TaxonomyOptions,
    OntologyInfo,
    SampleQuery,
    ContextualFilter,
    ContextualFilterTermDate,
    ContextualFilterTermFloat,
    ContextualFilterTermOntology,
    ContextualFilterTermSampleID,
    ContextualFilterTermString,
    TaxonomyFilter,
    get_sample_ids)
from django.template import loader
from .models import (
    ImportFileLog,
    ImportOntologyLog,
    ImportSamplesMissingMetadataLog)
from .util import (
    display_name,
    make_timestamp)
from .biom import biom_zip_file_generator
from .tabular import tabular_zip_file_generator
from . import tasks

logger = logging.getLogger("rainbow")


# See datatables.net serverSide documentation for details
ORDERING_PATTERN = re.compile(r'^order\[(\d+)\]\[(dir|column)\]$')
COLUMN_PATTERN = re.compile(r'^columns\[(\d+)\]\[(data|name|searchable|orderable)\]$')


class OTUError(Exception):
    def __init__(self, *errors):
        self.errors = errors


def make_environment_lookup():
    with OntologyInfo() as info:
        return dict(info.get_values(Environment))


class OTUSearch(TemplateView):
    template_name = 'bpaotu/search.html'
    base_url = settings.BASE_URL
    ckan_base_url = settings.CKAN_SERVERS[0]['base_url']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['base_url'] = settings.BASE_URL
        context['galaxy_base_url'] = settings.GALAXY_BASE_URL
        context['ckan_base_url'] = settings.CKAN_SERVERS[0]['base_url']
        context['ckan_check_permissions_url'] = settings.CKAN_CHECK_PERMISSIONS_URL if settings.PRODUCTION else reverse('dev_only_ckan_check_permissions')
        context['ckan_auth_integration'] = settings.CKAN_AUTH_INTEGRATION
        context['galaxy_integration'] = settings.GALAXY_INTEGRATION

        return context


def int_if_not_already_none(v):
    if v is None or v == '':
        return None
    v = str(v)  # let's not let anything odd through
    return int(v)


def get_operator_and_int_value(v):
    if v is None or v == '':
        return None
    if v.get('value', '') == '':
        return None
    return OrderedDict((
        ('operator', v.get('operator', '=')),
        ('value', int_if_not_already_none(v['value'])),
    ))


clean_amplicon_filter = get_operator_and_int_value
clean_environment_filter = get_operator_and_int_value


def clean_taxonomy_filter(state_vector):
    """
    take a taxonomy filter (a list of phylum, kingdom, ...) and clean it
    so that it is a simple list of ints or None of the correct length.
    """

    assert(len(state_vector) == len(TaxonomyOptions.hierarchy))
    return TaxonomyFilter(list(map(
        get_operator_and_int_value,
        state_vector)))


@require_CKAN_auth
@require_GET
def amplicon_options(request):
    """
    private API: return the possible amplicons
    """
    with OntologyInfo() as options:
        vals = options.get_values(OTUAmplicon)
    return JsonResponse({
        'possibilities': vals
    })


@require_CKAN_auth
@require_GET
def taxonomy_options(request):
    """
    private API: given taxonomy constraints, return the possible options
    """
    with TaxonomyOptions() as options:
        amplicon = clean_amplicon_filter(json.loads(request.GET['amplicon']))
        selected = clean_taxonomy_filter(json.loads(request.GET['selected']))
        possibilities = options.possibilities(amplicon, selected)
    return JsonResponse({
        'possibilities': possibilities
    })


@require_CKAN_auth
@require_GET
def contextual_fields(request):
    """
    private API: return the available fields, and their types, so that
    the contextual filtering UI can be built
    """
    fields_by_type = defaultdict(list)

    classifications = DataImporter.classify_fields(make_environment_lookup())

    ontology_classes = {}

    # group together columns by their type. note special case
    # handling for our ontology linkage columns
    for column in SampleContext.__table__.columns:
        if column.name == 'id':
            continue
        if hasattr(column, "ontology_class"):
            ty = '_ontology'
            ontology_classes[column.name] = column.ontology_class
        else:
            ty = str(column.type)
        fields_by_type[ty].append((column.name, getattr(column, 'units', None)))

    def make_defn(typ, name, units, **kwargs):
        environment = classifications.get(name)
        r = kwargs.copy()
        r.update({
            'type': typ,
            'name': name,
            'environment': environment
        })
        if units:
            r['units'] = units
        return r

    definitions = [make_defn('sample_id', 'id', None, display_name='Sample ID', values=list(sorted(get_sample_ids())))]
    for field_name, units in fields_by_type['DATE']:
        definitions.append(make_defn('date', field_name, units))
    for field_name, units in fields_by_type['FLOAT']:
        definitions.append(make_defn('float', field_name, units))
    for field_name, units in fields_by_type['CITEXT']:
        definitions.append(make_defn('string', field_name, units))
    with OntologyInfo() as info:
        for field_name, units in fields_by_type['_ontology']:
            ontology_class = ontology_classes[field_name]
            definitions.append(make_defn('ontology', field_name, units, values=info.get_values(ontology_class)))
    for defn in definitions:
        if 'display_name' not in defn:
            defn['display_name'] = display_name(defn['name'])

    definitions.sort(key=lambda x: x['display_name'])

    return JsonResponse({
        'definitions': definitions
    })


def param_to_filters(query_str):
    """
    take a JSON encoded query_str, validate, return any errors
    and the filter instances
    """

    def parse_date(s):
        try:
            return datetime.datetime.strptime(s, '%Y-%m-%d').date()
        except ValueError:
            return datetime.datetime.strptime(s, '%d/%m/%Y').date()

    def parse_float(s):
        try:
            return float(s)
        except ValueError:
            return None

    otu_query = json.loads(query_str)
    taxonomy_filter = clean_taxonomy_filter(otu_query['taxonomy_filters'])
    amplicon_filter = clean_amplicon_filter(otu_query['amplicon_filter'])

    context_spec = otu_query['contextual_filters']
    contextual_filter = ContextualFilter(context_spec['mode'], context_spec['environment'])

    errors = []

    for filter_spec in context_spec['filters']:
        field_name = filter_spec['field']
        if field_name not in SampleContext.__table__.columns:
            errors.append("Please select a contextual data field to filter upon.")
            continue
        operator = filter_spec.get('operator')
        column = SampleContext.__table__.columns[field_name]
        typ = str(column.type)
        try:
            if column.name == 'id':
                if len(filter_spec['is']) == 0:
                    raise ValueError("Value can't be empty")
                contextual_filter.add_term(ContextualFilterTermSampleID(field_name, operator, [int(t) for t in filter_spec['is']]))
            elif hasattr(column, 'ontology_class'):
                contextual_filter.add_term(
                    ContextualFilterTermOntology(field_name, operator, int(filter_spec['is'])))
            elif typ == 'DATE':
                contextual_filter.add_term(
                    ContextualFilterTermDate(field_name, operator, parse_date(filter_spec['from']), parse_date(filter_spec['to'])))
            elif typ == 'FLOAT':
                contextual_filter.add_term(
                    ContextualFilterTermFloat(field_name, operator, parse_float(filter_spec['from']), parse_float(filter_spec['to'])))
            elif typ == 'CITEXT':
                value = str(filter_spec['contains'])
                if value == '':
                    raise ValueError("Value can't be empty")
                contextual_filter.add_term(
                    ContextualFilterTermString(field_name, operator, value))
            else:
                raise ValueError("invalid filter term type: %s", typ)
        except Exception:
            errors.append("Invalid value provided for contextual field `%s'" % field_name)
            logger.critical("Exception parsing field: `%s':\n%s" % (field_name, traceback.format_exc()))

    return (OTUQueryParams(
        amplicon_filter=amplicon_filter,
        contextual_filter=contextual_filter,
        taxonomy_filter=taxonomy_filter), errors)


def param_to_filters_without_checks(query_str):
    otu_query = json.loads(query_str)
    taxonomy_filter = clean_taxonomy_filter(otu_query['taxonomy_filters'])
    amplicon_filter = clean_amplicon_filter(otu_query['amplicon_filter'])

    context_spec = otu_query['contextual_filters']
    contextual_filter = ContextualFilter(context_spec['mode'], context_spec['environment'])

    errors = []

    return (OTUQueryParams(
        amplicon_filter=amplicon_filter,
        contextual_filter=contextual_filter,
        taxonomy_filter=taxonomy_filter), errors)


@require_POST
def required_table_headers(request):
    """
    This is a modification of the otu_search method to populate the DataTable
    """

    def _int_get_param(param_name):
        param = request.POST.get(param_name, '')
        try:
            return int(param)
        except ValueError:
            return None

    start = _int_get_param('start')
    length = _int_get_param('length')

    additional_headers = json.loads(request.POST.get('columns', '[]'))
    all_headers = ['bpa_id', 'environment'] + additional_headers

    environment_lookup = make_environment_lookup()

    sorting = _parse_table_sorting(json.loads(request.POST.get('sorting', '[]')), all_headers)

    params, errors = param_to_filters_without_checks(request.POST['otu_query'])
    with SampleQuery(params) as query:
        results = query.matching_sample_headers(additional_headers, sorting)

    result_count = len(results)
    results = results[start:start + length]

    def get_environment(environment_id):
        if environment_id is None:
            return None
        return environment_lookup[environment_id]

    def map_result(row):
        d = dict(zip(all_headers, row))
        d['environment'] = get_environment(d['environment'])
        return d

    return JsonResponse({
        'data': [map_result(row) for row in results],
        'rowsCount': result_count,
    })


@require_CKAN_auth
@require_POST
def otu_search_sample_sites(request):
    params, errors = param_to_filters(request.POST['otu_query'])
    if errors:
        return JsonResponse({
            'errors': [str(e) for e in errors],
            'data': [],
        })
    data = spatial_query(params)
    return JsonResponse({'data': data})


# technically we should be using GET, but the specification
# of the query (plus the datatables params) is large: so we
# avoid the issues of long URLs by simply POSTing the query
@require_CKAN_auth
@require_POST
def otu_search(request):
    """
    private API: return the available fields, and their types, so that
    the contextual filtering UI can be built
    """
    def _int_get_param(param_name):
        param = request.POST.get(param_name)
        try:
            return int(param) if param is not None else None
        except ValueError:
            return None

    start = _int_get_param('start')
    length = _int_get_param('length')

    environment_lookup = make_environment_lookup()

    params, errors = param_to_filters(request.POST['otu_query'])
    with SampleQuery(params) as query:
        results = query.matching_sample_ids_and_environment()
    result_count = len(results)
    if start >= result_count:
        start = (result_count // length) * length
    results = results[start:start + length]

    def get_environment(environment_id):
        if environment_id is None:
            return None
        return environment_lookup[environment_id]

    if errors:
        res = {
            'errors': [str(t) for t in errors],
            'data': [],
            'rowsCount': 0,
        }
    else:
        res = {
            'data': [{"bpa_id": t[0], "environment": get_environment(t[1])} for t in results],
            'rowsCount': result_count,
        }
    return JsonResponse(res)


@require_CKAN_auth
@require_GET
def otu_biom_export(request):
    timestamp = make_timestamp()
    params, errors = param_to_filters(request.GET['q'])
    zf = biom_zip_file_generator(params, timestamp)
    response = StreamingHttpResponse(zf, content_type='application/zip')
    filename = params.filename(timestamp, '.biom.zip')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


@require_CKAN_auth
@require_GET
def otu_export(request):
    """
    this view takes:
     - contextual filters
     - taxonomic filters
    produces a Zip file containing:
      - an CSV of all the contextual data samples matching the query
      - an CSV of all the OTUs matching the query, with counts against Sample IDs
    """
    timestamp = make_timestamp()
    params, errors = param_to_filters(request.GET['q'])
    zf = tabular_zip_file_generator(params)
    response = StreamingHttpResponse(zf, content_type='application/zip')
    filename = params.filename(timestamp, '-csv.zip')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


@require_CKAN_auth
@require_POST
def submit_to_galaxy(request):
    try:
        ckan_data = request.ckan_data

        email = ckan_data.get('email')
        if not email:
            raise OTUError("Could not retrieve user's email")

        params, errors = param_to_filters(request.POST['query'])

        if errors:
            raise OTUError(*errors)

        submission_id = tasks.submit_to_galaxy(email, request.POST['query'])

        return JsonResponse({
            'success': True,
            'submission_id': submission_id,
        })
    except OTUError as exc:
        logger.exception('Error in submit to Galaxy')
        return JsonResponse({
            'success': False,
            'errors': exc.errors,
        })


@require_CKAN_auth
@require_GET
def galaxy_submission(request):
    submission_id = request.GET['submission_id']
    submission = tasks.Submission(submission_id)

    if not submission.history_id or not submission.file_id:
        state = 'pending'
    else:
        state = submission.upload_state

    return JsonResponse({
        'success': True,
        'submission': {
            'id': submission_id,
            'history_id': submission.history_id,
            'file_id': submission.file_id,
            'state': state,
        }
    })


def otu_log(request):
    template = loader.get_template('bpaotu/otu_log.html')
    missing_sample_ids = []
    from .query import Session
    from .otu import (SampleContext, OTU, SampleOTU)
    for obj in ImportSamplesMissingMetadataLog.objects.all():
        missing_sample_ids += obj.samples_without_metadata
    session = Session()
    context = {
        'files': ImportFileLog.objects.all(),
        'ontology_errors': ImportOntologyLog.objects.all(),
        'missing_samples': ', '.join(sorted(missing_sample_ids)),
        'otu_count': session.query(OTU).count(),
        'sampleotu_count': session.query(SampleOTU).count(),
        'samplecontext_count': session.query(SampleContext).count(),
    }
    session.close()
    return HttpResponse(template.render(context, request))


@require_CKAN_auth
@require_GET
def contextual_csv_download_endpoint(request):
    data = request.GET.get('otu_query')

    additional_headers = json.loads(request.GET.get('columns', '[]'))
    all_headers = ['bpa_id', 'environment'] + additional_headers

    sorting = _parse_table_sorting(json.loads(request.GET.get('sorting', '[]')), all_headers)

    params, errors = param_to_filters_without_checks(data)
    with SampleQuery(params) as query:
        results = query.matching_sample_headers(additional_headers, sorting)

    header = ['sample_bpa_id', 'bpa_project'] + additional_headers

    file_buffer = io.StringIO()
    csv_writer = csv.writer(file_buffer)

    def read_and_flush():
        data = file_buffer.getvalue()
        file_buffer.seek(0)
        file_buffer.truncate()
        return data

    def yield_csv_function():
        csv_writer.writerow(header)
        yield read_and_flush()

        for r in results:
            row = []
            row.append(r)

            csv_writer.writerow(r)
            yield read_and_flush()

    response = StreamingHttpResponse(yield_csv_function(), content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="contextual_data.csv"'

    return response


def tables(request):
    template = loader.get_template('bpaotu/tables.html')
    context = {
        'ckan_auth_integration': settings.CKAN_AUTH_INTEGRATION
    }

    return HttpResponse(template.render(context, request))


def _parse_table_sorting(sorting, headers):
    def parse_sorting(sort):
        if 'id' not in sort:
            return None
        col_name = sort.get('id')
        try:
            col_idx = headers.index(col_name)
        except ValueError:
            return None
        return {'col_idx': col_idx, 'desc': sort.get('desc', False)}

    def reject_nones(xs):
        return [x for x in xs if x is not None]

    return reject_nones(parse_sorting(s) for s in sorting)


def dev_only_ckan_check_permissions(request):
    if settings.PRODUCTION:
        raise Http404('View does not exist in production')

    # Uncomment to simulate user not logged in to CKAN
    # from django.http import HttpResponseForbidden
    # return HttpResponseForbidden()

    # organisations = [
    #     'anu-abc-upload', 'bpa-sepsis', 'australian-microbiome', 'bpa-project-documentation', 'bpa-barcode',
    #     'bioplatforms-australia', 'bpa-base', 'bpa-great-barrier-reef', 'incoming-data', 'bpa-marine-microbes',
    #     'bpa-melanoma', 'bpa-omg', 'bpa-stemcells', 'bpa-wheat-cultivars', 'bpa-wheat-pathogens-genomes', 'bpa-wheat-pathogens-transcript']
    organisations = ['australian-microbiome']

    data = json.dumps({
        'email': settings.CKAN_DEVELOPMENT_USER_EMAIL,
        'timestamp': time.time(),
        'organisations': organisations,
    })

    secret_key = os.environ.get('BPAOTU_AUTH_SECRET_KEY').encode('utf8')
    digest_maker = hmac.new(secret_key)
    digest_maker.update(data.encode('utf8'))
    digest = digest_maker.hexdigest()

    response = '||'.join([digest, data])

    return HttpResponse(response)
