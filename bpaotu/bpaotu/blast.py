
import csv
import logging


logger = logging.getLogger('rainbow')


class BLASTFilter:
    """
    Wrap BLAST: this is just a proof-of-concept for now, so this is mostly stubs
    """
    ID_FIELDS = (
        'query_id',
        'subject_id',
    )
    BLAST_FIELDS = (
        'percent_identity',
        'alignment_length',
        'mismatches',
        'gap_opens',
        'q_start',
        'q_end',
        's_start',
        's_end',
        'evalue',
        'bit_score',
    )

    def __init__(self, path):
        self._otu_metadata = self._read(path, threshold=97.0)
        self._otu_ids = list(sorted(self._otu_metadata.keys()))
        logger.critical('{} OTUs match BLAST search'.format(len(self._otu_ids)))

    def _read(self, path, threshold):
        otu_metadata = {}
        with open(path) as fd:
            r = csv.DictReader(fd, fieldnames=self.ID_FIELDS + self.BLAST_FIELDS, dialect='excel-tab')
            # Fields: query id, subject id, % identity, alignment length, mismatches, gap opens, q. start, q. end, s. start, s. end, evalue, bit score
            for row in r:
                if float(row['percent_identity']) < threshold:
                    continue
                otu_id = int(row['query_id'][4:])
                otu_metadata[otu_id] = row
        return otu_metadata

    def get_otu_ids(self):
        return self._otu_ids.copy()

    def get(self, otu_id):
        return self._otu_metadata[otu_id]
