class KeyWordLocationsEntity:
        def __init__(self, key_word=None, locations=None) -> None:
            self.key_word=key_word
            self.locations = locations

class ProximityEntity:
    def __init__(self,dictionary_id=None,doc_header_id=None) -> None:
        self.dictionary_id = dictionary_id
        self.doc_header_id = doc_header_id
        self.key_word_bunch =[]


        