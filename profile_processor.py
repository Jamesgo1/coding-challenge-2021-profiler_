import requests
import xml.etree.ElementTree as ET
from datetime import timedelta, date, datetime
from collections import deque, namedtuple
import re

"""These classes form a similar function to hansard_prepper/py but also collects relevant 'Procedure Lines'  such as 
[Interruption.], [Laughter.], etc.

It also allows to create a corpus/document based on a date range.
"""


class HansardXMLValidator:
    """Occasionally the XML string creates a ParseError Exception which needs to be caught."""

    def __init__(self):
        self.hansard_exceptions_list = []
        self.current_request = None

    def valid_request(self):
        status = self.current_request.status_code
        if status != 200:
            print(f"Bad Request: {status}")
            print(self.current_request)
            return False
        return True

    def xml_exception_catcher(self):
        current_request_as_text = self.current_request.text
        print(current_request_as_text)
        try:
            et_request = ET.fromstring(current_request_as_text)
        except ET.ParseError:
            self.hansard_exceptions_list.append(("ParseError", current_request_as_text))
            et_request = None
        return et_request

    def validate_xml(self, url):
        self.current_request = requests.get(url)
        xml_root = self.xml_exception_catcher()
        if all([self.valid_request(), xml_root]):
            return xml_root


class XMLGenerator(HansardXMLValidator):
    """Validates and compiles XML files into a linked list for a given date range."""
    date_input_format = "%Y-%m-%d"
    base_url = r"http://data.niassembly.gov.uk/hansard.asmx/GetHansardComponentsByPlenaryDate?plenaryDate="

    def __init__(self, start_date: str, end_date: str):
        super().__init__()
        self.start_date = datetime.strptime(start_date, self.date_input_format)
        self.end_date = datetime.strptime(end_date, self.date_input_format)
        self.current_date = None

        self.current_xml_string = None
        self.root = None

        self.valid_xml_list = deque()
        self.parse_errors_log = []

    def create_date_range_iterator(self):
        """start_date inclusive; end_date exclusive."""
        for n in range(int((self.end_date - self.start_date).days)):
            dt_date = self.start_date + timedelta(n)
            yield dt_date.strftime("%Y-%m-%d")

    def filter_root_components(self, root_tag):
        url = self.base_url + self.current_date
        self.root = self.validate_xml(url)
        if self.root:
            hansard_components = [c for c in self.root if c.tag == root_tag]
            return hansard_components

    def get_valid_xml_string_if_contains_required_component(self, hansard_components):
        # We're only interested in documents that contain spoken text:
        if any([c for c in hansard_components if c.find("ComponentType").text == "Spoken Text"]):
            self.valid_xml_list.append(hansard_components)

    def run_for_all_dates(self):
        for date_ in self.create_date_range_iterator():
            self.current_date = date_
            hansard_components = self.filter_root_components("HansardComponent")
            self.get_valid_xml_string_if_contains_required_component(hansard_components)


class CorpusBuilder:
    """Creates the text data document from which we will base our analysis."""

    # Here's a reference list of the component types - in case any others seem of interest.
    all_component_types = {re.compile("Speaker.*"), 'Question', 'Division', 'Time', 'Bill Text', 'Written Statement',
                           'Procedure Line', 'Plenary Item Text', 'Header', 'Spoken Text', 'Document Title', 'Quote'}
    desired_component_types = {'Question', 'Procedure Line', 'Spoken Text'}
    procedures_to_add = {re.compile(r"\[Interruption.*"), re.compile(r"\[Laughter.*")}
    SpeakerComponent = namedtuple("SpeakerComponent", ["speaker", "text", "interjection"])
    unwanted_speaker_pattern = re.compile(r".*\sSpeaker.*|A\sMember|Some Members")

    def __init__(self, valid_xml_list):
        self.valid_xml_list = valid_xml_list

        self.all_questions = deque()

        self.component_id = None
        self.component_type = None  # Current Hansard Component Type
        self.component_text = None
        self.speech_tup = self.SpeakerComponent(None, None, None)

        self.speech_dict = {}
        self.component_error_log = []

    def get_component_id(self, component):
        self.component_id = component.find("ComponentId").text

    def identify_component_type_and_text(self, component):
        self.component_type = component.find("ComponentType").text
        self.component_text = component.find("ComponentText").text

    def collate_questions(self):
        self.all_questions.append(self.component_text)

    def remove_parentheses(self):
        """Some speakers' ministerial position is given in parentheses; these need to be removed for matching."""
        split_speaker = self.component_text.split("(", maxsplit=1)
        self.component_text = split_speaker[0].strip()

    def add_new_speaker(self):
        if self.speech_tup.speaker:
            self.speech_dict[self.component_id] = self.speech_tup
        self.component_text = self.component_text.replace(":", "")
        self.remove_parentheses()
        self.speech_tup = self.SpeakerComponent(self.component_text, None, None)

    def add_to_error_log(self):
        """This provides a reference of any examples of a speaker being given without any speech."""
        self.component_error_log.append((self.speech_tup, self.component_type, self.component_text))

    def add_spoken_text(self):
        if self.speech_tup.speaker and not self.speech_tup.text:
            self.speech_tup = self.speech_tup._replace(text=self.component_text)
        else:
            self.add_to_error_log()

    def add_procedure_line(self):
        if self.speech_tup.speaker and self.speech_tup.text and not self.speech_tup.interjection:
            if any([re.fullmatch(regex, self.component_text) for regex in self.procedures_to_add]):
                self.speech_tup = self.speech_tup._replace(interjection=self.component_text)

    def remove_unwanted_speakers(self):
        """Remove the assembly speaker and other non-MLAs"""
        self.speech_dict = {
            k: v for k, v in self.speech_dict.items() if not
            re.fullmatch(self.unwanted_speaker_pattern, v.speaker)
        }

    def create_speaker_text_dict(self):
        for components in self.valid_xml_list:
            relevant_components = [c for c in components if c.find("ComponentType").text in
                                   self.desired_component_types or
                                   re.fullmatch("Speaker.*", c.find("ComponentType").text)]
            for component in relevant_components:
                self.get_component_id(component)
                self.identify_component_type_and_text(component)
                if self.component_type == "Question":
                    self.collate_questions()
                elif re.fullmatch("Speaker.*", self.component_type):
                    self.add_new_speaker()
                elif self.component_type == "Spoken Text":
                    self.add_spoken_text()
                elif self.component_type == "Procedure Line":
                    print(self.component_text)
                    self.add_procedure_line()
                else:
                    self.component_error_log.append(
                        ("Not called on main method", self.component_type, self.component_text))
        self.remove_unwanted_speakers()
        return self.speech_dict


import gender_guesser.detector as gender_detector
from geopy.distance import distance
from geopy import Nominatim
from collections import namedtuple

"""The purpose of these classes is to extract the data necessary to assign speakers a 'profile' based on
parameters of interest. The 'Members' API on the niassembly page provides useful information to ensure data validity.

The ability to get a comprehensive list of members by any given date is particularly handy when looking at changes to 
data over time. However, having to iterate through a member list for each date can cause a significant bottleneck 
for larger date requests."""


class MLAProfiler(XMLGenerator):
    base_url = r"http://data.niassembly.gov.uk/members.asmx/GetAllMembersByGivenDate?specificDate="

    MLAInfo = namedtuple("MLAInfo", ["member_name", "party", "constituency", "person_id"])
    xml_member_tag_types = ["MemberFullDisplayName", "PartyName", "ConstituencyName", "PersonId"]
    tag_to_tuple_dict = dict(zip(xml_member_tag_types, MLAInfo._fields))

    def __init__(self, start_date, end_date):
        super().__init__(start_date, end_date)
        self.root = None
        self.all_member_xml = []
        self.current_member_ids = {}

        self.tag = None
        self.text = None

        self.current_named_tuple = None
        self.mla_info_dict = {}

        self.all_mla_profile_tuples = []

    def add_to_info_dict_for_named_tuple(self):
        if self.tag in self.xml_member_tag_types:
            tup_name = self.tag_to_tuple_dict[self.tag]
            self.mla_info_dict[tup_name] = self.text

    def build_new_tuple(self):
        self.current_named_tuple = self.MLAInfo(**self.mla_info_dict)

    def get_all_profiles_for_date_range(self):
        for date_ in self.create_date_range_iterator():
            self.current_date = date_
            member_components = self.filter_root_components("Member")
            new_member_components = [c for c in member_components if c.find("PersonId").text not in
                                     self.current_member_ids.keys()]
            for c in new_member_components:
                self.current_member_ids[c.find("PersonId").text] = c

    def create_named_tuples(self):
        self.get_all_profiles_for_date_range()
        member_profiles = [v for v in self.current_member_ids.values()]
        for member_components in member_profiles:
            for component in member_components:
                self.tag, self.text = component.tag, component.text
                self.add_to_info_dict_for_named_tuple()
            self.build_new_tuple()
            self.all_mla_profile_tuples.append(self.current_named_tuple)
            print(self.current_named_tuple)


class ProfileParameterCreator(MLAProfiler):
    is_male = {"Mr"}
    is_female = {"Ms", "Mrs", "Miss"}  # These are arguably not comprehensive but could not find any gendered examples
    # out of this range. Still worth considering any oversights here.

    stormont_lat_long = (54.592997628, -5.835329992)

    MLAParams = namedtuple("MLAParams", ["gender", "distance", "party", "constituency", "name"])

    def __init__(self, start_date, end_date):
        super().__init__(start_date, end_date)
        self.nia_constituency_list = []
        self.lat_long = None
        self.locator = Nominatim(user_agent="lintol_processor")

        self.not_all_params_available = []

    def assign_gender(self, name):
        gender = None
        name_split = name.split(" ")
        title = name_split[0]
        if title in self.is_male:
            gender = "male"
        elif title in self.is_female:
            gender = "female"
        else:
            first_name = name_split[1]
            detect = gender_detector.Detector()
            detected_gender = detect.get_gender(first_name)
            detected_gender.replace("mostly_", "")  # A more cautious approach to avoid any false positives would
            # likely wish to remove this line.
            if detected_gender in {"male", "female"}:
                gender = detected_gender
        return gender

    def find_constituency_locations(self):
        """Get constituency locations through new API call"""
        self.base_url = r"http://data.niassembly.gov.uk/members.asmx/GetAllMemberContactDetails?"
        url = self.base_url + self.current_date
        self.root = self.validate_xml(url)
        member_constituency_list = [c for c in self.root if c.tag == "Member"]
        self.nia_constituency_list = [c for c in member_constituency_list if
                                      c.find("AddressType").text == "NIA Constituency Address"]

    def get_lat_long(self, components):
        c = components[0]
        lat, long = c.find("Latitude"), c.find("Longitude")
        if lat is not None and long is not None:
            self.lat_long = (lat.text, long.text)

    def get_constituency_distance_from_stormont(self, person_id):
        dist = None
        components = [c for c in self.nia_constituency_list if c.find("PersonId").text == person_id]
        self.lat_long = None
        if components:
            self.get_lat_long(components)
        if self.lat_long:
            dist = distance(self.stormont_lat_long, self.lat_long).miles
        return dist

    def create_parameters_from_mla_data(self):
        self.create_named_tuples()
        self.find_constituency_locations()
        mla_param_dict = {}
        for t in self.all_mla_profile_tuples:
            name, party, constituency, person_id = list(t)
            gender = self.assign_gender(name)
            distance_from_stormont = self.get_constituency_distance_from_stormont(person_id)

            params = [gender, distance_from_stormont, party, constituency, name]
            mla_params = self.MLAParams(*params)
            mla_param_dict[person_id] = mla_params
        return mla_param_dict


# import build_hansard_corpus, mla_profiling
from collections import Counter, namedtuple
from datetime import datetime

"""This file performs the task of matching the speaker name in the 'members' API call to the name of the speaker in 
the Hansard documents. The process involves removing duplicate names for the first round of matching. 
Although Hansard tends to add a first name initial for MLAs with matching surnames, it still could throw up some 
misleading matches which we'd want to avoid. 

The matching process is not comprehensive - what if two MLAs of the same gender have the same surname AND initial? This 
is yet to be accounted for.
"""


class HansardToMemberConnector:
    CombinedData = namedtuple("CombinedData", ["profile_id", "hansard_speaker", "hansard_text", "interjection",
                                               "gender", "constituency_distance", "party",
                                               "constituency", "mla_speaker"])

    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date

        self.all_speech = None
        self.mla_profile_dicts = None

        self.split_names_dict = {}
        self.deduped_speakers, self.dupe_speakers = {}, {}

        self.matched_components_dict = {}
        self.unmatched_components_dict = {}
        self.current_unmatched_speech = {}

    def get_speech_data(self):
        valid_xmls = XMLGenerator(self.start_date, self.end_date)
        valid_xmls.run_for_all_dates()
        corp = CorpusBuilder(valid_xmls.valid_xml_list)
        self.all_speech = corp.create_speaker_text_dict()
        return self.all_speech

    def get_mla_data(self):
        ppc = ProfileParameterCreator(self.start_date, self.end_date)
        self.mla_profile_dicts = ppc.create_parameters_from_mla_data()
        return self.mla_profile_dicts

    def split_duplicate_names_to_separate_dict(self):
        names_dict = {k: v.name for k, v in self.mla_profile_dicts.items()}
        self.split_names_dict = {k: v.split(" ") for k, v in names_dict.items()}
        speaker_name_dict = {k: " ".join([v[0], v[-1]]) for k, v in self.split_names_dict.items()}

        speaker_name_counter = Counter([v for v in speaker_name_dict.values()])
        duplicate_speaker_names = {k for k, v in speaker_name_counter.items() if v > 1}
        duplicate_keys = {k for k, v in speaker_name_dict.items() if v in duplicate_speaker_names}

        self.deduped_speakers = {k: v for k, v in speaker_name_dict.items() if k not in duplicate_keys}
        self.dupe_speakers = {k: v for k, v in speaker_name_dict.items() if k in duplicate_keys}

    def update_unmatched_components(self):
        self.current_unmatched_speech = {k: v for k, v in self.current_unmatched_speech.items() if
                                         k not in self.matched_components_dict.keys()}
        for d in self.current_unmatched_speech.items():
            print(d)

    def match_hansard_to_speaker(self, hansard_dict_item, speaker_dict):
        component_id, speech_tup = hansard_dict_item
        for speaker_id, speaker in speaker_dict.items():
            if speech_tup.speaker == speaker:
                self.matched_components_dict[component_id] = speaker_id
                break

    def title_surname_match(self):
        for hansard_dict_item in self.all_speech.items():
            self.match_hansard_to_speaker(hansard_dict_item, self.deduped_speakers)
        self.update_unmatched_components()

    def get_speakers_dict_as_title_initial_surname(self):
        initial_added_dict = {}
        for k, v in self.split_names_dict.items():
            new_v = " ".join([v[0], v[1][0], v[-1]])
            initial_added_dict[k] = new_v
        return initial_added_dict

    def title_initial_surname_match(self):
        initial_added_dict = self.get_speakers_dict_as_title_initial_surname()
        for hansard_dict_item in self.current_unmatched_speech.items():
            self.match_hansard_to_speaker(hansard_dict_item, initial_added_dict)
        self.update_unmatched_components()

    def get_speakers_dict_as_dual_surname(self):
        dual_surname_dict = {}
        for k, v in self.split_names_dict.items():
            if len(v) > 3:
                new_v = " ".join([v[0], v[-2], v[-1]])
                dual_surname_dict[k] = new_v
        return dual_surname_dict

    def dual_surname_match(self):
        dual_surname_dict = self.get_speakers_dict_as_dual_surname()
        for hansard_dict_item in self.current_unmatched_speech.items():
            self.match_hansard_to_speaker(hansard_dict_item, dual_surname_dict)
        self.update_unmatched_components()

    def run_all_matching(self):
        self.split_duplicate_names_to_separate_dict()
        self.current_unmatched_speech = self.all_speech
        self.title_surname_match()
        self.title_initial_surname_match()
        self.dual_surname_match()

    def unify_data(self):
        combined_data_dict = {}
        for k, v in self.matched_components_dict.items():
            hansard_data = self.all_speech[k]
            profile_data = self.mla_profile_dicts[v]
            combined_data_fields = [v, *hansard_data, *profile_data]
            combined_data_tup = self.CombinedData(*combined_data_fields)
            combined_data_dict[k] = combined_data_tup
        return combined_data_dict

    def full_hansard_member(self):
        self.run_all_matching()
        combined = self.unify_data()
        return combined


from collections import namedtuple
import re
import spacy
from spacytextblob.spacytextblob import SpacyTextBlob


class AnalyticsCreator:
    """Adds desired datapoints to each hansard element in the inputted named_tuple. This class acts a bit like a
    library of different methods that can be incorporateed as and when they are desired."""

    def __init__(self, combined_dict):
        self.combined_dict = combined_dict
        self.current_tup = None
        self.CountAddedTuple = None
        self.new_field_name = None

        self.analytics_to_add_dict = {}

        self.nlp = None

    def create_named_tuple_with_additional_analytic(self):
        for d in self.combined_dict.items():
            print(d)
        first_key = list(self.combined_dict.keys())[0]
        a_current_named_tuple = self.combined_dict[first_key]
        print(a_current_named_tuple._fields)
        return namedtuple("NewTuple", a_current_named_tuple._fields + (self.new_field_name,))

    def get_word_count(self):
        word_count = 0
        if self.current_tup.hansard_text:
            word_list = self.current_tup.hansard_text.split(" ")
            word_count = len(word_list)
        return word_count

    def get_whether_interrupted(self):
        is_interrupted = 0
        interjection = self.current_tup.interjection
        if interjection:
            if re.fullmatch(r".*Interruption.*", interjection):
                is_interrupted = 1
        return is_interrupted

    def preprocessing_spacy(self):
        """This is loaded first to avoid re-loading on every iteration."""
        if not self.nlp:
            self.nlp = spacy.load("en_core_web_md")
            spacy_text_blob = SpacyTextBlob()
            self.nlp.add_pipe(spacy_text_blob)

    def get_sentiment_subjectivity(self):
        text = self.current_tup.hansard_text
        doc = self.nlp(text)
        subjectivity = doc._.sentiment.subjectivity
        print(subjectivity)
        return subjectivity

    def get_sentiment_polarity(self):
        text = self.current_tup.hansard_text
        doc = self.nlp(text)
        polarity = doc._.sentiment.polarity
        print(polarity)
        return polarity

    def add_datapoint_to_named_tuple(self, func_to_add, prepocessing_func=None):
        if prepocessing_func:
            prepocessing_func()
        NewTuple = self.create_named_tuple_with_additional_analytic()
        for k, tup in self.combined_dict.items():
            self.current_tup = tup
            word_count = func_to_add()
            new_tuple = NewTuple(*tup, word_count)
            self.combined_dict[k] = new_tuple

    def add_word_count(self):
        self.new_field_name = "word_count"
        self.add_datapoint_to_named_tuple(self.get_word_count)

    def compile_analytics_to_add_dict(self):
        self.analytics_to_add_dict = {
            "word_count": [self.get_word_count],
            "interruptions_count": [self.get_whether_interrupted],
            "subjectivity": [self.get_sentiment_subjectivity, self.preprocessing_spacy],
            "polarity": [self.get_sentiment_polarity, self.preprocessing_spacy]
        }

    def add_to_tuple(self):
        self.compile_analytics_to_add_dict()
        for field_name, functions_list in self.analytics_to_add_dict.items():
            get_function = functions_list[0]
            preprocessor = None
            if len(functions_list) == 2:
                preprocessor = functions_list[1]
            self.new_field_name = field_name
            self.add_datapoint_to_named_tuple(get_function, prepocessing_func=preprocessor)
        for d in self.combined_dict.items():
            print(d)
        return self.combined_dict


class ProportionCalculator:
    """In order to extract meaning from e.g. no. of words spoken by gender, we need to know the underlying
    distribution of MLAs."""

    def __init__(self, mla_param_dict, desired_identifiers):
        self.mla_param_dict = mla_param_dict
        self.desired_identifiers = desired_identifiers

        self.proportions_dict = {}
        self.current_tup = None

    def get_proportions(self, identifier):
        tuple_list = [v for v in self.mla_param_dict.values()]
        dict_list = [v._asdict() for v in tuple_list]
        identifier_count = {}
        for d in dict_list:
            id_output = d[identifier]
            count_value = identifier_count.get(id_output)
            if count_value:
                identifier_count[id_output] += 1
            else:
                identifier_count[id_output] = 1

        total_count = sum([v for v in identifier_count.values()])

        identifier_as_proportion = {k: v / total_count for k, v in identifier_count.items()}
        return identifier_as_proportion

    def get_all_proportions(self):
        sample_named_tuple = [v for v in self.mla_param_dict.values()][0]
        all_identifiers = [i for i in self.desired_identifiers if i in sample_named_tuple._fields]
        all_identifier_counts = list(map(self.get_proportions, all_identifiers))
        identifier_counts_dict = dict(zip(all_identifiers, all_identifier_counts))
        return identifier_counts_dict


class DiscreteAnalyticsCreator:
    """Groups analytics at the hansard component level into chosen identifiers with a meaningfully limited number of
    discrete groups"""

    get_mean_metrics = {"subjectivity", "polarity"}
    get_proportional = {"word_count", "interruptions_count"}

    def __init__(self, combined_analytics_dict, proportions_dict):
        self.combined_analytics_dict = combined_analytics_dict
        self.proportions_dict = proportions_dict

        self.desired_identifiers = None
        self.desired_metrics = None

        self.current_identifier = None
        self.current_metric = None

        self.current_identifier_count = {}
        self.totalizer_dicts = {}

    def get_tuples_as_dict(self):
        tuple_list = [v for v in self.combined_analytics_dict.values()]
        dict_list = [v._asdict() for v in tuple_list]
        return dict_list

    def totalize_metric_for_identifier(self):
        dict_list = self.get_tuples_as_dict()

        self.current_identifier_count = {}
        for d in dict_list:
            id_output = d[self.current_identifier]
            identifier_grouping = self.current_identifier_count.get(id_output)

            identifier_value = d[self.current_metric]

            if identifier_grouping:
                self.current_identifier_count[id_output] += identifier_value
            else:
                self.current_identifier_count[id_output] = identifier_value

    def calculate_average(self):
        identifier_average = {k: v / len(self.combined_analytics_dict) for k, v in
                              self.current_identifier_count.items()}
        return identifier_average

    def calculate_proportion(self):
        total_count_for_metric = sum([v for v in self.current_identifier_count.values()])
        proportion_of_total_count_by_grouping = {k: v / total_count_for_metric for k, v in
                                                 self.current_identifier_count.items()}
        expected_proportions_dict = self.proportions_dict[self.current_identifier]

        proportion_diff_dict = {}
        for k, v in proportion_of_total_count_by_grouping.items():
            expected_proportion = expected_proportions_dict[k]
            proportion_found = v
            proportion_diff = proportion_found - expected_proportion
            proportion_diff_as_pcnt = proportion_diff * 100
            proportion_diff_as_pcnt_1dp = round(proportion_diff_as_pcnt, 1)
            proportion_diff_dict[k] = proportion_diff_as_pcnt_1dp
        return proportion_diff_dict

    def run_calculation(self):
        if self.current_metric in self.get_mean_metrics:
            analytic_output_dict = self.calculate_average()
        else:
            analytic_output_dict = self.calculate_proportion()
        return analytic_output_dict

    def get_all_desired_metrics_for_all_desired_identifiers(self):
        overall_analytics_summary = {identifier: {} for identifier in self.desired_identifiers}
        for identifier in self.desired_identifiers:
            self.current_identifier = identifier
            for metric in self.desired_metrics:
                self.current_metric = metric
                self.totalize_metric_for_identifier()
                calc_output_dict = self.run_calculation()
                overall_analytics_summary[identifier][metric] = calc_output_dict
        return overall_analytics_summary


import spacy

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_analyzer.nlp_engine import SpacyNlpEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.anonymizers import Replace
from presidio_anonymizer.entities import AnonymizerRequest
from presidio_anonymizer.entities import AnonymizerConfig


class HansardTextFormatter:
    def __init__(self):
        SpacyRecognizer.ENTITIES = ["PERSON"]
        Replace.NEW_VALUE = 'replace_text'
        nlp_engine = SpacyNlpEngine()
        nlp_engine.nlp['en'] = spacy.load('en_core_web_lg', disable=["parser", "tagger", "lemmatizer"])

        self.analyzer_engine = AnalyzerEngine(nlp_engine=nlp_engine)
        self.anonymizer_engine = AnonymizerEngine()

    def run_anonymizer(self, text):
        results = self.analyzer_engine.analyze(text=text,
                                               entities=[],
                                               language='en',
                                               score_threshold=0.5)
        if results:
            config = {"PERSON": AnonymizerConfig("replace", {"replace_text": "[GDPRREDACT]"})}
            return self.anonymizer_engine.anonymize(text, results, config)

    @staticmethod
    def clean_text(text):
        text = text.replace('\n', '')
        text = text.replace('<BR />', '\n')
        return text

    def run_formatter(self, text):
        anon_text = self.run_anonymizer(text)
        cleaned_text = self.clean_text(anon_text)
        return cleaned_text


hansard_anon = HansardTextFormatter()

txt = "I assure you, a Cheann Comhairle, that I will stick to the Budget. I am afraid to look at Mervyn in case he thinks that there are any notions."
anon_txt = hansard_anon.run_anonymizer(txt)
print(anon_txt)

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

from datetime import datetime, timedelta

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
        self.hansard_member = HansardToMemberConnector(self.start_date, self.end_date)

    def get_mla_profile_dict(self):
        # Compile profile data about MLAs that were active between start and end date.
        return self.hansard_member.get_mla_data()

    def get_speech_data(self):
        # Add speech and profile data to hansard_member object
        self.hansard_member.get_speech_data()

    def get_data_with_analytics(self):
        # Create a dictionary of component id: namedtuple to connect up the spoken data with the mla speaking.
        combined_dict = self.hansard_member.full_hansard_member()

        # Use this dictionary to run analytics on the spoken text and add these datapoints to a new namedtuple.
        analytics_creator = AnalyticsCreator(combined_dict)
        combined_analytics_dict = analytics_creator.add_to_tuple()
        return combined_analytics_dict

    def run_profile_analysis(self):
        self.get_hansard_data_obj()

        # Request and order data.
        mla_profile_dict = self.get_mla_profile_dict()
        self.get_speech_data()

        combined_analytics_dict = self.get_data_with_analytics()

        # Go back to the mla dictionary to get base proportions of different identifiers.
        # E.g. we want to know the % of female MLAs in order to then compare the % of female words spoken.
        prop_calc = ProportionCalculator(mla_profile_dict, self.identifiers)
        identifier_counts_dict = prop_calc.get_all_proportions()

        # Now we can run the analysis to compare how these proportions differ for identifier groupings.
        disc_analytics = DiscreteAnalyticsCreator(combined_analytics_dict, identifier_counts_dict)
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
        text_formatter = HansardTextFormatter()
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
    profile_analyzer.set_default()

    # Run methods to get our two desired output dictionaries: adata dictionary that contains the text, and an analytics
    # dictionary that contains the stats.
    data_dictionary, stats_dictionary = profile_analyzer.run_profile_analysis()
    # Iterate through identifier keys in our stats_dictionary to format output for lintol doorstep.
    for identifier, analytic_dict in stats_dictionary.items():
        for analytic, datapoints in analytic_dict.items():
            for datapoint, value in datapoints.items():
                if OUTPUT_ANALYTICS[analytic] == "proportional":
                    data_description = f"For {analytic}, the score for {datapoint} was {str(value)}% compared to " \
                                       f"their proportional share."
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
