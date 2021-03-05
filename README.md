# City Finder Processor for NI Assembly Hansard Minutes

This is an example of a Lintol processor. You can run it like so:

    python3 processor.py out-example-2021-02-01-hansard-plenary.txt

or, if you would like a nicely-formatted HTML page to look at:

    ltldoorstep -o html --output-file output.html process sample_transcripts/out-example-2021-02-01-hansard-plenary.txt processor.py -e dask.threaded

This will create output.html in the current directory and, in a browser (tested with Chrome), should look like output.png.

If you install and run `pytest`, this will help you automate checking changes. It will run the example test function in test_processor.py.

For more detail on installation and set-up steps, check out HOWTO_detailed.pdf - these steps are based on Linux use, but similar steps to other operating systems.

## Evaluation

To be eligible for submission, your processor **must** be public, MIT/Apache licensed and build an output HTML \[Lintol\] report automatically from git.
The simplest way to do this, is to fork this repository - when you commit to _master_, Gitlab will automatically start building and pushing the output report to
https://YOURACCOUNT.gitlab.io/FORKEDREPONAME . Before submitting, make 100% sure it is appearing correctly and automatically there (you can check
build progress each time you push commits by going to the "Pipelines" page on Gitlab.

You are welcome to use other platforms, as long as your code builds and runs the report with ltldoorstep, for example with Github Actions or CircleCI
(you will need to copy over from the .gitlab-ci.yml file in this repo and adjust accordingly).

## Notes

You do not have to use Python, or a specific version of Python, _provided_ that your code takes in and outputs the correct reporting schemas. The easiest way
to ensure this is to use the Python ltldoorstep libraries as shown here (it handles that automatically for you).

You are welcome to add additional open source dependencies to the requirements.txt, or additional open data to add extra reports. While we do
not expressly prohibit calling out to external services, solutions that run without hitting third-party APIs may be seen more favourably.
