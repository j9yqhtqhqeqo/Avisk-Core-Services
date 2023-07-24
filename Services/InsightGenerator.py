############################################################################################################
# Master Insight Generator File
# To Process New set of files:
#  1. Add textfiles to PARM_STAGE1_FOLDER
#  2. Create entry in table t_document and set document_processed_ind = 0 
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
from Utilities.Lookups import ContextResolver
import numpy as np
import copy

PARM_LOGFILE = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenLog/InsightLog')
PARM_TENK_OUTPUT_PATH = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Extracted10K/')
PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'
PARM_STAGE1_FOLDER = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage1CleanTextFiles/')
WORD_RADIUS = 25


# class insights:
#     def __init__(self) -> None:
#         self.document_section:str
#         self.document_id:str
#         self.cluster_terms = dict()
#         self.frequency:int

#     def add_proximity_info(self,term:str, distance:int):
#         self.cluster_terms.update({term:distance})


class keyWordSearchManager:

    def __init__(self) -> None:
        self.log_file_path = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'
        
        self.document_id:int
        self.document_name:str
        self.company_id:int
        self.reporting_year:int

        self.current_data:str

        self.sic_code: int
        self.company_list:any
        self.document_list =[]

        self.exp_dictionary_term_list =[]
        self.int_dictionary_term_list =[]
        self.int_dictionary_terms =[]
        self.mitigation_dictionary_term_list = []

        self.proximity_entity_list =[]

       
        self.errors: any
        self.log_generator = logGenerator(self.log_file_path)
        self.insightDBMgr = InsightGeneratorDBManager()


        self.big_int_location_list =[]
        

    def _get_company_list(self):
         pass

    def _load_content(self, document_name:str, year:int,document_id=9999,  qtr=1):
        pass

## Search all exposure pathway dictionary terms in the document and save locations 

    def generate_keyword_location_map_for_exposure_pathway(self):
        
        self.proximity_entity_list=[]
        self.document_list = self.insightDBMgr.get_exp_pathway_document_list()
        if(len(self.document_list) == 0):
            print("All documents processed: No new documents to process - Exiting generate_keyword_location_map")
            return


        for document in self.document_list:
            self.document_id = document.document_id
            self.document_name = document.document_name
            self.company_id = document.company_id
            self.reporting_year = document.year
            self._load_content(document.document_name, document.document_id, document.year)
           
            # Generate keyword location map for exposure pathway dictionary terms
            print("Generating keyword location map for exposure pathway dictionary terms ")

            self._get_exp_dictionary_term_list()
            self._create_exp_dictionary_proximity_map()
            if not self.is_related_keywords_need_to_be_addressed:
                self._save_dictionary_keyword_search_results(Lookups().Exposure_Pathway_Dictionary_Type)
                self.insightDBMgr.update_exp_pathway_keyword_search_completed_ind(self.document_id)
            else:
                print("Key word search not saved as Related Keywords need to be addressed: Please review the Logfile / Output")
    
    def _get_exp_dictionary_term_list(self):

        # DEBUG Code 
        # self.exp_dictionary_term_list.append(DictionaryEntity(dictionary_id=1000,keywords='floods', exposure_pathway_id=10102))


        insightDBMgr = InsightGeneratorDBManager()
        self.exp_dictionary_term_list = insightDBMgr.get_exp_dictionary_term_list()

    def _create_exp_dictionary_proximity_map(self):
        print('################################################################################################')
        print("Current Document:" +self.document_name)

        self.is_related_keywords_need_to_be_addressed = False

        self.proximity_entity_list.clear()
        total_dictionary_hits =0
        for DictionaryTermList in self.exp_dictionary_term_list:
            proximity_entity = ProximityEntity(DictionaryTermList.dictionary_id, self.document_id )
            key_word_list = DictionaryTermList.keywords
            
            key_words_natural = key_word_list.split(',')
            key_words =[]
            for keyword in key_words_natural:
                key_words.append(keyword.upper())
            
            key_words = sorted(key_words)

            indices:any
            word_list = self.current_data.split()
            for keyword in key_words:
             
                indices:any

                #Find Exact Match
                if keyword in('IT'):
                    indices = [i+1 for i, word in enumerate(word_list) if(keyword.strip() == word.replace('.','').replace(',','').replace(')','').replace(';','').replace(':','').strip())]

                else:
                    indices = [i+1 for i, word in enumerate(word_list) if(keyword.strip() == word.replace('.','').replace(',','').replace(')','').replace(';','').replace(':','').strip().upper())]

                if(indices):
                    # keyword_location_entity = KeyWordLocationsEntity(key_word=keyword, locations=indices, frequency=len(indices))
                    keyword_location_entity = KeyWordLocationsEntity(key_word=keyword, locations=indices, frequency=len(indices), dictionary_id=DictionaryTermList.dictionary_id, dictionary_type=Lookups().Exposure_Pathway_Dictionary_Type)

                    proximity_entity.key_word_bunch.append(keyword_location_entity)
                    location_str=''
                    total_dictionary_hits = total_dictionary_hits + 1
            
            proximity_entity =  self.combine_singular_plural_words(proximity_entity)

            self.proximity_entity_list.append(proximity_entity)
        self.log_generator.log_details('################################################################################################')
        self.log_generator.log_details("Current Document:" +self.document_name)
        self.log_generator.log_details("Total keywords found:"+ str(total_dictionary_hits))

        print("Total key words found:"+ str(total_dictionary_hits))



## Search all internalization pathway dictionary terms in the document and save locations 

    def generate_keyword_location_map_for_internalization(self):
        
        self.proximity_entity_list=[]
        self.document_list = self.insightDBMgr.get_internalization_document_list()
        if(len(self.document_list) == 0):
            print("All documents processed: No new documents to process - Exiting generate_keyword_location_map")
            return


        for document in self.document_list:
            self.document_id = document.document_id
            self.document_name = document.document_name
            self.company_id = document.company_id
            self.reporting_year = document.year

            self._load_content(document.document_name, document.document_id, document.year)
                      
           # Generate keyword location map for internalization pathway dictionary terms
            print('Generating keyword location map for internalization pathway dictionary terms')
            self._get_int_dictionary_term_list()
            self._create_int_dictionary_proximity_map()
            if not self.is_related_keywords_need_to_be_addressed:
                self._save_dictionary_keyword_search_results(Lookups().Internalization_Dictionary_Type)
                self.insightDBMgr.update_internalization_keyword_search_completed_ind(self.document_id)
            else:
                print("Key word search not saved as Related Keywords need to be addressed: Please review the Logfile/Output")

    def _get_int_dictionary_term_list(self):
        #DEBUG Code 
        # self.int_dictionary_term_list.append(DictionaryEntity(dictionary_id=1001,keywords='materials', exposure_pathway_id=10102))

        insightDBMgr = InsightGeneratorDBManager()
        self.int_dictionary_term_list = insightDBMgr.get_int_dictionary_term_list()

    def _create_int_dictionary_proximity_map(self):
        print('################################################################################################')
        print("Current Document:" +self.document_name)

        self.is_related_keywords_need_to_be_addressed = False

        self.proximity_entity_list.clear()
        total_dictionary_hits =0
        for DictionaryTermList in self.int_dictionary_term_list:
            proximity_entity = ProximityEntity(DictionaryTermList.dictionary_id, self.document_id )
            key_word_list = DictionaryTermList.keywords
           
            key_words_natural = key_word_list.split(',')
            key_words =[]
            for keyword in key_words_natural:
                key_words.append(keyword.upper())
            
            key_words = sorted(key_words)

            indices:any
            word_list = self.current_data.split()

            for keyword in key_words:
             
                indices:any

                #Find Exact Match
                if keyword in('IT'):
                    indices = [i+1 for i, word in enumerate(word_list) if(keyword.strip() == word.replace('.','').replace(',','').replace(')','').replace(';','').replace(':','').strip())]

                else:
                    indices = [i+1 for i, word in enumerate(word_list) if(keyword.strip() == word.replace('.','').replace(',','').replace(')','').replace(';','').replace(':','').strip().upper())]

                # if(indices):
                     # Find Partial Hits - corruption in 'anti-corruption' and add to database for disposal               
               #########################################
                keyword_cleaned = keyword.strip().upper()
                related_keyword_list=[]
                for word in word_list:
                    word_cleaned = word.replace('.','').replace(',','').replace(')','').replace(';','').replace(':','').strip().upper()
                    if(keyword_cleaned in word_cleaned and keyword_cleaned!= word_cleaned):
                        if(word_cleaned not in related_keyword_list and word_cleaned.upper() not in key_words):
                            # print("OROGINAL WORD:"+word)
                            related_keyword_list.append(word_cleaned)
                
                contextResolver = ContextResolver()
              
                if(len(related_keyword_list) >0 ):
                    for related_keyword in related_keyword_list:
                        if not contextResolver.is_keyword_in_exclusion_list(keyword,related_keyword):
                            if contextResolver.is_keyword_in_inclusion_list(keyword, related_keyword):
                                related_word_indices = [i+1 for i, word in enumerate(word_list) if(related_keyword.strip() == word.replace('.','').replace(',','').replace(')','').replace(';','').replace(':','').replace('’','').strip().upper())]
                                for i in related_word_indices: indices.append(i)
                            else:
                                print('Add \''+ keyword+ '\''+': [\''+related_keyword+'\']' + ' to ContextResolver - Inclusion OR Exclusion for Dictionary ID: '+ str(DictionaryTermList.dictionary_id))    
                                self.log_generator.log_details('Add \''+ keyword+ '\''+': [\''+related_keyword+'\']' + ' to ContextResolver - Inclusion OR Exclusion')
                                self.is_related_keywords_need_to_be_addressed = True
                                # raise Exception('keyword:' +keyword+', related word:'+  related_keyword + 'is not in either Inclusion OR exclusion list' )
                ###############################################


                keyword_location_entity = KeyWordLocationsEntity(key_word=keyword, locations=indices, frequency=len(indices), dictionary_id=DictionaryTermList.dictionary_id, dictionary_type=Lookups().Exposure_Pathway_Dictionary_Type)

                if(keyword_location_entity.frequency >0):  
                    proximity_entity.key_word_bunch.append(keyword_location_entity)
                    total_dictionary_hits = total_dictionary_hits + 1
            
            proximity_entity =  self.combine_singular_plural_words(proximity_entity)

            self.proximity_entity_list.append(proximity_entity)
        self.log_generator.log_details('################################################################################################')
        self.log_generator.log_details("Current Document:" +self.document_name)
        self.log_generator.log_details("Total keywords found:"+ str(total_dictionary_hits))

        print("Total key words found:"+ str(total_dictionary_hits))
        return self.is_related_keywords_need_to_be_addressed



    def combine_singular_plural_words(self, proximity_entity: ProximityEntity):
            combined_entity = ProximityEntity()
            child_entity = copy.deepcopy(proximity_entity)
            for master_item in proximity_entity.key_word_bunch:
                for child_item in child_entity.key_word_bunch:

                    if(master_item.key_word != child_item.key_word and master_item.key_word in child_item.key_word): 
                       temp_item = copy.deepcopy(master_item)
                       temp_item.key_word = child_item.key_word
                       temp_item.temp_place_holder = master_item.key_word
                       for location in child_item.locations:
                           if location not in master_item.locations:
                               temp_item.locations.append(location)

                       temp_item.dictionary_id = master_item.dictionary_id
                       temp_item.frequency = len(temp_item.locations)
                    #    print('Master Item: '+master_item.key_word+", Locations: "+str(master_item.locations))
                    #    print('Child Item: '+child_item.key_word+", Locations: "+str(child_item.locations))
                    #    print('Combined Word:'+temp_item.key_word+', Locations:'+str(temp_item.locations))

                       combined_entity.dictionary_id = proximity_entity.dictionary_id
                       combined_entity.doc_header_id = proximity_entity.doc_header_id
                       combined_entity.key_word_bunch.append(temp_item)

            # print("Singular/Plural keywords merged:" + str(len(combined_entity.key_word_bunch)))
            for master_item in proximity_entity.key_word_bunch:
                found = False
                for child_item in combined_entity.key_word_bunch:
                    if(master_item.key_word not in child_item.key_word):
                        found = False
                    else:
                        found = True
                        break
                if(not found):
                    temp_item = copy.deepcopy(master_item)
                    combined_entity.dictionary_id = proximity_entity.dictionary_id
                    combined_entity.doc_header_id = proximity_entity.doc_header_id
                    combined_entity.key_word_bunch.append(temp_item)

            index = 0    
            for child_item in combined_entity.key_word_bunch:
                if(combined_entity.key_word_bunch[index].temp_place_holder !=''):
                    combined_entity.key_word_bunch[index].key_word = combined_entity.key_word_bunch[index].temp_place_holder

            return combined_entity

## Search all mitigation dictionary terms in the document and save locations 

    def generate_keyword_location_map_for_mitigation(self):
        
        self.proximity_entity_list=[]
        self.document_list = self.insightDBMgr.get_mitigation_document_list()
        if(len(self.document_list) == 0):
            print("All documents processed: No new documents to process - Exiting generate_keyword_location_map")
            return


        for document in self.document_list:
            self.document_id = document.document_id
            self.document_name = document.document_name
            self.company_id = document.company_id
            self.reporting_year = document.year

            self._load_content(document.document_name, document.document_id, document.year)
                      
           # Generate keyword location map for internalization pathway dictionary terms
            print('Generating keyword location map for mitigation dictionary terms')
            self._get_mitigation_dictionary_term_list()
            self._create_mitigation_dictionary_proximity_map()
            self._save_dictionary_keyword_search_results(Lookups().Mitigation_Dictionary_Type)
            self.insightDBMgr.update_mitigation_keyword_search_completed_ind(self.document_id)

    def _get_mitigation_dictionary_term_list(self):

        insightDBMgr = InsightGeneratorDBManager()
        self.mitigation_dictionary_term_list = insightDBMgr.get_mitigation_dictionary_term_list()

    def _create_mitigation_dictionary_proximity_map(self):
        self.proximity_entity_list.clear()
        total_dictionary_hits =0
        for DictionaryTermList in self.mitigation_dictionary_term_list:
            proximity_entity = ProximityEntity(DictionaryTermList.dictionary_id, self.document_id )
            key_word_list = DictionaryTermList.keywords
            key_words = key_word_list.split(',')
            indices:any
            word_list = self.current_data.split()
            for keyword in key_words:
               # For each keyword, identify all the word locations the key word appears in the document
                indices = [i+1 for i, word in enumerate(word_list) if(keyword.strip().upper() in word.strip().upper())]

                if(indices):
                    keyword_location_entity = KeyWordLocationsEntity(key_word=keyword, locations=indices, frequency=len(indices), dictionary_id=DictionaryTermList.dictionary_id, dictionary_type=Lookups().Mitigation_Dictionary_Type)
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
   

    def cleanup(self):
        self.insightDBMgr.dbConnection.close()


class db_Insight_keyWordSearchManager(keyWordSearchManager):
    def __init__(self) -> None:
        super().__init__()
    
    def _load_content(self, document_name:str, document_id:int, year:int, qtr:int):
    
        self.document_id = document_id
        document_name = document_name.replace('.txt','.xml')
        
        f_input_file_path = f'{PARM_TENK_OUTPUT_PATH}Year{year}Q{qtr}/{document_name}'

        with open(f_input_file_path, 'r') as fin:
            self.current_data = fin.read()


class file_folder_keyWordSearchManager(keyWordSearchManager):
    def __init__(self, folder_path:str) -> None:
        super().__init__()
        self.folder_path = folder_path

    def _load_content(self, document_name:str, document_id:int, year:int):
    
        self.document_id = document_id
        self.document_name = document_name
        
        f_input_file_path = f'{self.folder_path}/{year}/{document_name}'

        with open(f_input_file_path, 'r') as fin:
            self.current_data = fin.read()

    
    def _get_document_id(self, file:str):
       document: KeyWordLocationsEntity
 
       for document in self.document_list:
            current_id = document.document_id
            if(document.document_name==file):
                return document.document_id
        # If document not configured in table  abort
       print("Document not configured in t_document table")
       raise Exception("Document not configured in t_document table")


class int_Exp_Insight_Generator(keyWordSearchManager):

# Generate Insights for two keyword combinations
    def generate_insights_with_2_factors(self,dictionary_type:int):

        batch_id:int

        document_list = self.insightDBMgr.get_unprocessed_document_items(dictionary_type=dictionary_type)

        document_item: KeyWordLocationsEntity
        for document_item in document_list:

            self.log_generator.log_details("Processing Batch:"+str(document_item.batch_id)+", Document ID:"+str(document_item.document_id)+", dictionary_type:"+str(document_item.dictionary_type)+", Dictionary ID:" + str(document_item.dictionary_id))
            print("Processing Batch:"+str(document_item.batch_id)+", Document ID:"+str(document_item.document_id)+", dictionary_type:"+str(document_item.dictionary_type)+", Dictionary ID:" + str(document_item.dictionary_id))
            self._generate_insights_with_2_factors_by_dictionary_id(batch_id=document_item.batch_id, dictionary_type=document_item.dictionary_type, dictionary_id=document_item.dictionary_id, document_id = document_item.document_id, document_name=document_item.document_name)


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
                            try:
                                if(distance == 0):
                                   print("Distance 0 - Ignoring Weight Calculation: Keyword:" + keyword_location.key_word +", Child Key word:" + child_node.key_word+", Location:"+str(location))
                                else:
                                    ratio = 1/distance
                                    factor2_distance_list.append(ratio)
                            except Exception as exc:
                                # Rollback the transaction if any error occurs
                                print(f"Error: {str(exc)}")
                                print("Error Processing Key Word:" + keyword_location.key_word)
                                raise exc
                            #ratio = distance/WORD_RADIUS

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



# Generate Aggregate Insights
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

    def _get_related_word_locations_in_Radius(self, int_keyword_location:int):
        radius_upper = int_keyword_location + WORD_RADIUS 
        radius_lower : int

        if(int_keyword_location - WORD_RADIUS < 0): radius_lower =0
        else: radius_lower = int_keyword_location - WORD_RADIUS 

        radius_locations = [location for location in self.big_int_location_list if location >= radius_lower and location <= radius_upper] 

        # print(radius_locations)    
        return radius_locations      
   
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


class mitigation_Insight_Generator(keyWordSearchManager):
    

    def generate_mitigation_exp_insights(self):
        
        document_list = self.insightDBMgr.get_mitigation_exp_document_list()

        document_item: KeyWordLocationsEntity
        for document_item in document_list:
            self.log_generator.log_details("Document ID:"+str(document_item.document_id)+", Document Name:"+str(document_item.document_name))
            print("Document ID:"+str(document_item.document_id)+", Document Name:"+str(document_item.document_name))

            self.mitigation_keyword_location_list, self.exp_keyword_location_list, self.exp_insight_list = self.insightDBMgr.get_exp_mitigation_lists(document_item.document_id)
            print("Mitigation key word locations:"+str(len(self.mitigation_keyword_location_list))+", Exp key word locations:"+str(len(self.exp_keyword_location_list))+", insights:"+str(len(self.exp_insight_list))) 
            exp_insight_entity: Insight
            self.mitigation_comon_insightList =[]
            for exp_insight_entity in self.exp_insight_list:
                #Get combined location list for each insight word combo
                doc_location_list = self._get_combined_insight_exp_keyword_location_list(exp_insight_entity.keyword_hit_id1, exp_insight_entity.keyword_hit_id2)
                #compute score against each mitigation key word
                for mitigation_keyword_locations in self.mitigation_keyword_location_list:
                    self._create_mitigation_insights_for_document(mitigation_keyword_locations,doc_location_list,document_item.document_id, document_item.document_name,exp_insight_entity,mitigation_keyword_locations.key_word, mitigation_keyword_locations.key_word_hit_id)
            
            self.log_generator.log_details("Dcoument:"+document_item.document_name+", Total Mitigation Insights generated:"+ str(len(self.mitigation_comon_insightList)))

            print("Dcoument:"+document_item.document_name+", Total Mitigation Insights generated:"+ str(len(self.mitigation_comon_insightList)))

            self.insightDBMgr.save_insights(insightList=self.mitigation_comon_insightList, dictionary_type = Lookups().Mitigation_Exp_Insight_Type)

            self.insightDBMgr.update_mitigation_insights_generated_batch(dictionary_type=Lookups().Exposure_Pathway_Dictionary_Type, document_id=document_item.document_id)

    def generate_mitigation_int_insights(self):
        self.log_generator.log_details("Generating Mitigation Insights for Internalization Pathways")
        print("Generating Mitigation Insights for Internalization Pathways")

        document_list = self.insightDBMgr.get_mitigation_int_document_list()

        document_item: KeyWordLocationsEntity
        for document_item in document_list:
            self.log_generator.log_details("Document ID:"+str(document_item.document_id)+", Document Name:"+str(document_item.document_name))
            print("Document ID:"+str(document_item.document_id)+", Document Name:"+str(document_item.document_name))

            self.mitigation_keyword_location_list, self.int_keyword_location_list, self.int_insight_list = self.insightDBMgr.get_int_mitigation_lists(document_item.document_id)
            print("Mitigation key word locations:"+str(len(self.mitigation_keyword_location_list))+", Int key word locations:"+str(len(self.int_keyword_location_list))+", insights:"+str(len(self.int_insight_list))) 
            int_insight_entity: Insight
            self.mitigation_comon_insightList =[]
            for int_insight_entity in self.int_insight_list:
                #Get combined location list for each insight word combo
                doc_location_list = self._get_combined_insight_int_keyword_location_list(int_insight_entity.keyword_hit_id1, int_insight_entity.keyword_hit_id2)
                #compute score against each mitigation key word
                for mitigation_keyword_locations in self.mitigation_keyword_location_list:
                    self._create_mitigation_insights_for_document(mitigation_keyword_locations,doc_location_list,document_item.document_id, document_item.document_name,int_insight_entity,mitigation_keyword_locations.key_word, mitigation_keyword_locations.key_word_hit_id)
            
            self.log_generator.log_details("Dcoument:"+document_item.document_name+", Total Mitigation Insights generated:"+ str(len(self.mitigation_comon_insightList)))

            print("Dcoument:"+document_item.document_name+", Total Mitigation Insights generated:"+ str(len(self.mitigation_comon_insightList)))

            self.insightDBMgr.save_insights(insightList=self.mitigation_comon_insightList, dictionary_type = Lookups().Mitigation_Int_Insight_Type)

            self.insightDBMgr.update_mitigation_insights_generated_batch(dictionary_type=Lookups().Internalization_Dictionary_Type, document_id=document_item.document_id)

    def _create_mitigation_insights_for_document(self, mitigation_keyword_locations:None,doc_location_list:None,document_id =0, document_name='', insight_entity=None,   mitigation_keyword ='', mitigation_keyword_hit_id=0 ):

        mitigation_keyword_locations = mitigation_keyword_locations.locations.strip('[').strip(']').split(',')
        int_mitigation_keyword_locations = np.asarray(mitigation_keyword_locations, dtype = np.int32)

        doc_location_list = doc_location_list.strip('[').strip(']').split(',')
        int_doc_location_list = np.asarray(doc_location_list, dtype = np.int32)

        distance_list =np.array([])
        for int_mitigation_keyword_location in int_mitigation_keyword_locations:
            distance_list =  np.append(distance_list,self._get_distance_list_for_locations_in_Radius(int_mitigation_keyword_location, int_doc_location_list))

        factor1_frequency = 0
        factor2_distance_list = []
        factor2_average_distance =0.0
        score =0.0
        
        factor1_frequency = factor1_frequency + len(distance_list)
            
        for distance in distance_list:
            try:
                ratio = 1/distance
                factor2_distance_list.append(ratio)
            except Exception as exc:
                # Rollback the transaction if any error occurs
                print(f"Error: {str(exc)}")
                print("Error Processing Key Word:" + mitigation_keyword)
                raise exc

        if(len(factor2_distance_list) >0):
            factor2_average_distance = np.average(factor2_distance_list)
            if(factor2_average_distance >0.0):
                score = factor1_frequency *(1/factor2_average_distance)

        if(score >0.0):
            insight = Insight(mitigation_keyword_hit_id=mitigation_keyword_hit_id, mitigation_keyword= mitigation_keyword,\
                                keyword_hit_id1=insight_entity.keyword_hit_id1,keyword1= insight_entity.keyword1, \
                                keyword_hit_id2=insight_entity.keyword_hit_id2,keyword2=insight_entity.keyword2, score=score, \
                                factor1= factor1_frequency,factor2=factor2_average_distance, document_name=document_name, document_id=document_id
                            )
            self.mitigation_comon_insightList.append(insight)
            self.log_generator.log_details("Mitigation:"+mitigation_keyword+", Keywords:"+insight_entity.keyword1+' ,'+insight_entity.keyword2 +" ,Score"+str(score))
            # print("Mitigation:"+mitigation_keyword+",Exp Keywords:"+exp_insight_entity.keyword1+' ,'+exp_insight_entity.keyword2, +" , Score"+score)


    def _get_distance_list_for_locations_in_Radius(self, int_keyword_location:int, int_child_locations:any):
        radius_upper = int_keyword_location + WORD_RADIUS 
        radius_lower : int

        if(int_keyword_location - WORD_RADIUS < 0): radius_lower =0
        else: radius_lower = int_keyword_location - WORD_RADIUS 

        radius_locations = [location for location in int_child_locations if location >= radius_lower and location <= radius_upper] 

        distance_list = [abs(int_keyword_location - location) for location in radius_locations]

        # print(radius_locations)    
        return distance_list          

    def _get_combined_insight_exp_keyword_location_list(self,keyword_hit_id1: int, keyword_hit_id2:int):
        location_list1:str
        location_list2:str
        keyword_location: KeyWordLocationsEntity
        for keyword_location in self.exp_keyword_location_list:
            if(keyword_location.key_word_hit_id == keyword_hit_id1 ):
                location_list1 = (keyword_location.locations).strip('[').strip(']')
            if(keyword_location.key_word_hit_id == keyword_hit_id2 ):
                location_list2 = (keyword_location.locations).strip('[').strip(']')
        combined_location_list = location_list1+','+location_list2
       # print('Combined Locations for '+str(keyword_hit_id1) + ','+ str(keyword_hit_id2)+': ' +combined_location_list)
        return (combined_location_list)
    
    def _get_combined_insight_int_keyword_location_list(self,keyword_hit_id1: int, keyword_hit_id2:int):
        location_list1:str
        location_list2:str
        keyword_location: KeyWordLocationsEntity
        for keyword_location in self.int_keyword_location_list:
            if(keyword_location.key_word_hit_id == keyword_hit_id1 ):
                location_list1 = (keyword_location.locations).strip('[').strip(']')
            if(keyword_location.key_word_hit_id == keyword_hit_id2 ):
                location_list2 = (keyword_location.locations).strip('[').strip(']')
        combined_location_list = location_list1+','+location_list2
       # print('Combined Locations for '+str(keyword_hit_id1) + ','+ str(keyword_hit_id2)+': ' +combined_location_list)
        return (combined_location_list)



insight_gen = file_folder_keyWordSearchManager(folder_path=PARM_STAGE1_FOLDER)

# insight_gen.generate_keyword_location_map_for_exposure_pathway()
# # print("Generating Insights for Exposure Pathway Dictionary Terms")
# insight_gen.generate_insights_with_2_factors(Lookups().Exposure_Pathway_Dictionary_Type)

insight_gen.generate_keyword_location_map_for_internalization()
# print("Generating Insights for Internalization Dictionary Terms")
#insight_gen.generate_insights_with_2_factors(Lookups().Internalization_Dictionary_Type)

# insight_gen.generate_keyword_location_map_for_mitigation()
# print("Generating Insights for Mitigation Dictionary Terms")
# insight_gen.generate_insights_with_2_factors(Lookups().Mitigation_Dictionary_Type)

# mitigation_insight_gen = mitigation_Insight_Generator()
# # mitigation_insight_gen.generate_mitigation_exp_insights()
# mitigation_insight_gen.generate_mitigation_int_insights()


# mitigation_insight_gen.cleanup()


