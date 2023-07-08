class DictionaryEntity:
    def __init__(self, dictionary_id=None, keywords=None, internalization_id=None, exposure_pathway_id=None) -> None:
        self.dictionary_id = dictionary_id
        self.keywords = keywords
        self.internalization_id = internalization_id
        self.exposure_pathway_id = exposure_pathway_id
