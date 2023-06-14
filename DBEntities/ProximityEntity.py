class KeyWordLocationsEntity:
    def __init__(self, key_word=None, locations=None, frequency = 0) -> None:
        self.key_word=key_word
        self.key_word_hit_id:int
        self.locations = locations
        self.frequency = frequency

class ProximityEntity:
    def __init__(self,dictionary_id=None,doc_header_id=None) -> None:
        self.dictionary_id = dictionary_id
        self.doc_header_id = doc_header_id
        self.key_word_bunch =[]


class FD_Factor:
    def __init__(self,keyword_hit_id:int, keyword:str, frequency:int) -> None:
        self.keyword_hit_id = keyword_hit_id
        self.keyword = keyword
        self.parent_keyword_frequency = frequency
        self.child_keyword_frequency =[]
        self.fd_factor = []
    
    def add_fd_factor(self,fd_factor:float, child_keyword_frequency: int):
        self.fd_factor.append(fd_factor)
        self.child_keyword_frequency.append(child_keyword_frequency)


        # select key_word_hit_id, key_word, locations from t_key_word_hits where insights_generated = 0 and document_id = 11