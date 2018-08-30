
import sys
from django.core.management.base import BaseCommand
from ...query import OTUQueryParams, ContextualFilter, OntologyInfo, SampleQuery
from ...otu import OTUKingdom, OTUPhylum, OTUClass, Environment
from ...biom import generate_biom_file
from ...util import make_timestamp
from collections import OrderedDict


class Command(BaseCommand):

    @classmethod
    def make_is(cls, v):
        if v is None:
            return v
        return OrderedDict([('operator', 'is'), ('value', v)])

    @classmethod
    def onto_is(cls, taxo_cls, s):
        with OntologyInfo() as info:
            return cls.make_is([i for (i, t) in info.get_values(taxo_cls) if t == s][0])

    def handle(self, *args, **kwargs):
        params = OTUQueryParams(
            amplicon_filter=None,
            contextual_filter=ContextualFilter('and', self.onto_is(Environment, 'Soil')),
            taxonomy_filter=[
                self.onto_is(OTUKingdom, 'Bacteria'),
                self.onto_is(OTUPhylum, 'Bacteroidetes'),
                self.onto_is(OTUClass, 'Ignavibacteria'),
                None,
                None,
                None,
                None])

        timestamp = make_timestamp()
        print(params.filename(timestamp, '.biom.zip'))
        print(params.summary())
        print(params.description())

        return

        with SampleQuery(params) as query:
            size = 0
            for data in (s.encode('utf8') for s in generate_biom_file(query)):
                size += len(data)
            print('BIOM output complete, total size={:,}'.format(size), file=sys.stderr)
