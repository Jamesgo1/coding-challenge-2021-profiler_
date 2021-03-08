"""This is the processor file built upon the files created in the 'processor classes' package."""

from processor_classes import speaker_to_profile, profile_analysis
from arg_parser import parse_args

my_parser = parse_args.get_arg_variables()
args = my_parser.parse_args()
hansard_member = speaker_to_profile.HansardToMemberConnector(start_date=args.start_date,
                                                             end_date=args.end_date)
desired_identifiers = {"gender", "party"}

mla_prof_dicts = hansard_member.get_mla_data()
prop_calc = profile_analysis.ProportionCalculator(mla_prof_dicts, desired_identifiers)
identifier_counts_dict = prop_calc.get_all_proportions()

hansard_member.get_speech_data()
combined_dict = hansard_member.full_hansard_member()
analytics_creator = profile_analysis.AnalyticsCreator(combined_dict)
combined_analytics_dict = analytics_creator.add_to_tuple()

disc_analytics = profile_analysis.DiscreteAnalyticsCreator(combined_analytics_dict, identifier_counts_dict)
disc_analytics.desired_identifiers = desired_identifiers
disc_analytics.desired_metrics = ["word_count", "interruptions_count", "polarity", "subjectivity"]
output_dict = disc_analytics.get_all_desired_metrics_for_all_desired_identifiers()
for i in output_dict.items():
    print(i)
