"""
Profile Deconstructor Processor
---------------------

This is the main doc, but the commandline decided it didn't like me importing my own files. Therefore I had to resort to
creating a single (very long) processor file.
"""

import re
import sys
import logging
from dask.threaded import get

from ltldoorstep.processor import DoorstepProcessor
from ltldoorstep.aspect import AnnotatedTextAspect
from ltldoorstep.reports.report import combine_reports
from ltldoorstep.document_utils import load_text, split_into_paragraphs

from datetime import datetime, timedelta

import speaker_to_profile
import profile_analysis
import new_hansard_prepper

# These are the different ways we can profile MLAs.
# TODO: Create discrete boundaries for distance_from_stormont to enable its use as an identifier.
IDENTIFIERS = {"gender", "party", "constituency"}

# These are the parameters by which these identifier groups are then analyzed.
OUTPUT_ANALYTICS = {"word_count": "proportional", "interruptions_count": "proportional", "polarity": "absolute",
                    "subjectivity": "absolute"}


class ProfileAnalyzer:

    def __init__(self):
        self.identifiers = None
        self.output_analytics = None

        self.start_date = None
        self.end_date = None

        self.hansard_member = None

    def get_identifiers(self, *args: str):
        self.identifiers = [i for i in args if i in IDENTIFIERS]

    def get_output_analytics(self, *args: str):
        self.output_analytics = [out for out in args if out in OUTPUT_ANALYTICS.keys()]

    def get_date_range(self, start_date: str = None, end_date: str = None):
        self.start_date = start_date
        self.end_date = end_date

    def set_default(self):
        """Ensures no arguments are mandatory to run the processor without error. Processor defaults to running all
        variables for all analytics for the past week of data."""

        if not self.identifiers:
            self.identifiers = IDENTIFIERS
        if not self.output_analytics:
            self.output_analytics = OUTPUT_ANALYTICS

        date_now = datetime.now()
        last_week = date_now - timedelta(days=7)
        date_now_as_str = date_now.strftime("%Y-%m-%d")
        last_week_as_str = last_week.strftime("%Y-%m-%d")
        if not self.start_date:
            self.start_date = last_week_as_str
        if not self.end_date:
            self.end_date = date_now_as_str

    def get_hansard_data_obj(self):
        self.set_default()

        # Intialize data collection object for desired date range.
        self.hansard_member = speaker_to_profile.HansardToMemberConnector(self.start_date, self.end_date)

    def get_mla_profile_dict(self):
        # Compile profile data about MLAs that were active between start and end date.
        mla_profile_dict = self.hansard_member.get_mla_data()
        return mla_profile_dict

    def get_data_with_analytics(self):
        # Compile speech data (Hansard) for this date range.
        self.hansard_member.get_speech_data()

        # Create a dictionary of component id: namedtuple to connect up the spoken data with the mla speaking.
        combined_dict = self.hansard_member.full_hansard_member()

        # Use this dictionary to run analytics on the spoken text and add these datapoints to a new namedtuple.
        analytics_creator = profile_analysis.AnalyticsCreator(combined_dict)
        combined_analytics_dict = analytics_creator.add_to_tuple()
        return combined_analytics_dict

    def run_profile_analysis(self):
        combined_analytics_dict = self.get_data_with_analytics()
        mla_profile_dict = self.get_mla_profile_dict()

        # Go back to the mla dictionary to get base proportions of different identifiers.
        # E.g. we want to know the % of female MLAs in order to then compare the % of female words spoken.
        prop_calc = profile_analysis.ProportionCalculator(mla_profile_dict, self.identifiers)
        identifier_counts_dict = prop_calc.get_all_proportions()

        # Now we can run the analysis to compare how these proportions differ for identifier groupings.
        disc_analytics = profile_analysis.DiscreteAnalyticsCreator(combined_analytics_dict, identifier_counts_dict)
        disc_analytics.desired_identifiers = self.identifiers
        disc_analytics.desired_metrics = self.output_analytics

        # The output format is split by identifer which gives an analysis for each grouping for that identifier.
        output_dict = disc_analytics.get_all_desired_metrics_for_all_desired_identifiers()
        return combined_analytics_dict, output_dict


class LintolPrepper:
    """This class preps the analytics output dictionary to be plugged into Lintol's doorstep utility for
    highlighting useful phrases based on a member profile."""

    # TODO: Integrate text finding into processor.
    def __init__(self, analytics_output_dict, data_dict):
        self.analytics_output_dict = analytics_output_dict
        self.data_dict = data_dict

    def clean_hansard_text(self):
        text_formatter = new_hansard_prepper.HansardTextFormatter()
        for k, v in self.data_dict.items():
            txt = v.hansard_text
            clean_txt = text_formatter.run_formatter(txt)
            new_v = v._replace(hansard_text=clean_txt)
            self.data_dict[k] = new_v


def run_default_analysis(rprt):
    """
    Add report items to indicate where cities appear, and how often in total
    """

    # No need to add any arguments as we're running default.
    profile_analyzer = ProfileAnalyzer()

    # Run methods to get our two desired output dictionaries: adata dictionary that contains the text, and an analytics
    # dictionary that contains the stats.
    data_dictionary, stats_dictionary = profile_analyzer.run_profile_analysis()

    # Iterate through identifier keys in our stats_dictionary to format output for lintol doorstep.
    for identifier, analytic_dict in stats_dictionary.items():
        for analytic, datapoints in analytic_dict.items():
            for datapoint, value in datapoints.items():
                if OUTPUT_ANALYTICS[analytic] == "proportional":
                    data_description = f"For {analytic}, the score for {datapoint} was {str(value)} higher than their proportional share."
                else:
                    data_description = f"For {analytic}, {datapoint} scored {str(value)}"

                rprt.add_issue(
                    logging.INFO,
                    f"Analytics for {identifier}",
                    data_description
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
    code = 'lintol-code-challenge-profile-deconstructor:1'

    # This is a short phrase or description explaining the processor.
    description = "Insight finder by type of speaker as part of Lintol Coding Challenge"

    # Some of our processors get very complex, so this lets us build up execution graphs
    # However, for the coding challenge, you probably only want one or more steps.
    # To add two more, create functions like city_finder called town_finder and country_finder,
    # then uncomment the code in this function (and remove the extra parenthesis in the 'output' line)
    def get_workflow(self, filename, metadata={}):
        workflow = {
            # 'load-text': (load_text, filename),
            'get-report': (self.make_report,),
            'step-A': (run_default_analysis, 'get-report'),
            # 'step-B': (town_finder, 'load-text', 'get-report'),
            # 'step-C': (country_finder, 'load-text', 'get-report'),
            'output': (workflow_condense, 'step-A')  # , 'step-B', 'step-C')
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
    print(argv)
    processor = CityFinderProcessor()
    processor.initialize()
    workflow = processor.build_workflow(argv[1])
    print(get(workflow, 'output'))
