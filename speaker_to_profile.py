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
        valid_xmls = build_hansard_corpus.XMLGenerator(self.start_date, self.end_date)
        valid_xmls.run_for_all_dates()
        corp = build_hansard_corpus.CorpusBuilder(valid_xmls.valid_xml_list)
        self.all_speech = corp.create_speaker_text_dict()
        return self.all_speech

    def get_mla_data(self):
        ppc = mla_profiling.ProfileParameterCreator(self.start_date, self.end_date)
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
