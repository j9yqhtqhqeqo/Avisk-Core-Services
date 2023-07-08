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
from DBEntities.ProximityEntity import  ProximityEntity, KeyWordLocationsEntity, FD_Factor
from Utilities.LoggingServices import logGenerator
from DBEntities.DictionaryEntity import DictionaryEntity
from DBEntities.ProximityEntity import  Insight
from Utilities.Lookups import Lookups
import numpy as np


PARM_LOGFILE = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenLog/InsightLog')
PARM_TENK_OUTPUT_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Extracted10K/')
PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'
PARM_STAGE1_FOLDER = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage1CleanTextFiles/')
WORD_RADIUS = 25


class insights:
    def __init__(self) -> None:
        self.document_section:str
        self.document_id:str
        self.cluster_terms = dict()
        self.frequency:int

    def add_proximity_info(self,term:str, distance:int):
        self.cluster_terms.update({term:distance})



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
        self.document_list =[]
        self.errors: any
        self.log_generator = logGenerator(self.log_file_path)
        self.insightDBMgr = InsightGeneratorDBManager()


        self.big_int_location_list =[]
        
    
    def _get_company_list(self):
         pass


    def generate_keyword_location_map(self):
        
        self.proximity_entity_list=[]
        self.document_list = self.insightDBMgr.get_document_list()
        self.company_list = self._get_company_list()
        company: DocHeaderEntity
    
        for company in self.company_list:
            self.document_id = company.document_id
            self.document_name = company.document_name
            self._load_content(company.document_name, company.document_id, company.reporting_year, company.reporting_quarter)
           
            # Generate keyword location map for exposure pathway dictionary terms
            self._get_exp_dictionary_term_list()
            self._create_exp_dictionary_proximity_map()
            self._save_dictionary_keyword_search_results(Lookups().Exposure_Pathway_Dictionary_Type)

           ## Generate keyword location map for internalization pathway dictionary terms
            # self._get_int_dictionary_term_list()
            # self._create_int_dictionary_proximity_map()
            # self._save_dictionary_keyword_search_results(Lookups().Internalization_Dictionary_Type)
    
        # self.cleanup()


    def _get_exp_dictionary_term_list(self):

        # DEBUG Code 
        # self.exp_dictionary_term_list.append(DictionaryEntity(dictionary_id=1000,keywords='IT', internalization_id=1017))


        insightDBMgr = InsightGeneratorDBManager()
        self.exp_dictionary_term_list = insightDBMgr.get_exp_dictionary_term_list()

    def _create_exp_dictionary_proximity_map(self):
        self.proximity_entity_list.clear()
        total_dictionary_hits =0
        for DictionaryTermList in self.exp_dictionary_term_list:
            proximity_entity = ProximityEntity(DictionaryTermList.dictionary_id, self.document_id )
            key_word_list = DictionaryTermList.keywords
            key_words = key_word_list.split(',')
            indices:any
            word_list = self.current_data.split()
            for keyword in key_words:
               # For each keyword, identify all the word locations the key word appears in the document
               indices:any
               if keyword in('IT'):
                indices = [i+1 for i, word in enumerate(word_list) if(keyword.strip() in word.strip())]

               else:
                indices = [i+1 for i, word in enumerate(word_list) if(keyword.strip().upper() in word.strip().upper())]

                if(indices):
                    keyword_location_entity = KeyWordLocationsEntity(key_word=keyword, locations=indices, frequency=len(indices))
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

    def _get_int_dictionary_term_list(self):

        insightDBMgr = InsightGeneratorDBManager()
        self.int_dictionary_term_list = insightDBMgr.get_int_dictionary_term_list()


    def _create_int_dictionary_proximity_map(self):
        self.proximity_entity_list.clear()
        total_dictionary_hits =0
        for DictionaryTermList in self.int_dictionary_term_list:
            proximity_entity = ProximityEntity(DictionaryTermList.dictionary_id, self.document_id )
            key_word_list = DictionaryTermList.keywords
            key_words = key_word_list.split(',')
            indices:any
            word_list = self.current_data.split()
            for keyword in key_words:
               # For each keyword, identify all the word locations the key word appears in the document
                indices = [i+1 for i, word in enumerate(word_list) if(keyword.strip().upper() in word.strip().upper())]

                if(indices):
                    keyword_location_entity = KeyWordLocationsEntity(key_word=keyword, locations=indices, frequency=len(indices))
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


    def _save_dictionary_keyword_search_results(self, dictionary_type:int):
         ## Save Keyword search Results to Database
        if(self.proximity_entity_list):
            self.insightDBMgr.save_key_word_hits(self.proximity_entity_list, self.company_id,self.document_id, self.document_name, self.reporting_year, dictionary_type=dictionary_type)
   

    def _load_content(self, document_name:str, year:int,document_id=9999,  qtr=1):
        pass



    def generate_aggregate_insights_from_keyword_location_details(self):

        #Create a sorted array of all locations found for a given dictionary list
        self.big_int_location_list.clear()
        big_int_location_list =[]
        big_list = []
        keyword_location_list = self._load_keyword_location_list()
        keyword_location: KeyWordLocationsEntity
        for keyword_location in keyword_location_list:
            locations = keyword_location.locations.strip('[').strip(']').split(',')
            big_list = np.append(big_list, locations)
            # print('Current Big List Count:'+ str(len(big_list)))
        self.big_int_location_list = np.sort(np.asarray(big_list, dtype= np.int32))
        
        
        # For each keyword in the dictionary list, compute the Distance Factor as 1 * 10000 / word distance
        #Try for Supply: 1002
        for keyword_location in keyword_location_list:
            # print('Processing:'+ keyword_location.key_word)
            self._compute_FD_Factor(keyword_location)


    def _compute_FD_Factor(self,keyword_location:KeyWordLocationsEntity):
            # print('Computing Frequency Distance Factor for:'+ keyword_location.key_word)
            fd_factors_for_keyword = []

            keyword_hit_id = keyword_location.key_word_hit_id
            keyword = keyword_location.key_word
            frequency = keyword_location.frequency
            locations = keyword_location.locations.strip('[').strip(']').split(',')

            int_keyword_locations = np.asarray(locations, dtype = np.int32)
            fd_factor1 = FD_Factor(keyword_hit_id=keyword_hit_id, keyword=keyword,frequency=frequency)
            for int_keyword_location in int_keyword_locations:

                # print(int_keyword_location)
                related_word_locations = self._get_related_word_locations_in_Radius(int_keyword_location=int_keyword_location)

                # Compute the Distance Factor as 1 * 10000 / word distance
                calculated_factor = 0.00
                for related_word_location in related_word_locations:
                    distance = abs(int_keyword_location - related_word_location)
                    if(distance != 0):
                        calculated_factor = calculated_factor + (1*(1/distance))               
                fd_factor1.add_fd_factor(round(calculated_factor,2),len(related_word_locations))
            fd_factors_for_keyword.append(fd_factor1)

            # print("Frequency Distance Factors:"+str(fd_factors_for_keyword))

            fd_factor2:FD_Factor
            for fd_factor2 in fd_factors_for_keyword:
                print("Key Word:"+fd_factor2.keyword)
                print("FD Factors:"+str(fd_factor2.fd_factor))
    

    def _get_related_word_locations_in_Radius(self, int_keyword_location:int):
        radius_upper = int_keyword_location + WORD_RADIUS 
        radius_lower : int

        if(int_keyword_location - WORD_RADIUS < 0): radius_lower =0
        else: radius_lower = int_keyword_location - WORD_RADIUS 

        radius_locations = [location for location in self.big_int_location_list if location >= radius_lower and location <= radius_upper] 

        # print(radius_locations)    
        return radius_locations      

 
    def generate_insights_with_2_factors(self, batch_id = 0, dictionary_type =0):


        document_list = self.insightDBMgr.get_unprocessed_document_items_by_batch(batch_id=batch_id, dictionary_type=dictionary_type)

        document_item: KeyWordLocationsEntity
        for document_item in document_list:
            self.log_generator.log_details("Processing Batch:"+str(batch_id)+", Document ID:"+str(document_item.document_id)+", dictionary_type:"+str(dictionary_type)+", Dictionary ID:" + str(document_item.dictionary_id))
            print("Processing Batch:"+str(batch_id)+", Document ID:"+str(document_item.document_id)+", dictionary_type:"+str(dictionary_type)+", Dictionary ID:" + str(document_item.dictionary_id))
            self._generate_insights_with_2_factors_by_dictionary_id(batch_id=batch_id, dictionary_type=dictionary_type, dictionary_id=document_item.dictionary_id, document_id = document_item.document_id, document_name=document_item.document_name)


    def _generate_insights_with_2_factors_by_dictionary_id(self, batch_id=0, dictionary_type = 0, dictionary_id = 0, document_id =0, document_name=''):
        keyword_location_list = self._load_keyword_location_list(batch_id, dictionary_type, dictionary_id, document_id)
        insightList = []
        keyword_location: KeyWordLocationsEntity
        for keyword_location in keyword_location_list:
            master_locations = keyword_location.locations.strip('[').strip(']').split(',')
            int_master_locations = np.asarray(master_locations, dtype = np.int32)
            child_node: KeyWordLocationsEntity
            for child_node in keyword_location_list:
                radius_locations =[]
                factor1_frequency = 0
                factor2_distance_list = []
                factor2_average_distance =0.0
                score =0.0

                if(child_node.key_word_hit_id > keyword_location.key_word_hit_id):
                    child_locations = child_node.locations.strip('[').strip(']').split(',')
                    int_child_locations = np.asarray(child_locations, dtype = np.int32)
                    for int_master_location in int_master_locations:
                        
                        radius_location_partial = (self._get_related_word_locations_in_Radius_for_child_list(int_master_location, int_child_locations))
                        factor1_frequency = factor1_frequency + len(radius_location_partial)
                        
                        for location in radius_location_partial:
                            distance = abs(int_master_location - location)
                            ratio = distance/WORD_RADIUS
                            factor2_distance_list.append(ratio)

                    if(len(factor2_distance_list) >0):
                        factor2_average_distance = np.average(factor2_distance_list)
                        if(factor2_average_distance >0.0):
                            score = factor1_frequency *(1/factor2_average_distance)

                    if(score >0.0):
                        insight = Insight(keyword_hit_id1=keyword_location.key_word_hit_id,keyword1= keyword_location.key_word, \
                                          keyword_hit_id2=child_node.key_word_hit_id,keyword2=child_node.key_word, score=score, \
                                          factor1= factor1_frequency,factor2=factor2_average_distance, document_name=document_name, document_id=document_id)
                        insightList.append(insight)
        self.log_generator.log_details("Total Insights generated:"+ str(len(insightList)))
        self.log_generator.log_details('################################################################################################')

        insights_genetated =  len(insightList)
        print("Total Insights generated:"+ str(insights_genetated))

        if(insights_genetated >0):
            self.insightDBMgr.save_insights(insightList=insightList, dictionary_type = dictionary_type)
            self.insightDBMgr.update_insights_generated_batch(batch_id, dictionary_type=dictionary_type,dictionary_id=dictionary_id, document_id=document_id)


    def _load_keyword_location_list(self, batch_id=0, dictionary_type = 0, dictionary_id = 0, document_id = 0):
        return(self.insightDBMgr.get_keyword_location_list(batch_id, dictionary_type, dictionary_id, document_id))
    

    def _get_related_word_locations_in_Radius_for_child_list(self, int_keyword_location:int, int_child_locations:any):
        radius_upper = int_keyword_location + WORD_RADIUS 
        radius_lower : int

        if(int_keyword_location - WORD_RADIUS < 0): radius_lower =0
        else: radius_lower = int_keyword_location - WORD_RADIUS 

        radius_locations = [location for location in int_child_locations if location >= radius_lower and location <= radius_upper] 

        # print(radius_locations)    
        return radius_locations    


    def cleanup(self):
        self.insightDBMgr.dbConnection.close()


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
                doc_header_entity.document_id = self._get_document_id(file)
                company_list.append(doc_header_entity)

        return company_list

    
    def _get_document_id(self, file:str):
       document: KeyWordLocationsEntity
 
       for document in self.document_list:
            current_id = document.document_id
            if(document.document_name==file):
                return document.document_id
        # If document not configured in table  abort
       print("Document not configured in t_document table")
       raise Exception("Document not configured in t_document table")


insight_gen = file_folder_Insight_Generator(folder_path=PARM_STAGE1_FOLDER, company_name='Marathon OIL', reporting_year=2022)
insight_gen.generate_keyword_location_map()
insight_gen.generate_insights_with_2_factors(2, 1000)
insight_gen.cleanup()


