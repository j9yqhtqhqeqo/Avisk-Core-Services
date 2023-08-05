class KeyWordLocationsEntity:
    def __init__(self, key_word=None, locations=None, frequency=0, dictionary_type=0, dictionary_id=0, document_id=0, document_name='', exposure_path_id=0, intenalization_id=0) -> None:
        self.key_word = key_word
        self.key_word_hit_id: int
        self.locations = locations
        self.frequency = frequency
        self.dictionary_type = dictionary_type
        self.dictionary_id = dictionary_id
        self.document_id = document_id
        self.document_name = document_name
        self.batch_id = 0
        self.exposure_path_id = exposure_path_id
        self.intenalization_id = intenalization_id

        self.temp_place_holder = ''


class DocumentEntity:
    def __init__(self, document_id=0, document_name=0, company_name='', year=0, insights_generated=0) -> None:
        self.document_id = document_id
        self.document_name = document_name
        self.company_name = company_name
        self.company_id = 0
        self.year = year
        self.insights_generated = insights_generated


class ProximityEntity:
    def __init__(self, dictionary_id=None, doc_header_id=None, exposure_path_id=0, internalization_id=0, impact_category_id=0, esg_category_id=0) -> None:
        self.dictionary_id = dictionary_id
        self.doc_header_id = doc_header_id
        self.exposure_path_id = exposure_path_id
        self.internalization_id = internalization_id
        self.impact_category_id = impact_category_id
        self.esg_category_id = esg_category_id
        self.key_word_bunch = []


class FD_Factor:
    def __init__(self, keyword_hit_id: int, keyword: str, frequency: int) -> None:
        self.keyword_hit_id = keyword_hit_id
        self.keyword = keyword
        self.parent_keyword_frequency = frequency
        self.child_keyword_frequency = []
        self.fd_factor = []

    def add_fd_factor(self, fd_factor: float, child_keyword_frequency: int):
        self.fd_factor.append(fd_factor)
        self.child_keyword_frequency.append(child_keyword_frequency)

        # select key_word_hit_id, key_word, locations from t_key_word_hits where insights_generated = 0 and document_id = 11


class Insight:
    def __init__(self, keyword_hit_id1=0, keyword1='', keyword_hit_id2=0, keyword2='', score=0.00, factor1=0, factor2=0, document_name='', document_id=0, mitigation_keyword_hit_id=0, mitigation_keyword='', locations1='', locations2='', exposure_path_id=0, internalization_id=0) -> None:
        self.mitigation_keyword_hit_id = mitigation_keyword_hit_id
        self.mitigation_keyword = mitigation_keyword
        self.keyword_hit_id1 = keyword_hit_id1
        self.keyword1 = keyword1
        self.keyword_hit_id2 = keyword_hit_id2
        self.keyword2 = keyword2
        self.factor1 = factor1
        self.factor2 = factor2
        self.score = score
        self.document_name = document_name
        self.document_id = document_id
        self.locations1 = locations1
        self.locations2 = locations2
        self.internalization_id = internalization_id
        self.exposure_path_id = exposure_path_id


class ExpIntInsight:
    def __init__(self, exp_keyword_hit_id1=0, exp_keyword1='', exp_keyword_hit_id2=0, exp_keyword2='', int_key_word_hit_id1=0, int_key_word1='', int_key_word_hit_id2=0, int_key_word2='', factor1=0, factor2=0, score=0.00, document_name='', document_id=0, internalization_id=0, exposure_path_id=0) -> None:
        self.exp_keyword_hit_id1 = exp_keyword_hit_id1
        self.exp_keyword1 = exp_keyword1
        self.exp_keyword_hit_id2 = exp_keyword_hit_id2
        self.exp_keyword2 = exp_keyword2
        self.int_key_word_hit_id1 = int_key_word_hit_id1
        self.int_key_word1 = int_key_word1
        self.int_key_word_hit_id2 = int_key_word_hit_id2
        self.int_key_word2 = int_key_word2
        self.factor1 = factor1
        self.factor2 = factor2
        self.score = score
        self.document_name = document_name
        self.document_id = document_id
        self.internalization_id = internalization_id
        self.exposure_path_id = exposure_path_id


class MitigationExpIntInsight(ExpIntInsight):

    def __init__(self, exp_keyword_hit_id1=0, exp_keyword1='', exp_keyword_hit_id2=0, exp_keyword2='', int_key_word_hit_id1=0, int_key_word1='', int_key_word_hit_id2=0, int_key_word2='', factor1=0, factor2=0, score=0, document_name='', document_id=0, internalization_id=0, exposure_path_id=0, mitigation_keyword_hit_id=0, mitigation_keyword='', exp1_locations='',exp2_locations='',int1_locations='',int2_locations='') -> None:
        super().__init__(exp_keyword_hit_id1, exp_keyword1, exp_keyword_hit_id2, exp_keyword2, int_key_word_hit_id1, int_key_word1,
                         int_key_word_hit_id2, int_key_word2, factor1, factor2, score, document_name, document_id, internalization_id, exposure_path_id)
        self.mitigation_keyword_hit_id = mitigation_keyword_hit_id
        self.mitigation_keyword = mitigation_keyword
        self.exp1_locations = exp1_locations
        self.exp2_locations = exp2_locations
        self.int1_locations = int1_locations
        self.int2_locations = int2_locations