############################################################################################################
# Master Insight Generator File
# 
#
############################################################################################################
import sys
from pathlib import Path
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import datetime as dt
import re
from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager
from DBEntities.DocumentHeaderEntity import DocHeaderEntity
# from DocumentProcessor import tenKXMLProcessor
from DBEntities.ProximityEntity import  ProximityEntity, KeyWordLocationsEntity
from Utilities.LoggingServices import logGenerator
from DBEntities.DictionaryEntity import DictionaryEntity
from Utilities.Lookups import Lookups


PARM_LOGFILE = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenLog/InsightLog')
PARM_TENK_OUTPUT_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Extracted10K/')
PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'
PARM_STAGE1_FOLDER = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage1CleanTextFiles/')



class insightGenerator:
    def __init__(self) -> None:
        self.log_file_path = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'
        
        self.document_id:int
        self.document_name:str
        self.company_id:int
        self.reporting_year:int

        self.current_data:str
        self.sic_code: int
        self.company_list:any
        self.exp_dictionary_term_list =[]
        self.int_dictionary_terms =[]
        self.proximity_entity_list =[]
        self.errors: any
        self.log_generator = logGenerator(self.log_file_path)
        self.insightDBMgr = InsightGeneratorDBManager()
        
    
    def _get_company_list(self):
         pass

    def generate_insights(self):
        
        self.proximity_entity_list=[]
        self.company_list = self._get_company_list()
        company: DocHeaderEntity
    
        for company in self.company_list:
            self.document_name = company.document_name
            self._load_content(company.document_name, company.document_id, company.reporting_year, company.reporting_quarter)
            self._get_dictionary_terms()
            self._get_parsed_content()
            self._create_proximity_map()
            self._save_keyword_search_results(Lookups().Exposure_Pathway_Dictionary_Type)
    
        self.cleanup()
    
    def cleanup(self):
        self.insightDBMgr.dbConnection.close()


    def _get_dictionary_terms(self):

        # # DEBUG CODE
        # self.exp_dictionary_term_list.append(DictionaryEntity(dictionary_id=0, keywords='cost'))
        # return

        insightDBMgr = InsightGeneratorDBManager()
        self.exp_dictionary_term_list = insightDBMgr.get_int_dictionary_term_list()

    def _create_proximity_map(self):
        self.proximity_entity_list.clear()
        total_dictionary_hits =0
        for DictionaryTermList in self.exp_dictionary_term_list:
            proximity_entity = ProximityEntity(DictionaryTermList.dictionary_id, self.document_id )
            key_word_list = DictionaryTermList.keywords
            key_words = key_word_list.split(',')
            indices:any
            for keyword in key_words:
                indices = [i+1 for i, word in enumerate(self.current_data.split()) if word.strip().upper() == keyword.strip().upper()]     
                if(indices):
                    keyword_location_entity = KeyWordLocationsEntity(key_word=keyword, locations=indices, frequency=len(indices))
                    proximity_entity.key_word_bunch.append(keyword_location_entity)
                    location_str=''
                    total_dictionary_hits = total_dictionary_hits + 1
                #Perform Plural search if plural term was not included
                try:
                    index =  key_words.index((keyword+'s').strip())
                    if(index):
                        pass            
                except:
                        indices = [i+1 for i, word in enumerate(self.current_data.split()) if word.strip().upper() == (keyword+'s').strip().upper()]
                        if(indices):
                            keyword_location_entity = KeyWordLocationsEntity(key_word=keyword+'s', locations=indices, frequency=len(indices))
                            proximity_entity.key_word_bunch.append(keyword_location_entity)
                            location_str=''
                            total_dictionary_hits = total_dictionary_hits + 1

            
            self.proximity_entity_list.append(proximity_entity)
        self.log_generator.log_details('################################################################################################')
        self.log_generator.log_details("Current Document:" +self.document_name)
        self.log_generator.log_details("Total keywords found:"+ str(total_dictionary_hits))
        print('################################################################################################')
        print("Current Document:" +self.document_name)
        print("Total key words found:"+ str(total_dictionary_hits))


    def _get_parsed_content(self):
        pass

    def _load_content(self, document_name:str, year:int,document_id=9999,  qtr=1):
        pass

    def _save_keyword_search_results(self, dictionary_type:int):
         ## Save Keyword search Results to Database
        if(self.proximity_entity_list):
            self.insightDBMgr.save_key_word_hits(self.proximity_entity_list, self.company_id, self.document_name, self.reporting_year, dictionary_type=dictionary_type)
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


class db_Insight_Generator(insightGenerator):
    def __init__(self) -> None:
        super().__init__()
    
    def _load_content(self, document_name:str, document_id:int, year:int, qtr:int):
    
        self.document_id = document_id
        document_name = document_name.replace('.txt','.xml')
        
        f_input_file_path = f'{PARM_TENK_OUTPUT_PATH}Year{year}Q{qtr}/{document_name}'

        with open(f_input_file_path, 'r') as fin:
            self.current_data = fin.read()

    def _get_company_list(self):
        insightDBMgr = InsightGeneratorDBManager()
        self.company_list = insightDBMgr.get_company_list(sic_code="Mining")
        return self.company_list


class file_folder_Insight_Generator(insightGenerator):
    def __init__(self, folder_path:str, company_name:str, reporting_year:int) -> None:
        super().__init__()
        self.folder_path = folder_path
        self.reporting_year = reporting_year
        self.company_name = company_name

    
    def _load_content(self, document_name:str, document_id:int, year:int, qtr:int):
    
        self.document_id = document_id
        self.document_name = document_name
        
        f_input_file_path = f'{self.folder_path}/{self.company_name}/{self.reporting_year}/{document_name}'

        with open(f_input_file_path, 'r') as fin:
            self.current_data = fin.read()

    def _get_company_list(self):
        company_list = []
        insightDBMgr = InsightGeneratorDBManager()
        self.company_id = insightDBMgr.get_company_id_by_Name(company_name=self.company_name, reporting_year=self.reporting_year)

        fully_qualified_path = f'{self.folder_path}/{self.company_name}/{self.reporting_year}'
        file_list = sorted(os.listdir(fully_qualified_path))

        for file in file_list:
            if (file =='.DS_Store'):
                pass
            else:
                doc_header_entity = DocHeaderEntity()
                doc_header_entity.company_id = self.company_id
                doc_header_entity.document_name = file
                doc_header_entity.reporting_year = self.reporting_year
                company_list.append(doc_header_entity)
        return company_list



insight_gen = file_folder_Insight_Generator(folder_path=PARM_STAGE1_FOLDER, company_name='Marathon OIL', reporting_year=2022)
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

