
import csv
import logging
from collections import OrderedDict


logger = logging.getLogger('rainbow')


class BLASTFilter:
    """
    Wrap BLAST: this is just a proof-of-concept for now, so this is mostly stubs
    """
    ID_FIELDS = (
        'query_id',
        'subject_id',
    )
    BLAST_FIELDS = OrderedDict((
        ('percent_identity', float),
        ('alignment_length', int),
        ('mismatches', int),
        ('gap_opens', int),
        ('q_start', int),
        ('q_end', int),
        ('s_start', int),
        ('s_end', int),
        ('evalue', float),
        ('bit_score', float)))

    def __init__(self, path):
        self._otu_metadata = self._read(path, threshold=97.0)
        self._otu_ids = list(sorted(self._otu_metadata.keys()))
        logger.critical('{} OTUs match BLAST search'.format(len(self._otu_ids)))

    def _read(self, path, threshold):
        otu_metadata = {}
        with open(path) as fd:
            r = csv.DictReader(fd, fieldnames=self.ID_FIELDS + tuple(self.BLAST_FIELDS.keys()), dialect='excel-tab')
            # Fields: query id, subject id, % identity, alignment length, mismatches, gap opens, q. start, q. end, s. start, s. end, evalue, bit score
            for row in r:
                if float(row['percent_identity']) < threshold:
                    continue
                otu_id = int(row['query_id'][4:])
                otu_metadata[otu_id] = dict((f, typ(row[f])) for (f, typ) in self.BLAST_FIELDS.items())
        return otu_metadata

    def get_otu_ids(self):
        return self._otu_ids.copy()

    def get(self, otu_id):
        return self._otu_metadata[otu_id]
