import os
import json
from dask.threaded import get
from processor import processor
import pytest
from ltldoorstep.encoders import json_dumps

def testing_city_finder():
    path = os.path.join(os.path.dirname(__file__), 'sample_transcripts', 'out-example-2021-02-01-hansard-plenary.txt')
    city_finder = processor()

    workflow = city_finder.build_workflow(path)
    report = get(workflow, 'output')

    with open('./tests/test_report.json', 'r') as json_file:
        expected_report = json.load(json_file)

    compiled_report = report.compile()
    # Once you have a working version of your processor, we recommend that you
    # get the JSON output (python3 processor.py out...txt) and save it to tests/test_report.json
    # Then uncomment the line below - this will alert you if your processor output ever changes!
    # assert expected_report == compiled_report
