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
