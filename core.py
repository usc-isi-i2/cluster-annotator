import json
import csv
from collections import defaultdict, OrderedDict
import sqlite3
import datetime

from config import CONFIG, get_logger


logger = get_logger(__name__)


class Annotator(object):
    def __init__(self):
        # data file
        self.data = {}
        with open(CONFIG['data_file'], 'r', newline='') as f:
            reader = csv.DictReader(f)
            self.data_columns = CONFIG['data_columns'] if CONFIG['data_columns'] else reader.fieldnames
            for row in reader:
                rid = row[CONFIG['data_id_column']]
                self.data[rid] = OrderedDict()
                for k in self.data_columns:
                    self.data[rid][k] = row[k]

        # status file
        self.status_db = StatusDBHelper(CONFIG['status_file'])
        self.status_db.initialize()

    def initialize_annotation(self, mode, cluster_file_path):
        self.status_db.cleanup()
        self.status_db.initialize()
        self.status_db.create_mode(mode, cluster_file_path, CONFIG['data_file'])
        try:
            with open(cluster_file_path) as f:
                obj = json.load(f)
                clusters = obj['clusters']
                cluster_ids = set([])
                for c in clusters:
                    cluster_ids.add(c['id'])
                    self.status_db.create_cluster(c['id'], len(c['records']))
                    self.status_db.create_records(c['records'], c['id'])

                if mode == 'split':
                    for c in clusters:
                        if len(c['records']) < 2:
                            self.status_db.ignore_cluster(c['id'])
                elif mode == 'merge':
                    similar_cluster_ids = set([])
                    for idx, cids in enumerate(obj['similar_clusters']):
                        for cid in cids:
                            similar_cluster_ids.add(cid)
                            self.status_db.create_similar_clusters(cid, idx)

                    # ignore the clusters with no similar cluster candidates
                    for cid in cluster_ids - similar_cluster_ids:
                        self.status_db.ignore_cluster(cid)

        except Exception as e:
            self.status_db.cleanup()
            self.status_db.initialize()
            logger.error(f'Invalid file: {e}')
            return 'Invalid file'

    def __del__(self):
        pass

    def get_cluster(self, cid, limit=None):
        records = {}
        for c in self.status_db.get_cluster(cid, limit):
            rid, new_cid = c['rid'], c['new_cid']
            records[rid] = self.data[rid]
            records[rid]['new_cid'] = new_cid
        return records

    def get_similar_cluster_ids(self, cid):
        if self.mode != 'merge':
            return None
        return self.status_db.get_similar_cluster_ids(cid)

    def get_next_cluster_id(self, cid=None):
        return self.status_db.get_next_cluster_id(cid=cid)

    def annotate_cluster(self, cid, assignment):
        # assignment = {"rid": "number", ...}
        ii = defaultdict(list)
        for rid, new_id in assignment.items():
            new_id = new_id.strip()
            if new_id == '':
                continue
            ii[new_id].append(rid)

        # update to db
        for new_cid, rids in ii.items():
            for rid in rids:
                self.status_db.annotate_record(rid, new_cid)
        self.status_db.annotate_cluster(cid)

    def merge_cluster(self, cid, selected_cids):
        # set itself to be in itself
        self.status_db.merge_similar_cluster(cid, cid)
        # set selected cids to be cid
        for selected_cid in selected_cids:
            self.status_db.merge_similar_cluster(cid, selected_cid)
        self.status_db.annotate_cluster(cid)

    def generate_annotation(self, new_cluster_file_path):
        mode = self.mode
        res = {'clusters': []}
        rid_to_cid_mapping = None

        if mode == 'split':
            rid_to_cid_mapping = self.status_db.generate_split()
        elif mode == 'merge':
            rid_to_cid_mapping = self.status_db.generate_merge()

        ii = defaultdict(list)
        for rid, cid in rid_to_cid_mapping.items():
            ii[cid].append(rid)

        for cid, rids in ii.items():
            res['clusters'].append({'id': cid, 'records': rids})

        with open(new_cluster_file_path, 'w') as f:
            json.dump(res, f)

        self.status_db.cleanup()
        self.status_db.initialize()

    def discard_annotation(self):
        self.status_db.cleanup()
        self.status_db.initialize()

    @property
    def progress(self):

        def gen_status(c):
            if c['ignored']:
                return 'Ignored'
            elif c['annotated']:
                return 'Annotated'
            return ''

        return {c['cid']: {'status': gen_status(c), 'size': c['size']} for c in self.status_db.cluster_list()}

    @property
    def mode(self):
        meta = self.status_db.get_meta()
        if not meta:
            return None

        return self.status_db.get_meta()['mode']

    @property
    def status(self):
        meta = self.status_db.get_meta()
        if not meta:
            return None

        statistics = self.status_db.statistics()
        return {
            'mode': meta['mode'],
            'cluster_file': meta['cluster_file'],
            'num_of_clusters': statistics['num_of_clusters'],
            'num_of_annotated_clusters': statistics['num_of_annotated_clusters'],
            'num_of_ignored_clusters': statistics['num_of_ignored_clusters']
        }


class StatusDBHelper(object):

    def __init__(self, filename):
        self.conn = sqlite3.connect(filename, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

    def __del__(self):
        self.cur.close()
        self.conn.close()

    def initialize(self):
        query = '''
        CREATE TABLE IF NOT EXISTS meta (
            mode VARCHAR(255),
            cluster_file VARCHAR(255),
            data_file VARCHAR(255),
            created_at DATETIME NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS records (
            rid VARCHAR(255) NOT NULL PRIMARY KEY,
            old_cid VARCHAR(255) NOT NULL,
            new_cid INTEGER DEFAULT 0,
            discard BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (old_cid) REFERENCES clusters(cid)
        );
        
        CREATE TABLE IF NOT EXISTS clusters (
            cid VARCHAR(255) NOT NULL PRIMARY KEY,
            annotated BOOLEAN DEFAULT FALSE,
            ignored BOOLEAN DEFAULT FALSE,
            size INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS similar_clusters (
            cid VARCHAR(255) NOT NULL,
            ccid INTEGER NOT NULL,
            new_ccid INTEGER,
            FOREIGN KEY (cid) REFERENCES clusters(cid)
        );
        '''
        self.cur.executescript(query)
        self.conn.commit()

    def cleanup(self):
        query = '''
        DROP TABLE IF EXISTS meta;
        DROP TABLE IF EXISTS records;
        DROP TABLE IF EXISTS clusters;
        DROP TABLE IF EXISTS similar_clusters;
        '''

        self.cur.executescript(query)
        self.conn.commit()

    def create_mode(self, mode, cluster_file, data_file):
        """
        :param mode: split / merge
        """
        dt = datetime.datetime.now()
        query = '''INSERT INTO meta(mode, created_at, cluster_file, data_file) VALUES(?, ?, ?, ?)'''
        self.cur.execute(query, (mode, dt, cluster_file, data_file))
        self.conn.commit()

    def get_meta(self):
        query = '''SELECT * FROM meta ORDER BY created_at DESC LIMIT 1'''
        return self.cur.execute(query).fetchone()

    def create_cluster(self, cid, size):
        query = '''INSERT OR IGNORE INTO clusters(cid, size) VALUES (?, ?)'''
        self.cur.execute(query, (cid, size))
        self.conn.commit()

    def create_records(self, records, old_cid):
        query = '''INSERT INTO records(rid, old_cid) VALUES (?, ?)'''
        for rid in records:  # TODO: batch this step
            self.cur.execute(query, (rid, old_cid))
            self.conn.commit()

    def create_similar_clusters(self, cid, ccid):
        query = '''INSERT OR IGNORE INTO similar_clusters(cid, ccid) VALUES (?, ?)'''
        self.cur.execute(query, (cid, ccid))
        self.conn.commit()

    def annotate_record(self, rid, new_cid):
        query = '''UPDATE records SET new_cid=? WHERE rid=?'''
        self.cur.execute(query, (new_cid, rid))
        self.conn.commit()

    def annotate_cluster(self, old_cid):
        query = '''UPDATE clusters SET annotated=1 WHERE cid=?'''
        self.cur.execute(query, (old_cid,))
        self.conn.commit()

    def ignore_cluster(self, old_cid):
        query = '''UPDATE clusters SET ignored=1 WHERE cid=?'''
        self.cur.execute(query, (old_cid,))
        self.conn.commit()

    def statistics(self):
        query = '''SELECT COUNT(*) AS num_of_clusters FROM clusters'''
        num_of_clusters = self.cur.execute(query).fetchone()['num_of_clusters']
        query = '''SELECT COUNT(*) AS num_of_annotated_clusters FROM clusters WHERE annotated IS TRUE'''
        num_of_annotated_clusters = self.cur.execute(query).fetchone()['num_of_annotated_clusters']
        query = '''SELECT COUNT(*) AS num_of_ignored_clusters FROM clusters WHERE ignored IS TRUE'''
        num_of_ignored_clusters = self.cur.execute(query).fetchone()['num_of_ignored_clusters']
        return {
            'num_of_clusters': num_of_clusters,
            'num_of_annotated_clusters': num_of_annotated_clusters,
            'num_of_ignored_clusters': num_of_ignored_clusters
        }

    def cluster_list(self):
        query = '''SELECT cid, annotated, ignored, size FROM clusters'''
        return [{'cid': row['cid'], 'annotated': row['annotated'], 'ignored': row['ignored'], 'size': row['size']}
                for row in self.cur.execute(query).fetchall()]

    def get_next_cluster_id(self, cid=None):
        query = '''SELECT cid, annotated, ignored FROM clusters'''
        cids = []
        skips = []  # skip the annotated or ignored clusters
        for row in self.cur.execute(query).fetchall():
            cids.append(row['cid'])
            skips.append(row['annotated'] or row['ignored'])

        def get_idx_of_next_unannotated(idx):
            for i in range(idx+1, len(skips)):
                if skips[i] == 0:
                    return i
            for i in range(0, idx):
                if skips[i] == 0:
                    return i
            return None

        if len(cids) == 0:
            return None

        if not cid:  # not specified, choose the first available
            next_idx = get_idx_of_next_unannotated(-1)
        else:  # specified, choose the first available after it
            next_idx = get_idx_of_next_unannotated(cids.index(cid))

        if next_idx is None:
            return None
        else:
            return cids[next_idx]

    def get_cluster(self, old_cid, limit=None):
        query = '''SELECT rid, new_cid FROM records WHERE old_cid=?'''
        param = (old_cid,)
        if limit:
            query += ' LIMIT ?'
            param = (old_cid, limit)
        return [{'rid': row['rid'], 'new_cid': row['new_cid']} for row in self.cur.execute(query, param)]

    def get_similar_cluster_ids(self, cid):
        # get cids
        query = '''SELECT cid FROM similar_clusters 
        WHERE ccid=(SELECT ccid FROM similar_clusters WHERE cid=?) 
        AND cid NOT IN (?)'''
        similar_cids = {row['cid']: False for row in self.cur.execute(query, (cid, cid)).fetchall()}

        # get cids if new_ccid is the same
        query = '''SELECT cid FROM similar_clusters WHERE new_ccid=(
            SELECT new_ccid FROM similar_clusters WHERE cid=?
        ) AND cid NOT IN (?)'''
        for cid in [row['cid'] for row in self.cur.execute(query, (cid, cid)).fetchall()]:
            similar_cids[cid] = True

        return similar_cids

    def merge_similar_cluster(self, cid, selected_cid):
        query = '''UPDATE similar_clusters SET new_ccid=? WHERE cid=?'''
        self.cur.execute(query, (cid, selected_cid))
        self.conn.commit()

    def generate_split(self):
        query = '''SELECT rid, old_cid, new_cid FROM records'''
        return {row['rid']: f'{row["old_cid"]}.{row["new_cid"]}' for row in self.cur.execute(query).fetchall()}

    def generate_merge(self):
        query = '''SELECT rid,
            CASE WHEN similar_clusters.new_ccid is NULL THEN records.old_cid ELSE similar_clusters.new_ccid END AS new_ccid
            FROM records
            LEFT OUTER JOIN similar_clusters ON records.old_cid = similar_clusters.cid'''
        return {row['rid']: f'{row["new_ccid"]}' for row in self.cur.execute(query).fetchall()}
