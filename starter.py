import argparse
import json
import sys
import os

import utils


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cluster Annotator')
    parser.add_argument('-c', '--config', dest='config_file', action='store', type=str, default='config.json')
    args = parser.parse_args()

    # run in pyinstaller bundle
    # sys._MEIPASS is bundle dir. For one-file bundle, this is the path to
    # the temporary folder created by the bootloader
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))

    utils.config = utils.get_config(args.config_file)

    # force the flask debug mode to be off in pyinstaller bundle
    if getattr(sys, 'frozen', False):
        utils.config['debug'] = False

    from app import app
    app.run(debug=utils.config['debug'], host=utils.config['host'], port=utils.config['port'])
