from processor_classes import speaker_to_profile, profile_analysis

hansard_member = speaker_to_profile.HansardToMemberConnector(start_date="2020-02-20", end_date="2020-02-28")
hansard_member.get_speech_data()
hansard_member.get_mla_data()
combined_dict = hansard_member.full_hansard_member()
p_an = profile_analysis.AnalyticsCreator(combined_dict)
p_an.add_to_tuple()
