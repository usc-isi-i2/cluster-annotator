# Cluster Annotator

Cluster Annotator is a general-purpose tool for annotating clusters.

## Usage

- Installation:

```
git clone git@github.com:usc-isi-i2/cluster-annotator.git
cd cluster-annotator
pip install -r requirements.txt
```

- Configuration:

The configuration file `config.json` needs to be created in the root of the directory.

A typical config file formats like this:

```
{
    "debug": true,
    "host": "localhost",
    "port": 9999,
    "logging_file": "data/log.log",
    "logging_level": "DEBUG",
    
    "data_file": "data/2015-2020 Evictions Maricopa County - 2020.csv",
    "data_columns": [
        "Case Number",
        "Plaintiff Name",
        "Plaintiff1 Address"
    ],
    "data_id_column": "Case Number",
    "cluster_file_dir": "data",
    "status_file": "data/status.db",
    
    "max_num_of_records": 5
}
```

- Execution:

```
python app.py
```
