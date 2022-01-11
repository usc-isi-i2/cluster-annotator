import os

from flask import Flask, render_template, request, redirect, url_for
from config import CONFIG

from core import Annotator

app = Flask(__name__)
annotator = Annotator()


@app.route('/')
@app.route('/overview', methods=['GET'])
def overview():
    message = {}
    args = request.args.to_dict()
    if 'error' in args:
        message['error'] = args['error']

    data = {
        'data_file': CONFIG['data_file'],
        'status_file': CONFIG['status_file'],
        'data_id_column': CONFIG['data_id_column'],
        'data_columns': annotator.data_columns,
        'cluster_file_dir': CONFIG['cluster_file_dir'],
        'cluster_file_list': os.listdir(CONFIG['cluster_file_dir']),
    }

    status = annotator.status
    if status:
        data['mode'] = status['mode']
        data['cluster_file'] = status['cluster_file']
        data['num_of_clusters'] = status['num_of_clusters']
        data['num_of_annotated_clusters'] = status['num_of_annotated_clusters']
        data['num_of_ignored_clusters'] = status['num_of_ignored_clusters']
        data['num_of_remaining_clusters'] = status['num_of_clusters'] \
            - status['num_of_annotated_clusters'] - status['num_of_ignored_clusters']
        if data['num_of_clusters'] > 0:
            progress = 1 - 1.0 * data["num_of_remaining_clusters"] / data["num_of_clusters"]
            data['progress'] = f'{int(progress * 100)}%'
        else:
            data['progress'] = 'N/A'

        data['next_cluster_id'] = annotator.get_next_cluster_id()
    return render_template('overview.html', data=data, message=message)


@app.route('/initialize', methods=['POST'])
def initialize():
    params = request.form.to_dict()
    cluster_file_path = os.path.join(CONFIG['cluster_file_dir'], params['select-cluster-file'])
    error = annotator.initialize_annotation(params['mode'].lower(), cluster_file_path)
    return redirect(url_for('overview'))
    # return redirect('/overview' + f'?error={error}' if error else '')


@app.route('/generate', methods=['POST'])
def generate():
    params = request.form.to_dict()
    new_cluster_file_path = os.path.join(CONFIG['cluster_file_dir'], params['new-cluster-file-name'])
    annotator.generate_annotation(new_cluster_file_path)
    return redirect(url_for('overview'))


@app.route('/discard', methods=['POST'])
def discard():
    annotator.discard_annotation()
    return redirect(url_for('overview'))


@app.route('/progress', methods=['GET'])
def progress():
    data = {
        'mode': annotator.mode,
        'clusters': annotator.progress

    }
    return render_template('progress.html', data=data)


@app.route('/split/<cid>', methods=['GET', 'POST'])
def split(cid):
    message = {}

    if request.method == 'POST':
        params = request.form.to_dict()
        if 'skip' in params:
            params.pop('skip')
            next_cluster_id = annotator.get_next_cluster_id(cid)
            if not next_cluster_id:
                return redirect(url_for('progress'))
            return redirect(url_for('split', cid=next_cluster_id))
        elif 'submit' in params:
            params.pop('submit')

            params = list(filter(lambda kv: kv[0].startswith('cid-'), params.items()))
            params = {k[4:]: v for k, v in params}
            for k, v in params.items():
                if not v.isnumeric() and v.strip() != '':
                    message['error'] = 'Invalid numbers assigned, please fix!'
                    break
            else:
                annotator.annotate_cluster(cid, params)
                next_cluster_id = annotator.get_next_cluster_id(cid)
                if not next_cluster_id:
                    return redirect(url_for('progress'))
                return redirect(url_for('split', cid=next_cluster_id))

    records = annotator.get_cluster(cid)
    data = {
        'cluster_id': cid,
        'records': records,
        'data_columns': annotator.data_columns
    }
    return render_template('split.html', data=data, message=message)


@app.route('/merge/<cid>', methods=['GET', 'POST'])
def merge(cid):

    message = {}

    if request.method == 'POST':
        params = request.form.to_dict()
        if 'skip' in params:
            params.pop('skip')
            next_cluster_id = annotator.get_next_cluster_id(cid)
            if not next_cluster_id:
                return redirect(url_for('progress'))
            return redirect(url_for('merge', cid=next_cluster_id))
        elif 'submit' in params:
            params.pop('submit')

            selected_clusters = [k[4:] for k in list(filter(lambda k: k.startswith('cid-'), params.keys()))]
            annotator.merge_cluster(cid, selected_clusters)
            next_cluster_id = annotator.get_next_cluster_id(cid)
            if not next_cluster_id:
                return redirect(url_for('progress'))
            return redirect(url_for('merge', cid=next_cluster_id))

    # cluster
    records = annotator.get_cluster(cid, CONFIG['max_num_of_records'])
    data = {
        'cluster_id': cid,
        'records': records,
        'data_columns': annotator.data_columns
    }

    # similar cluster
    data['similar_clusters'] = {}
    sim_cids = annotator.get_similar_cluster_ids(cid)
    for cid, is_annotated_the_same in sim_cids.items():
        data['similar_clusters'][cid] = {
            'is_annotated_the_same': is_annotated_the_same,
            'records': annotator.get_cluster(cid, CONFIG['max_num_of_records'])
        }

    return render_template('merge.html', data=data, message=message)


if __name__ == '__main__':
    app.run(debug=CONFIG['debug'], host=CONFIG['host'], port=CONFIG['port'])