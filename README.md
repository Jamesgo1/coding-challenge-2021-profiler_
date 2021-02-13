# City Finder Processor

This is an example of a Lintol processor. You can run it like so:

    python3 processor.py out-example-2021-02-01-hansard-plenary.txt

or, if you would like a nicely-formatted HTML page to look at:

    ltldoorstep -o html --output-file output.html process sample_transcripts/out-example-2021-02-01-hansard-plenary.txt processor.py -e dask.threaded

This will create output.html in the current directory and, in a browser (tested with Chrome), should look like output.png.
