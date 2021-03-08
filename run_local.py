import profile_processor_with_imports

profile_analyzer = profile_processor_with_imports.ProfileAnalyzer()
profile_analyzer.get_identifiers("gender")
profile_analyzer.get_output_analytics("word_count")
profile_analyzer.get_date_range(start_date="2020-01-01", end_date="2021-01-01")
analysis_output_dict = profile_analyzer.run_profile_analysis()