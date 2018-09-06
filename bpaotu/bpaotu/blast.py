
import csv
import logging


logger = logging.getLogger('rainbow')


class BLASTFilter:
    """
    Wrap BLAST: this is just a proof-of-concept for now, so this is mostly stubs
    """
    BLAST_FIELDS = (
        'query_id',
        'subject_id',
        'percent_identity',
        'alignment_length',
        'mismatches',
        'gap_opens',
        'q_start',
        'q_end',
        's_start',
        's_end',
        'evalue',
        'bit_score'
    )

    def __init__(self, path):
        self.otu_ids = self._read(path, threshold=97.0)

    def _read(self, path, threshold):
        matches = []
        with open(path) as fd:
            r = csv.DictReader(fd, fieldnames=self.BLAST_FIELDS, dialect='excel-tab')
            # Fields: query id, subject id, % identity, alignment length, mismatches, gap opens, q. start, q. end, s. start, s. end, evalue, bit score
            for row in r:
                if float(row['percent_identity']) < threshold:
                    continue
                otu_id = int(row['query_id'][4:])
                matches.append(otu_id)
        logger.critical('{} OTUs match BLAST search'.format(len(matches)))
        return matches

    def get_otu_ids(self):
        return self.otu_ids.copy()
