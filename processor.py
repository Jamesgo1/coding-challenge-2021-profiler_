"""
City Finder Processor
---------------------

This is an example of a Lintol processor. You can run it like so:

    python3 processor.py out-example-2021-02-01-hansard-plenary.txt

or, if you would like a nicely-formatted HTML page to look at:

    ltldoorstep -o html --output-file output.html process sample_transcripts/out-example-2021-02-01-hansard-plenary.txt processor.py -e dask.threaded

This will create output.html in the current directory and, in a browser (tested with Chrome), should look like output.png.
"""

import re
import sys
import logging
from dask.threaded import get

from ltldoorstep.processor import DoorstepProcessor
from ltldoorstep.aspect import AnnotatedTextAspect
from ltldoorstep.reports.report import combine_reports
from ltldoorstep.document_utils import load_text, split_into_paragraphs

# We name some cities - we will do all our comparisons in lowercase to match any casing
CITIES = ['armagh', 'belfast', 'derry', 'lisburn', 'newry', 'dublin', 'london', 'brussels']

def city_finder(text, rprt):
    """
    Add report items to indicate where cities appear, and how often in total
    """

    # This doorstep utility splits a big text into paragraphs, and standardizes some of
    # the punctuation. We do this splitting so that it is easier to view the results, rather
    # than scrolling through highlighted lines in one big document.
    paragraphs = split_into_paragraphs(text)

    # This is our counter for cities - we initialize every city's count to 0
    city_counts = {city: 0 for city in CITIES}

    # Now we loop through the paragraphs - `enumerate` gives us a running count in `para_n`
    for para_n, (paragraph, line_number) in enumerate(paragraphs):

        # As mentioned above, we will search entirely in lowercase - a quick way of doing
        # a case insensitive search (others welcome too!)
        paragraph_lower = paragraph.lower()

        # We check this paragraph for city names...
        for city in CITIES:
            # This gets a total count for the city
            city_occurrences = paragraph_lower.count(city)

            # If it's not 0, we will need to add an item to our report
            if city_occurrences > 0:
                # ...but first, update our overall count for this city
                # (we will need this down below)
                city_counts[city] += city_occurrences

                # To let us highlight words or phrases, we use an "Aspect"
                # This wraps a phrase/snippet/paragraph, and we add
                # one or more notes to highlight words or phrases within it.
                content = AnnotatedTextAspect(paragraph)

                # This loop uses Regular Expressions to search through
                # all the occurrences of the city's (lowercase) name in the
                # lowercase paragraph. Note that regular expressions have
                # their own language for doing more complex searches - because
                # the `city` variable only contains letters and numbers, this
                # works easily, but you might need to be careful if searching for something
                # with punctuation as well.
                for match in re.finditer(city, paragraph_lower):
                    # We found an occurrence of the city, now we add it to the report!
                    # The necessary arguments are:
                    #    note  - the comment that should pop up
                    #            if you put your mouse over the highlighted text
                    #    start_offset and end_offset
                    #          - where the highlighting should start and end _relative
                    #            to the paragraph_ in characters.
                    #    level - which urgency group you want to put it in
                    #            (logging.INFO, logging.WARNING, logging.ERROR)
                    #            it's up to you.
                    #    tags  - (optional) any additional tags you want to make up.
                    content.add(
                        note=f'Occurence of {city.title()}',
                        start_offset=match.start(),
                        end_offset=match.end(),
                        level=logging.INFO,
                        tags=['city']
                    )

                # Maybe NI's capital gets too much attention? Maybe not?
                # This will emphasize uses of Belfast by putting them into a
                # warning group at the top.
                if city == 'belfast':
                    urgency = logging.WARNING
                else:
                    urgency = logging.INFO

                # Finally, we add our summary for this city in this paragraph to
                # the overall report.
                rprt.add_issue(
                    urgency,
                    'city-cropped-up',
                    f'Found {city}',
                    line_number=line_number,
                    character_number=0,
                    content=content
                )

    # Not all things we want to report have a location in the document - that's OK.
    # Here, we go through and a report item to display the total count for each city
    # in the entire document.
    for city, total in city_counts.items():
        rprt.add_issue(
            logging.INFO,
            'city-totals',
            f'Found {total} occurrences of {city.title()}'
        )

    return rprt

class CityFinderProcessor(DoorstepProcessor):
    """
    This class wraps some of the Lintol magic under the hood, that lets us plug
    our city finder into the online version, and create reports mixing and matching
    from various processors.
    """

    # This is the type of report we create - it could be tabular (e.g. CSV), geospatial
    # (e.g. GeoJSON) or document, as in this case.
    preset = 'document'

    # This is a unique code and version to identity the processor. The code should be
    # hyphenated, lowercase, and start with lintol-code-challenge
    code = 'lintol-code-challenge-city-finder:1'

    # This is a short phrase or description explaining the processor.
    description = _("City Finder for Lintol Coding Challenge")

    # Some of our processors get very complex, so this lets us build up execution graphs
    # However, for the coding challenge, you probably only want one or more steps.
    # To add two more, create functions like city_finder called town_finder and country_finder,
    # then uncomment the code in this function (and remove the extra parenthesis in the 'output' line)
    def get_workflow(self, filename, metadata={}):
        workflow = {
            'load-text': (load_text, filename),
            'get-report': (self.make_report,),
            'step-A': (city_finder, 'load-text', 'get-report'),
            # 'step-B': (town_finder, 'load-text', 'get-report'),
            # 'step-C': (country_finder, 'load-text', 'get-report'),
            'output': (workflow_condense, 'step-A') #, 'step-B', 'step-C')
        }
        return workflow

# If there are several steps, this final function pulls them into one big report.
def workflow_condense(base, *args):
    return combine_reports(*args, base=base)

# This is the actual variable Lintol looks for to set up the processor - you
# shouldn't need to touch it (except to change the class name, if neeeded)
processor = CityFinderProcessor.make

# Lintol will normally execute this processor in its own magical way, but you
# can also run it via the command line without using ltldoorstep at all (just the
# libraries already imported). The code below lets this happen, and prints out a
# JSON version of the report.
if __name__ == "__main__":
    argv = sys.argv
    processor = CityFinderProcessor()
    processor.initialize()
    workflow = processor.build_workflow(argv[1])
    print(get(workflow, 'output'))
