from collections import defaultdict, OrderedDict
import csv
from functools import wraps
import hmac
import io
import json
import logging
from operator import itemgetter
import os
import re
import time

from django.core.mail import send_mail
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_page
from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse, StreamingHttpResponse, Http404, HttpResponse
from bpaingest.projects.amdb.contextual import AustralianMicrobiomeSampleContextual

from .ckan_auth import require_CKAN_auth
from .galaxy_client import galaxy_ensure_user, get_krona_workflow
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
    ImportMetadata,
    ImportFileLog,
    ImportOntologyLog,
    ImportSamplesMissingMetadataLog)
from .util import (
    make_timestamp,
    parse_date,
    parse_float)
from .biom import biom_zip_file_generator
from .tabular import tabular_zip_file_generator
from . import tasks
from .site_images import (
    get_site_image_lookup_table,
    fetch_image
)

logger = logging.getLogger("rainbow")


# See datatables.net serverSide documentation for details
ORDERING_PATTERN = re.compile(r'^order\[(\d+)\]\[(dir|column)\]$')
COLUMN_PATTERN = re.compile(r'^columns\[(\d+)\]\[(data|name|searchable|orderable)\]$')

CACHE_1DAY = (60 * 60 * 24)
CACHE_7DAYS = (60 * 60 * 24 * 7)


class OTUError(Exception):
    def __init__(self, *errors):
        self.errors = errors


def make_environment_lookup():
    with OntologyInfo() as info:
        return dict(info.get_values(Environment))


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


def make_clean_taxonomy_filter(amplicon_filter, state_vector):
    """
    take an amplicon filter and a taxonomy filter
    # (a list of phylum, kingdom, ...) and clean it
    """

    assert(len(state_vector) == len(TaxonomyOptions.hierarchy))
    return TaxonomyFilter(
        clean_amplicon_filter(amplicon_filter),
        list(map(
            get_operator_and_int_value,
            state_vector)))


def normalise_blast_search_string(s):
    cleaned = s.strip().upper()
    used_chars = set(cleaned)
    permitted_chars = set('GATC')
    invalid = used_chars - permitted_chars
    if invalid:
        raise OTUError("BLAST search string contains invalid characters: {}".format(invalid))
    return cleaned


@require_GET
@ensure_csrf_cookie
def api_config(request):
    config = {
        'amplicon_endpoint': reverse('amplicon_options'),
        'taxonomy_endpoint': reverse('taxonomy_options'),
        'contextual_endpoint': reverse('contextual_fields'),
        'search_endpoint': reverse('otu_search'),
        'export_endpoint': reverse('otu_export'),
        'export_biom_endpoint': reverse('otu_biom_export'),
        'submit_to_galaxy_endpoint': reverse('submit_to_galaxy'),
        'execute_workflow_on_galaxy_endpoint': reverse('execute_workflow_on_galaxy'),
        'galaxy_submission_endpoint': reverse('galaxy_submission'),
        'nondenoised_request_endpoint': reverse('nondenoised_request'),
        'submit_blast_endpoint': reverse('submit_blast'),
        'blast_submission_endpoint': reverse('blast_submission'),
        'search_sample_sites_endpoint': reverse('otu_search_sample_sites'),
        'required_table_headers_endpoint': reverse('required_table_headers'),
        'contextual_csv_download_endpoint': reverse('contextual_csv_download_endpoint'),
        'base_url': settings.BASE_URL,
        'static_base_url': settings.STATIC_URL,
        'galaxy_base_url': settings.GALAXY_BASE_URL,
        'ckan_base_url': settings.CKAN_SERVER['base_url'],
        'ckan_check_permissions': (
            settings.CKAN_CHECK_PERMISSIONS_URL if settings.PRODUCTION
            else reverse('dev_only_ckan_check_permissions')),
        'galaxy_integration': settings.GALAXY_INTEGRATION,
    }
    return JsonResponse(config)


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
        taxonomy_filter = make_clean_taxonomy_filter(
            json.loads(request.GET['amplicon']),
            json.loads(request.GET['selected']))
        possibilities = options.possibilities(taxonomy_filter)
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
    field_units = AustralianMicrobiomeSampleContextual.units_for_fields()

    ontology_classes = {}

    # TODO Note TS: I don't understand why do we group columns together by their type.
    # Why can't we just got through them once and map them to the definitions?

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
        fields_by_type[ty].append(column.name)

    def make_defn(typ, name, **kwargs):
        environment = classifications.get(name)
        r = kwargs.copy()
        r.update({
            'type': typ,
            'name': name,
            'environment': environment,
            'display_name': SampleContext.display_name(name),
            'units': field_units.get(name)
        })
        return r

    with OntologyInfo() as info:
        fields_with_values = [
            (field_name, info.get_values(ontology_classes[field_name]))
            for field_name in fields_by_type['_ontology']]

    definitions = (
        [make_defn('sample_id', 'id', display_name='Sample ID', values=sorted(get_sample_ids()))] +
        [make_defn('date', field_name) for field_name in fields_by_type['DATE']] +
        [make_defn('float', field_name) for field_name in fields_by_type['FLOAT']] +
        [make_defn('string', field_name) for field_name in fields_by_type['CITEXT']] +
        [make_defn('ontology', field_name, values=values) for field_name, values in fields_with_values])
    definitions.sort(key=itemgetter('display_name'))

    return JsonResponse({
        'definitions': definitions
    })


def _parse_contextual_term(filter_spec):
    field_name = filter_spec['field']

    operator = filter_spec.get('operator')
    column = SampleContext.__table__.columns[field_name]
    typ = str(column.type)
    if column.name == 'id':
        if len(filter_spec['is']) == 0:
            raise ValueError("Value can't be empty")
        return ContextualFilterTermSampleID(field_name, operator, [int(t) for t in filter_spec['is']])
    elif hasattr(column, 'ontology_class'):
        return ContextualFilterTermOntology(field_name, operator, int(filter_spec['is']))
    elif typ == 'DATE':
        return ContextualFilterTermDate(
            field_name, operator, parse_date(filter_spec['from']), parse_date(filter_spec['to']))
    elif typ == 'FLOAT':
        return ContextualFilterTermFloat(
            field_name, operator, parse_float(filter_spec['from']), parse_float(filter_spec['to']))
    elif typ == 'CITEXT':
        value = str(filter_spec['contains'])
        if value == '':
            raise ValueError("Value can't be empty")
        return ContextualFilterTermString(field_name, operator, value)
    else:
        raise ValueError("invalid filter term type: %s", typ)


def param_to_filters(query_str, contextual_filtering=True):
    """
    take a JSON encoded query_str, validate, return any errors
    and the filter instances
    """

    otu_query = json.loads(query_str)
    taxonomy_filter = make_clean_taxonomy_filter(
        otu_query['amplicon_filter'],
        otu_query['taxonomy_filters'])

    context_spec = otu_query['contextual_filters']
    contextual_filter = ContextualFilter(context_spec['mode'], context_spec['environment'])

    errors = []

    if contextual_filtering:
        for filter_spec in context_spec['filters']:
            field_name = filter_spec['field']
            if field_name not in SampleContext.__table__.columns:
                errors.append("Please select a contextual data field to filter upon.")
                continue

            try:
                contextual_filter.add_term(_parse_contextual_term(filter_spec))
            except Exception:
                errors.append("Invalid value provided for contextual field `%s'" % field_name)
                logger.critical("Exception parsing field: `%s'", field_name, exc_info=True)

    return (OTUQueryParams(
        contextual_filter=contextual_filter,
        taxonomy_filter=taxonomy_filter), errors)


@require_POST
def required_table_headers(request):
    return otu_search(request, contextual_filtering=False)


ACKNOWLEDGEMENT_EMAIL_TEMPLATE = """\
Your request for non-denoised data from the Australian Microbiome has been received.

We will be in touch once the data is available, or if we require further information.
"""


NONDENOISED_EMAIL_TEMPLATE = """\
A request for non-denoised data has been received.

User email: {email}

Requested samples:
{selected_samples}

Match sequence:
{match_sequence}

Taxonomy string:
{taxonomy_string}
"""


@require_CKAN_auth
@require_POST
def nondenoised_request(request):
    format_obj = {
        k: request.POST.get(k, '')
        for k in ('match_sequence', 'taxonomy_string')
    }
    format_obj['email'] = request.ckan_data.get('email')
    format_obj['selected_samples'] = '\n'.join(json.loads(request.POST.get('selected_samples', '[]')))
    send_mail(
        "Australian Microbiome: Data request received",
        ACKNOWLEDGEMENT_EMAIL_TEMPLATE.format(**format_obj),
        "Australian Microbiome Data Requests <am-data-requests@bioplatforms.com>", [format_obj['email']])
    send_mail(
        "[AMI] Non-denoised data request",
        NONDENOISED_EMAIL_TEMPLATE.format(**format_obj),
        "Australian Microbiome Data Requests <am-data-requests@bioplatforms.com>", [settings.NONDENOISED_REQUEST_EMAIL])
    return JsonResponse({'okay': True})


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

    site_image_lookup_table = get_site_image_lookup_table()

    for d in data:
        key = (str(d['latitude']), str(d['longitude']))
        d['site_images'] = site_image_lookup_table.get(key)
    return JsonResponse({'data': data})


# technically we should be using GET, but the specification
# of the query (plus the datatables params) is large: so we
# avoid the issues of long URLs by simply POSTing the query
@require_CKAN_auth
@require_POST
def otu_search(request, contextual_filtering=True):
    def _int_get_param(param_name):
        param = request.POST.get(param_name)
        try:
            return int(param) if param is not None else None
        except ValueError:
            return None

    start = _int_get_param('start')
    length = _int_get_param('length')

    additional_headers = json.loads(request.POST.get('columns', '[]'))
    all_headers = ['sample_id', 'environment'] + additional_headers

    environment_lookup = make_environment_lookup()

    sorting = _parse_table_sorting(json.loads(request.POST.get('sorting', '[]')), all_headers)

    params, errors = param_to_filters(request.POST['otu_query'], contextual_filtering=contextual_filtering)
    if errors:
        return JsonResponse({
            'errors': [str(t) for t in errors],
            'data': [],
            'rowsCount': 0,
        })

    with SampleQuery(params) as query:
        results = query.matching_sample_headers(additional_headers, sorting)

    result_count = len(results)

    if start >= result_count:
        start = (result_count // length) * length
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


def do_on_galaxy(galaxy_action):

    @wraps(galaxy_action)
    def galaxy_wrapper_view(request):
        try:
            ckan_data = request.ckan_data

            email = ckan_data.get('email')
            if not email:
                raise OTUError("Could not retrieve user's email")

            params, errors = param_to_filters(request.POST['query'])

            if errors:
                raise OTUError(*errors)

            submission_id, user_created = galaxy_action(request, email)

            return JsonResponse({
                'success': True,
                'submission_id': submission_id,
                'user_created': user_created,
            })
        except OTUError as exc:
            logger.exception('Error in submit to Galaxy')
            return JsonResponse({
                'success': False,
                'errors': exc.errors,
            })

    return galaxy_wrapper_view


@require_CKAN_auth
@require_POST
@do_on_galaxy
def submit_to_galaxy(request, email):
    '''Submits the search results as a biom file into a new history in Galaxy.'''
    user_created = galaxy_ensure_user(email)
    submission_id = tasks.submit_to_galaxy(email, request.POST['query'])
    return submission_id, user_created


@require_CKAN_auth
@require_POST
@do_on_galaxy
def execute_workflow_on_galaxy(request, email):
    user_created = galaxy_ensure_user(email)
    workflow_id = get_krona_workflow(email)
    submission_id = tasks.execute_workflow_on_galaxy(email, request.POST['query'], workflow_id)
    return submission_id, user_created


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


@require_CKAN_auth
@require_POST
def submit_blast(request):
    try:
        params, errors = param_to_filters(request.POST['query'])
        if errors:
            raise OTUError(*errors)

        search_string = normalise_blast_search_string(request.POST['search_string'])
        submission_id = tasks.submit_blast(
            search_string,
            request.POST['query'])

        return JsonResponse({
            'success': True,
            'submission_id': submission_id,
        })
    except OTUError as exc:
        logger.exception('Error in submit to Blast')
        return JsonResponse({
            'success': False,
            'errors': exc.errors,
        })


@require_CKAN_auth
@require_GET
def blast_submission(request):
    submission_id = request.GET['submission_id']
    submission = tasks.Submission(submission_id)
    if not submission.result_url:
        state = 'pending'
    else:
        state = 'complete'

    return JsonResponse({
        'success': True,
        'submission': {
            'id': submission_id,
            'result_url': submission.result_url,
            'state': state,
        }
    })


def otu_log(request):
    template = loader.get_template('bpaotu/otu_log.html')
    missing = {}
    for obj in ImportSamplesMissingMetadataLog.objects.all():
        missing[obj.reason] = obj.samples
    import_meta = ImportMetadata.objects.get()
    context = {
        'ckan_base_url': settings.CKAN_SERVER['base_url'],
        'files': ImportFileLog.objects.all(),
        'ontology_errors': ImportOntologyLog.objects.all(),
        'metadata': import_meta,
    }
    context.update(missing)
    return HttpResponse(template.render(context, request))


@require_CKAN_auth
@require_GET
def contextual_csv_download_endpoint(request):
    data = request.GET.get('otu_query')

    additional_headers = json.loads(request.GET.get('columns', '[]'))
    all_headers = ['sample_id', 'environment'] + additional_headers

    sorting = _parse_table_sorting(json.loads(request.GET.get('sorting', '[]')), all_headers)

    params, errors = param_to_filters(data, contextual_filtering=False)
    with SampleQuery(params) as query:
        results = query.matching_sample_headers(additional_headers, sorting)

    header = ['sample_id', 'bpa_project'] + additional_headers

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
    #     'bpa-melanoma', 'bpa-omg', 'bpa-stemcells', 'bpa-wheat-cultivars', 'bpa-wheat-pathogens-genomes',
    #     'bpa-wheat-pathogens-transcript']
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


@cache_page(CACHE_1DAY, cache="image_results")
def site_image_thumbnail(request, package_id, resource_id):
    '''
    Return specified cached image or fetch image from ckan and resize before caching and returning.
    '''

    buf, content_type = fetch_image(package_id, resource_id)
    return HttpResponse(buf.getvalue(), content_type=content_type)
