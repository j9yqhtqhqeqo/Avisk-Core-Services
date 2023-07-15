class KeyWordLocationsEntity:
    def __init__(self, key_word=None, locations=None, frequency = 0, dictionary_type =0, dictionary_id =0, document_id =0, document_name='') -> None:
        self.key_word=key_word
        self.key_word_hit_id:int
        self.locations = locations
        self.frequency = frequency
        self.dictionary_type = dictionary_type
        self.dictionary_id = dictionary_id
        self.document_id = document_id
        self.document_name = document_name
        self.batch_id = 0

class DocumentEntity:
    def __init__(self, document_id =0, document_name=0, company_name='', year=0, insights_generated=0) -> None:
        self.document_id = document_id
        self.document_name = document_name
        self.company_name=company_name
        self.company_id = 0
        self.year = year
        self.insights_generated = insights_generated


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



class Insight:
    def __init__(self,keyword_hit_id1=0, keyword1='', keyword_hit_id2=0, keyword2='',score=0.00, factor1=0, factor2=0,document_name='', document_id=0) -> None:
        self.keyword_hit_id1 = keyword_hit_id1
        self.keyword1 = keyword1
        self.keyword_hit_id2 = keyword_hit_id2
        self.keyword2 = keyword2
        self.factor1 = factor1
        self.factor2 = factor2
        self.score = score
        self.document_name = document_name
        self.document_id = document_id