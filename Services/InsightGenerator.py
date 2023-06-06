############################################################################################################
# Master Insight Generator File
# 
#
############################################################################################################
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import datetime as dt
import re
from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager
from DBEntities.DocumentHeaderEntity import DocHeaderEntity
# from DocumentProcessor import tenKXMLProcessor
from DBEntities.ProximityEntity import  ProximityEntity, Key_word_locations

PARM_LOGFILE = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenerator')
PARM_TENK_OUTPUT_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Extracted10K/')
PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'


class insightGenerator:
    def __init__(self) -> None:
        self.log_file_path = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'
        

        self.current_data:str
        self.sic_code: int
        self.company_list:any
        self.exp_dictionary_term_list =[]
        self.int_dictionary_terms =[]
        self.insightList = []

        self.errors: any
        
    
    def _get_company_list(self):
        insightDBMgr = InsightGeneratorDBManager()
        self.company_list = insightDBMgr.get_company_list(sic_code="Mining")
        return self.company_list

    def generate_insights(self):
        self.company_list = self._get_company_list()

        company: DocHeaderEntity
    
        for company in self.company_list:
            self._load_content(company.document_name, company.reporting_year, company.reporting_quarter)
            self._get_dictionary_terms()
            self._get_parsed_content()
            self._create_proximity_map()
            self._save_insights()
    
    def _get_dictionary_terms(self):
        insightDBMgr = InsightGeneratorDBManager()
        self.exp_dictionary_term_list = insightDBMgr.get_exp_dictionary_term_list()
        # self.int_dictionary_terms = insightDBMgr.int_dictionary_terms()
        # return self.company_list
        

    def _create_proximity_map(self):
        
        for DictionaryTermList in self.exp_dictionary_term_list: 
           key_word_list = DictionaryTermList.keywords
           key_words = key_word_list.split(',')
           indices:any
           for keyword in key_words:
               indices = [i+1 for i, word in enumerate(self.current_data.split()) if word == keyword]
               print('Key Word:' + keyword)
               for i in indices:
                    print('Word Location:' + str(i ))
            # search_Exp = re.compile(keyword,re.IGNORECASE)
            # for search_iter in re.finditer(keyword,self.current_data):
            #       print(search_iter.group() + ' ' + str(search_iter.start()))
            # for m in re.finditer(pattern, s):
            # print m.group(2), '*', m.group(1)


    def _get_parsed_content(self):
        pass

    def _load_content(self, document_name:str, year:int, qtr:int):

        document_name = document_name.replace('.txt','.xml')

        f_input_file_path = f'{PARM_TENK_OUTPUT_PATH}Year{year}Q{qtr}/{document_name}'

        with open(f_input_file_path, 'r') as fin:
            self.current_data = fin.read()


    def _save_insights(self):
        pass

    def remove_insights(self):
        pass


class insights:
    def __init__(self) -> None:
        self.document_section:str
        self.document_id:str
        self.cluster_terms = dict()
        self.frequency:int

    def add_proximity_info(self,term:str, distance:int):
        self.cluster_terms.update({term:distance})


class tenK_Insight_Generator(insightGenerator):
    def __init__(self) -> None:
        super().__init__()


insight_gen = insightGenerator()
insight_gen.generate_insights()
# company_list = insight_gen._get_company_list()
# l_company: DocHeaderEntity

# for company in company_list:
#     print(str(company.document_id )+ '  ' + str(company.document_name))
    
#     # l_company.document_id = company.document_id
#     # l_company.document_name = company.document_name
#     # l_company.reporting_year = company.reporting_year
#     # l_company.reporting_quarter = company.reporting_quarter
#     # l_company.conformed_name = company.conformed_name
#     # l_company.sic_code = company.sic_code
#     # l_company.form_type = company.form_type

   

# insights = insights()

# insights.add_proximity_info("water", 5)
# insights.add_proximity_info("drauhgt", 8)
# insights.add_proximity_info("fire", 6)
# insights.add_proximity_info("rain", 9)

# print(insights.cluster_terms)

