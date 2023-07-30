class DictionaryEntity:
    def __init__(self, dictionary_id=None, keywords=None, internalization_id=None, exposure_path_id=None,impact_category_id=None,esg_category_id=None) -> None:
        self.dictionary_id = dictionary_id
        self.keywords = keywords
        self.internalization_id = internalization_id
        self.exposure_path_id = exposure_path_id
        self.impact_category_id = impact_category_id
        self.esg_category_id = esg_category_id
