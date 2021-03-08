import sys
import xml.etree.ElementTree as ET

import spacy

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_analyzer.nlp_engine import SpacyNlpEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.anonymizers import Replace
from presidio_anonymizer.entities import AnonymizerRequest


def run_anonymizer(engine, text, analyzer_results, transformations=None):
    req = AnonymizerRequest({
        'analyzer_results': [res.to_dict() for res in analyzer_results],
        'text': text,
        'transformations': transformations
    }, AnonymizerEngine.builtin_anonymizers)
    trans = req.get_transformation('PERSON')
    trans['replace_text'] = "[GDPRREDACT]"
    return engine.anonymize(req)


class HansardCleaner:
    def initialize(self):
        SpacyRecognizer.ENTITIES = ["PERSON"]
        Replace.NEW_VALUE = 'replace_text'
        nlp_engine = SpacyNlpEngine()
        nlp_engine.nlp['en'] = spacy.load('en_core_web_lg', disable=["parser", "tagger", "lemmatizer"])

        self.analyzer_engine = AnalyzerEngine(nlp_engine=nlp_engine)
        self.anonymizer_engine = AnonymizerEngine()

    def run(self, xml_filename):
        etree = ET.parse(xml_filename)

        for elem in etree.iter():
            text = elem.text.strip()
            if text:
                results = self.analyzer_engine.analyze(correlation_id=0,
                                                       text=text,
                                                       entities=[],
                                                       language='en',
                                                       score_threshold=0.5)
                if results:
                    elem.text = run_anonymizer(self.anonymizer_engine, text, results)

        new_filename = f'out-{xml_filename}'
        etree.write(new_filename)
        return new_filename


class HansardTextExtractor:
    def run(self, xml_filename):
        etree = ET.parse(xml_filename)

        proceedings_plaintext = ''

        for component in etree.getroot():
            if component.tag == 'HansardComponent':
                component_type_node = component.find('ComponentType')
                component_text_node = component.find('ComponentText')
                if component_text_node.text and component_type_node.text:
                    if component_type_node.text.strip() == 'Spoken Text':
                        text = component_text_node.text.replace('\n', '')
                        text = text.replace('<BR />', '\n')
                        proceedings_plaintext += f'{text}\n\n----\n\n'
                    elif component_type_node.text.strip() == 'Header':
                        proceedings_plaintext += f'[{component_text_node.text.upper()}]\n\n'

        text_filename = xml_filename.replace('.xml', '.txt')
        with open(text_filename, 'w') as text_file:
            text_file.write(proceedings_plaintext)


if __name__ == "__main__":
    try:
        filename = sys.argv[1]
    except KeyError as e:
        print("Hansard Cleaner takes one argument, the XML file to be cleaned.")
        raise e

    cleaner = HansardCleaner()
    cleaner.initialize()
    cleaner.run(filename)
    filename = cleaner.run(filename)
    extractor = HansardTextExtractor()
    extractor.run(filename)
