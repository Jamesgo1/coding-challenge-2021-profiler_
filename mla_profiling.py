import build_hansard_corpus
import gender_guesser.detector as gender_detector
from geopy.distance import distance
from geopy import Nominatim
from collections import namedtuple

"""The purpose of these classes is to extract the data necessary to assign speakers a 'profile' based on
parameters of interest. The 'Members' API on the niassembly page provides useful information to ensure data validity.

The ability to get a comprehensive list of members by any given date is particularly handy when looking at changes to 
data over time. However, having to iterate through a member list for each date can cause a significant bottleneck 
for larger date requests."""


class MLAProfiler(build_hansard_corpus.XMLGenerator):
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
