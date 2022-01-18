import argparse
import json

import utils


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cluster Annotator')
    parser.add_argument('-c', '--config', dest='config_file', action='store', type=str, default='config.json')
    args = parser.parse_args()

    utils.config = utils.get_config(args.config_file)

    from app import app
    app.run(debug=utils.config['debug'], host=utils.config['host'], port=utils.config['port'])
