import datetime
from functools import partial
from itertools import chain
from .util import make_cache_key
import logging

import sqlalchemy
from sqlalchemy.orm import sessionmaker, aliased

from django.core.cache import caches

from .otu import (
    Environment,
    OTU,
    OTUAmplicon,
    OTUKingdom,
    OTUPhylum,
    OTUClass,
    OTUOrder,
    OTUFamily,
    OTUGenus,
    OTUSpecies,
    SampleContext,
    SampleOTU,
    make_engine)


logger = logging.getLogger("rainbow")
engine = make_engine()
Session = sessionmaker(bind=engine)


CACHE_FOREVER = None
CACHE_7DAYS = (60 * 60 * 24 * 7)


class OTUQueryParams:
    def __init__(self, contextual_filter, taxonomy_filter, blast_filter):
        self.contextual_filter = contextual_filter
        self.taxonomy_filter = taxonomy_filter
        self.blast_filter = blast_filter
        # for use by caching, should be a stable state summary
        self.state_key = make_cache_key(repr(self))

    def filename(self, timestamp, extension):
        return 'AustralianMicrobiome-{}{}'.format(timestamp, extension)

    def summary(self, max_chars=100):
        # a short title, maximum length `max_chars`
        parts = ['Australian Microbiome:']
        amplicon_descr, taxonomy_descr = self.taxonomy_filter.describe()
        if amplicon_descr is not None:
            parts.append(amplicon_descr)
        if taxonomy_descr:
            parts.append(taxonomy_descr[-1])
        parts.append(self.contextual_filter.describe())
        return ' '.join(parts)

    def describe(self, max_chars=100):
        "a short title, maximum length `max_chars`"

        parts = []
        amplicon_descr, taxonomy_descr = self.taxonomy_filter.describe()

        def add_section(lines):
            parts.append('\n'.join(lines))

        def amplicon_section():
            p = ['## Amplicon filter', '']
            if amplicon_descr is not None:
                p.append(amplicon_descr)
            else:
                p.append('(no amplicon filter applied)')
            return p

        def taxonomy_section():
            p = ['## Taxonomy filter', '']
            if taxonomy_descr:
                p += taxonomy_descr
            else:
                p.append('(no taxonomy filter applied)')
            return p

        def contextual_section():
            p = ['## Contextual filter', '']
            p.append(self.contextual_filter.describe())
            return p

        add_section(amplicon_section())
        add_section(taxonomy_section())
        add_section(contextual_section())

        return '\n\n'.join(parts)

    def __repr__(self):
        # Note: used for caching, so make sure all components have a defined
        # representation that's stable over time
        return 'OTUQueryParams<{},{}>'.format(
            self.contextual_filter,
            self.taxonomy_filter)


class TaxonomyOptions:
    hierarchy = [
        ('kingdom_id', OTUKingdom),
        ('phylum_id', OTUPhylum),
        ('class_id', OTUClass),
        ('order_id', OTUOrder),
        ('family_id', OTUFamily),
        ('genus_id', OTUGenus),
        ('species_id', OTUSpecies),
    ]

    def __init__(self):
        self._session = Session()

    def __enter__(self):
        return self

    def __exit__(self, exec_type, exc_value, traceback):
        self._session.close()

    def possibilities(self, taxonomy_filter, force_cache=False):
        cache = caches['search_results']
        key = make_cache_key(
            'TaxonomyOptions.possibilities',
            taxonomy_filter)
        result = None
        if not force_cache:
            result = cache.get(key)
        if result is None:
            result = self._possibilities(taxonomy_filter)
            cache.set(key, result, CACHE_FOREVER)
        return result

    def _possibilities(self, taxonomy_filter):
        """
        state should be a list of integer IDs for the relevent model, in the order of
        TaxonomyOptions.hierarchy. a value of None indicates there is no selection.
        """

        def drop_id(attr):
            "return without `_id`"
            return attr[:-3]

        def determine_target():
            # this query is built up over time, and validates the hierarchy provided to us
            q = self._session.query(OTU.kingdom_id).group_by(OTU.kingdom_id)
            q = apply_amplicon_filter(q, taxonomy_filter.amplicon_filter)
            for idx, ((otu_attr, ontology_class), taxonomy) in enumerate(zip(TaxonomyOptions.hierarchy, state)):
                valid = True
                if taxonomy is None or taxonomy.get('value') is None:
                    valid = False
                else:
                    q = apply_otu_filter(otu_attr, q, taxonomy)
                    valid = q.count() > 0
                if not valid:
                    return otu_attr, ontology_class, idx
            return None, None, None

        state = taxonomy_filter.state_vector.copy()

        # scan through in order and find our target, by finding the first invalid selection
        target_attr, target_class, target_idx = determine_target()
        # the targets to be reset as a result of this choice
        clear = [drop_id(attr) for attr, _ in TaxonomyOptions.hierarchy[target_idx:]]

        # no completion: we have a complete hierarchy
        if target_attr is None:
            return {}
        # performance: hard-code kingdom (it's the slowest query, and the most common)
        elif not taxonomy_filter.amplicon_filter and target_class is OTUKingdom:
            possibilities = self._session.query(target_class.id, target_class.value).all()
        else:
            # clear invalidated part of the state
            state = state[:target_idx] + [None] * (len(TaxonomyOptions.hierarchy) - target_idx)
            # build up a query of the OTUs for our target attribute
            q = self._session.query(getattr(OTU, target_attr), target_class.value).group_by(getattr(OTU, target_attr), target_class.value).order_by(target_class.value)

            q = apply_amplicon_filter(q, taxonomy_filter.amplicon_filter)
            for (otu_attr, ontology_class), taxonomy in zip(TaxonomyOptions.hierarchy, state):
                q = apply_otu_filter(otu_attr, q, taxonomy)
            q = q.join(target_class)
            possibilities = q.all()

        result = {
            'new_options': {
                'target': drop_id(target_attr),
                'possibilities': possibilities,
            },
            'clear': clear
        }
        return result


class OntologyInfo:
    def __init__(self):
        self._session = Session()

    def __enter__(self):
        return self

    def __exit__(self, exec_type, exc_value, traceback):
        self._session.close()

    def get_values(self, ontology_class):
        vals = self._session.query(ontology_class.id, ontology_class.value).all()
        vals.sort(key=lambda v: v[1])
        return vals

    def id_to_value(self, ontology_class, _id):
        if _id is None:
            return None
        return self._session.query(ontology_class.value).filter(ontology_class.id == _id).one()[0]

    def value_to_id(self, ontology_class, value):
        if value is None:
            return None
        return self._session.query(ontology_class.id).filter(ontology_class.value == value).one()[0]


class SampleQuery:
    """
    find samples IDs which match the given taxonomical and
    contextual filters
    """

    def __init__(self, params):
        self._session = Session()
        # amplicon filter is a master filter over the taxonomy; it's not
        # a strict part of the hierarchy, but affects taxonomy options
        # available
        self._taxonomy_filter = params.taxonomy_filter
        self._contextual_filter = params.contextual_filter
        self._blast_filter = params.blast_filter

    def __enter__(self):
        return self

    def __exit__(self, exec_type, exc_value, traceback):
        self._session.close()

    def _q_all_cached(self, topic, q, mutate_result=None):
        cache = caches['search_results']
        key = make_cache_key(
            'SampleQuery._q_all_cached',
            topic,
            self._taxonomy_filter,
            self._contextual_filter)
        result = cache.get(key)
        if not result:
            result = q.all()
            if mutate_result:
                result = mutate_result(result)
            cache.set(key, result, CACHE_7DAYS)
        return result

    def matching_sample_ids_and_environment(self):
        q = self._session.query(SampleContext.id, SampleContext.environment_id)
        subq = self._build_taxonomy_subquery()
        q = self._assemble_sample_query(q, subq).order_by(SampleContext.id)
        return self._q_all_cached('matching_sample_ids_and_environment', q)

    def matching_sample_headers(self, required_headers=None, sorting=()):
        query_headers = [SampleContext.id, SampleContext.environment_id]
        joins = []  # Keep track of any foreign ontology classes which may be needed to be joined to.

        cache_name = ['matching_sample_headers']
        if required_headers:
            cache_name += required_headers
            for h in required_headers:
                if not h:
                    continue

                col = getattr(SampleContext, h)

                if hasattr(col, "ontology_class"):
                    # we must create an alias here, as a single ontology may be linked to multiple
                    # columns (e.g. Broad Land Use, Detailed Land use)
                    aliased_table = aliased(col.ontology_class)
                    foreign_id = getattr(aliased_table, 'id')
                    foreign_col = getattr(aliased_table, 'value')
                    query_headers.append(foreign_col)
                    joins.append((aliased_table, foreign_id == col))
                else:
                    query_headers.append(col)

        q = self._session.query(*query_headers)
        for join, cond in joins:
            q = q.outerjoin(join, cond)

        for sort in sorting:
            sort_col = sort['col_idx']
            if sort.get('desc', False):
                q = q.order_by(query_headers[int(sort_col)].desc())
            else:
                q = q.order_by(query_headers[int(sort_col)])

            cache_name.append(str(query_headers[int(sort_col)]))
            cache_name.append('desc' if sort.get('desc', False) else 'asc')

        return self._q_all_cached(':'.join(cache_name), q)

    def matching_samples(self):
        q = self._session.query(SampleContext)
        subq = self._build_taxonomy_subquery()
        q = self._assemble_sample_query(q, subq).order_by(SampleContext.id)
        return self._q_all_cached('matching_samples', q)

    def matching_otus(self, kingdom_id=None):
        q = self._session.query(OTU)
        subq = self._build_contextual_subquery()
        q = self._assemble_otu_query(q, subq, kingdom_id).order_by(OTU.id)
        return q

    def has_matching_sample_otus(self, kingdom_id):
        def to_boolean(result):
            return result[0][0]

        q = self._session.query(self.matching_sample_otus(
            SampleOTU.sample_id,
            SampleOTU.otu_id,
            SampleOTU.count, kingdom_id=kingdom_id).exists())
        return self._q_all_cached('has_matching_sample_otus:%s' % (kingdom_id), q, to_boolean)

    def matching_sample_otus(self, *args, kingdom_id=None):
        # we do a cross-join, but convert to an inner-join with
        # filters. as SampleContext is in the main query, the
        # machinery for filtering above will just work
        q = self._session.query(*args) \
            .filter(OTU.id == SampleOTU.otu_id) \
            .filter(SampleContext.id == SampleOTU.sample_id)
        q = self._taxonomy_filter.apply(q)
        q = q.filter(OTU.id.in_(self._blast_filter.get_otu_ids()))
        q = self._contextual_filter.apply(q)
        if kingdom_id is not None:
            q = q.filter(OTU.kingdom_id == kingdom_id)
        # we don't cache this query: the result size is enormous,
        # and we're unlikely to have the same query run twice.
        # instead, we return the sqlalchemy query object so that
        # it can be iterated over
        return q

    def _build_taxonomy_subquery(self):
        """
        return the BPA IDs (as ints) which have a non-zero OTU count for OTUs
        matching the taxonomy filter
        """
#        if self._taxonomy_filter.is_empty():
#            return None
        q = self._session.query(SampleOTU.sample_id) \
            .distinct() \
            .join(OTU) \
            .filter(OTU.id == SampleOTU.otu_id) \
            .filter(OTU.id.in_(self._blast_filter.get_otu_ids()))
        return self._taxonomy_filter.apply(q)

    def _build_contextual_subquery(self):
        """
        return the OTU ID (as ints) which have a non-zero OTU count for Samples
        matching the contextual filter
        """
        # shortcut: if we don't have any filters, don't produce a subquery
        if self._contextual_filter.is_empty():
            return None
        q = self._session.query(SampleOTU.otu_id) \
            .distinct() \
            .join(SampleContext) \
            .filter(SampleContext.id == SampleOTU.sample_id)
        return self._contextual_filter.apply(q)

    def _assemble_sample_query(self, sample_query, taxonomy_subquery):
        """
        applies the passed taxonomy_subquery to apply taxonomy filters.

        paging support: applies limit and offset, and returns (count, [bpa_id, ...])
        """
        # we use a window function here, to get count() over the whole query without having to
        # run it twice
        q = sample_query
        if taxonomy_subquery is not None:
            q = q.filter(SampleContext.id.in_(taxonomy_subquery))
        # apply contextual filter terms
        q = self._contextual_filter.apply(q)
        return q

    def _assemble_otu_query(self, otu_query, contextual_subquery, kingdom_id):
        """
        applies the passed contextual_subquery to apply taxonomy filters.

        paging support: applies limit and offset, and returns (count, [bpa_id, ...])
        """
        # we use a window function here, to get count() over the whole query without having to
        # run it twice
        q = otu_query
        if contextual_subquery is not None:
            q = q.filter(OTU.id.in_(contextual_subquery))
        # apply taxonomic filter terms
        q = self._taxonomy_filter.apply(q)
        q = q.filter(OTU.id.in_(self._blast_filter.get_otu_ids()))
        if kingdom_id is not None:
            q = q.filter(OTU.kingdom_id == kingdom_id)
        return q


class TaxonomyFilter:
    def __init__(self, amplicon_filter, state_vector):
        self.amplicon_filter = amplicon_filter
        self.state_vector = state_vector

    def describe(self):
        with OntologyInfo() as info:
            amplicon_description = describe_op_and_val(info, 'amplicon_id', OTUAmplicon, self.amplicon_filter)
            taxonomy_descriptions = []
            for (otu_attr, ontology_class), taxonomy in zip(TaxonomyOptions.hierarchy, self.state_vector):
                descr = describe_op_and_val(info, otu_attr, ontology_class, taxonomy)
                if descr:
                    taxonomy_descriptions.append(descr)
            return amplicon_description, taxonomy_descriptions

    def is_empty(self):
        return not self.amplicon_filter and self.state_vector[0] is None

    def apply(self, q):
        q = apply_amplicon_filter(q, self.amplicon_filter)
        for (otu_attr, ontology_class), taxonomy in zip(TaxonomyOptions.hierarchy, self.state_vector):
            q = apply_otu_filter(otu_attr, q, taxonomy)
        return q

    def __repr__(self):
        return '<TaxonomyFilter(%s,state_vec[%s])>' % (
            self.amplicon_filter,
            self.state_vector)


class ContextualFilter:
    mode_operators = {
        'or': sqlalchemy.or_,
        'and': sqlalchemy.and_,
    }

    def __init__(self, mode, environment_filter):
        self.mode = mode
        self.mode_func = ContextualFilter.mode_operators[self.mode]
        self.environment_filter = environment_filter
        self.terms = []

    def __repr__(self):
        return '<ContextualFilter(%s,env[%s],[%s]>' % (self.mode, repr(self.environment_filter), ','.join(repr(t) for t in self.terms))

    def describe(self):
        descr = []
        with OntologyInfo() as info:
            env_descr = describe_op_and_val(info, 'environment_id', Environment, self.environment_filter)
            descr.append(env_descr)
            descr += [term.describe() for term in self.terms]
        return ' '.join(t for t in descr if t)

    def is_empty(self):
        return len(self.terms) == 0 and not self.environment_filter

    def add_term(self, term):
        self.terms.append(term)

    def apply(self, q):
        """
        return q with contextual filter terms applied to it
        """
        # if there's an environment filter, it applies prior to the filters
        # below, so it's outside of the application of mode_func
        q = apply_environment_filter(q, self.environment_filter)
        # chain together the conditions provided by each term,
        # combine into a single expression using our mode,
        # then filter the query
        return q.filter(
            self.mode_func(
                *(chain(*(t.conditions for t in self.terms)))))


class ContextualFilterTerm:
    def __init__(self, field_name, operator):
        self.field_name = field_name
        self.field = getattr(SampleContext, self.field_name)
        self.operator = operator

    @property
    def conditions(self):
        if self.operator == 'complement':
            return [sqlalchemy.not_(c) for c in (self.get_conditions())]
        return self.get_conditions()


class ContextualFilterTermFloat(ContextualFilterTerm):
    def __init__(self, field_name, operator, val_from, val_to):
        super().__init__(field_name, operator)
        assert(type(val_from) is float)
        assert(type(val_to) is float)
        self.val_from = val_from
        self.val_to = val_to

    def __repr__(self):
        return '<TermFloat(%s,%s,%s,%s)>' % (self.field_name, self.operator, self.val_from, self.val_to)

    def get_conditions(self):
        return [
            self.field.between(self.val_from, self.val_to)
        ]


class ContextualFilterTermDate(ContextualFilterTerm):
    def __init__(self, field_name, operator, val_from, val_to):
        super().__init__(field_name, operator)
        assert(type(val_from) is datetime.date)
        assert(type(val_to) is datetime.date)
        self.val_from = val_from
        self.val_to = val_to

    def __repr__(self):
        return '<TermDate(%s,%s,%s,%s)>' % (self.field_name, self.operator, self.val_from, self.val_to)

    def get_conditions(self):
        return [
            self.field.between(self.val_from, self.val_to)
        ]


class ContextualFilterTermString(ContextualFilterTerm):
    def __init__(self, field_name, operator, val_contains):
        super().__init__(field_name, operator)
        assert(type(val_contains) is str)
        self.val_contains = val_contains

    def __repr__(self):
        return '<TermString(%s,%s,%s)>' % (self.field_name, self.operator, self.val_contains)

    def get_conditions(self):
        cond = self.field.contains(self.val_contains)
        return [cond]


class ContextualFilterTermOntology(ContextualFilterTerm):
    def __init__(self, field_name, operator, val_is):
        super().__init__(field_name, operator)
        assert(type(val_is) is int)
        self.val_is = val_is

    def __repr__(self):
        return '<TermOntology(%s,%s,%s)>' % (self.field_name, self.operator, self.val_is)

    def get_conditions(self):
        return [
            self.field == self.val_is
        ]


class ContextualFilterTermSampleID(ContextualFilterTerm):
    def __init__(self, field_name, operator, val_is_in):
        super().__init__(field_name, operator)
        assert(type(val_is_in) is list)
        for t in val_is_in:
            assert(type(t) is int)
        self.val_is_in = val_is_in

    def __repr__(self):
        return '<TermSampleID(%s,%s,%s)>' % (self.field_name, self.operator, self.val_is_in)

    def get_conditions(self):
        return [
            self.field.in_(self.val_is_in)
        ]


def get_sample_ids():
    session = Session()
    ids = [t[0] for t in session.query(SampleContext.id).all()]
    session.close()
    return ids


OP_DESCR = {
    'is': '=',
    'isnot': '!=',
}


def describe_op_and_val(ontology_info, attr, cls, q):
    if q is None:
        return None
    return ''.join(([attr[:-3], OP_DESCR[q.get('operator')], ontology_info.id_to_value(cls, q.get('value'))]))


def apply_op_and_val_filter(attr, q, op_and_val):
    if op_and_val is None or op_and_val.get('value') is None:
        return q
    value = op_and_val.get('value')
    if op_and_val.get('operator', 'is') == 'isnot':
        q = q.filter(attr != value)
    else:
        q = q.filter(attr == value)
    return q


def apply_otu_filter(otu_attr, q, op_and_val):
    return apply_op_and_val_filter(getattr(OTU, otu_attr), q, op_and_val)


apply_amplicon_filter = partial(apply_otu_filter, 'amplicon_id')
apply_environment_filter = partial(apply_op_and_val_filter, SampleContext.environment_id)


def log_query(q):
    from sqlalchemy.dialects import postgresql
    s = q.statement.compile(dialect=postgresql.dialect())
    logger.debug('Query: \n%s', s)
