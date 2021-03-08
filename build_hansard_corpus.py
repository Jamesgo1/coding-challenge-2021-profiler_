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
