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
            "polarity": [self.get_sentiment_subjectivity, self.preprocessing_spacy]
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
            proportion_diff_dict[k] = proportion_diff
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
