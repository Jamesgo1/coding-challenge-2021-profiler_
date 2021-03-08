from processor_classes.build_hansard_corpus import XMLGenerator, CorpusBuilder
from tests import pkl

valid_xmls = XMLGenerator("2021-02-20", "2021-02-26")
valid_xmls.run_for_all_dates()
t1 = pkl.pickle_o("xml_hansard")  # Remove Pickle
corp = CorpusBuilder(t1)
speech = corp.create_speaker_text_dict()
