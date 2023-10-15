############################################################################################################
# Master Insight Generator File
# To Process New set of files:
#  1. Add textfiles to PARM_STAGE1_FOLDER
#  2. Create entry in table t_document and set document_processed_ind = 0
############################################################################################################
import numpy as np
import copy
from Dictionary.DictionaryManager import ContextResolver
from Dictionary.DictionaryManager import DictionaryManager
from Utilities.Lookups import Lookups
from DBEntities.ProximityEntity import Insight
from DBEntities.ProximityEntity import ExpIntInsight
from DBEntities.ProximityEntity import MitigationExpIntInsight
from DBEntities.DictionaryEntity import DictionaryEntity
from Utilities.LoggingServices import logGenerator
from DBEntities.ProximityEntity import ProximityEntity, KeyWordLocationsEntity, FD_Factor
from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager
from DBEntities.DocumentHeaderEntity import DocHeaderEntity
import re
import datetime as dt
import os
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


EXP_INT_MITIGATION_THRESHOLD = 50


# from DocumentProcessor import tenKXMLProcessor

PARM_LOGFILE = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenLog/InsightLog')

PARM_NEW_INCLUDE_DICT_TERM_PATH = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/Dictionary/new_include_list.txt')
PARM_NEW_EXCLUDE_DICT_TERM_PATH = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/Dictionary/new_exclude_list.txt')

PARM_VALIDATION_LIST_PATH = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Testing/Dictionary/')


PARM_TENK_OUTPUT_PATH = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Extracted10K/')
PARM_FORM_PREFIX = 'https://www.sec.gov/Archives/'
PARM_STAGE1_FOLDER = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Stage1CleanTextFiles/')
WORD_RADIUS = 25


class keyWordSearchManager:

    def __init__(self, database_context: None) -> None:
        self.log_file_path = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'

        self.document_id: int
        self.document_name: str
        self.company_id: int
        self.reporting_year: int

        self.current_data: str

        self.sic_code: int
        self.company_list: any
        self.document_list = []

        self.exp_dictionary_term_list = []
        self.int_dictionary_term_list = []
        self.int_dictionary_terms = []
        self.mitigation_dictionary_term_list = []

        self.proximity_entity_list = []

        self.errors: any
        self.log_generator = logGenerator(self.log_file_path)
        self.include_log_generator = logGenerator(
            f'{PARM_NEW_INCLUDE_DICT_TERM_PATH}')
        self.exclude_log_generator = logGenerator(
            f'{PARM_NEW_EXCLUDE_DICT_TERM_PATH}')
        self.validation_log_generator = logGenerator(
            f'{PARM_VALIDATION_LIST_PATH}')

        self.big_int_location_list = []
        self.dictionary_Mgr = DictionaryManager()

        self.related_keyword_list_for_validation = dict()
        self.validation_mode = False

        # if os.path.isfile(f'{PARM_NEW_INCLUDE_DICT_TERM_PATH}'):
        #     os.remove(f'{PARM_NEW_INCLUDE_DICT_TERM_PATH}')
        # if os.path.isfile(f'{PARM_NEW_EXCLUDE_DICT_TERM_PATH}'):
        #     os.remove(f'{PARM_NEW_EXCLUDE_DICT_TERM_PATH}')

        self.insightDBMgr = InsightGeneratorDBManager(database_context)

        self.database_context = database_context

    def _get_company_list(self):
        pass

    def _load_content(self, document_name: str, year: int, document_id=9999,  qtr=1):
        pass

    def add_new_terms_to_include_exclude_dictionary_file(self, keyword, related_keyword):

        try:
            value = self.related_keyword_list_for_validation[keyword+related_keyword]
            if (value == related_keyword):
                # print('Already Found in the current pass')
                return
            else:
                self.related_keyword_list_for_validation[keyword +
                                                         related_keyword] = related_keyword

        except:
            self.related_keyword_list_for_validation[keyword +
                                                     related_keyword] = related_keyword
        exit_loop = False
        while (not exit_loop):

            if (not self.validation_mode):
                userInput = input('Enter i to Include, e to Exclude:')
                if (userInput == 'i'):
                    self.include_log_generator.log_details(
                        keyword + ':' + related_keyword, False)
                    exit_loop = True

                if (userInput == 'e'):
                    self.exclude_log_generator.log_details(
                        keyword + ':' + related_keyword, False)
                    exit_loop = True
            else:
                self.include_log_generator.log_details(
                    keyword + ':' + related_keyword, False)
                self.exclude_log_generator.log_details(
                    keyword + ':' + related_keyword, False)
                exit_loop = True


# Search all exposure pathway dictionary terms in the document and save locations


    def generate_keyword_location_map_for_exposure_pathway(self, document_List=[], batch_num=0, validation_mode=False):

        self.validation_mode = validation_mode
        # self.keyword_search_logfile_init()
        self.proximity_entity_list = []

        # self.document_list = self.insightDBMgr.get_exp_pathway_document_list(self.validation_mode)
        self.document_list = document_List
        if (len(self.document_list) == 0):
            print(
                "All documents processed: No new documents to process - Exiting generate_keyword_location_map_for_exposure_pathway")
            return

        retry_for_new_dicitonary_items = False
        document_count = 0
        for document in self.document_list:
            self.document_id = document.document_id
            self.document_name = document.document_name
            self.company_id = document.company_id
            self.reporting_year = document.year
            document_count = document_count + 1

            self._load_content(document.document_name,
                               document.document_id, document.year)

            # Generate keyword location map for exposure pathway dictionary terms
            # print(
            #     "Generating keyword location map for exposure pathway dictionary terms ")

            self._get_exp_dictionary_term_list()
            self._create_exp_dictionary_proximity_map()

            if not self.is_related_keywords_need_to_be_addressed and not self.validation_mode:
                self._save_dictionary_keyword_search_results(
                    Lookups().Exposure_Pathway_Dictionary_Type)
                self.insightDBMgr.update_exp_pathway_keyword_search_completed_ind(
                    self.document_id)

                print('Completed Keyword Search- Batch#:' + str(batch_num) +', Document:' +
                      str(document_count)+' of ' + str(len(self.document_list)))

            elif (not self.validation_mode):
                self.dictionary_Mgr.update_Dictionary()
                print("New Keywords added to Dictionary...Self Healing in effect...")
                retry_for_new_dicitonary_items = True
            elif (self.validation_mode):
               print('Completed Validation - Batch#:' + str(batch_num) +', Document:' +
                      str(document_count)+' of ' + str(len(self.document_list)))
                # Add Logic to update  Validation Completed Flags

            else:
                print(
                    'No new words to be added to the validation: Please run Live mode for:'+self.document_name)

        # if (self.validation_mode and end_validation):
        #     self.dictionary_Mgr.send_Include_Exclude_Dictionary_Files_For_Validation()

        if (retry_for_new_dicitonary_items):
            print("Rerunning..generate_keyword_location_map_for_exposure_pathway..")
            self.generate_keyword_location_map_for_exposure_pathway()

    def _get_exp_dictionary_term_list(self):

        # DEBUG Code
        # self.exp_dictionary_term_list.append(DictionaryEntity(dictionary_id=1000,keywords='floods', exposure_pathway_id=10102))

        insightDBMgr = InsightGeneratorDBManager(self.database_context)
        self.exp_dictionary_term_list = insightDBMgr.get_exp_dictionary_term_list()

    def _create_exp_dictionary_proximity_map(self):
        # print('################################################################################################')
        # print("Document In Progress:" + self.document_name)

        self.is_related_keywords_need_to_be_addressed = False
        self.proximity_entity_list.clear()
        total_dictionary_hits = 0
        for DictionaryTermList in self.exp_dictionary_term_list:
            proximity_entity = ProximityEntity(
                esg_category_id=DictionaryTermList.esg_category_id, impact_category_id=DictionaryTermList.impact_category_id, exposure_path_id=DictionaryTermList.exposure_path_id,
                dictionary_id=DictionaryTermList.dictionary_id, doc_header_id=self.document_id
            )
            key_word_list = DictionaryTermList.keywords

            key_words_natural = key_word_list.split(',')
            key_words = []
            for keyword in key_words_natural:
                key_words.append(keyword.upper())

            key_words = sorted(key_words)

            indices: any
            word_list = self.current_data.split()

            for keyword in key_words:

                indices: any

                # Find Exact Match
                if keyword in ('IT'):
                    indices = [i+1 for i, word in enumerate(word_list) if (
                        keyword.strip() == re.sub(r'[^A-Za-z0-9 /-]+', '', word))]

                else:

                    indices = [i+1 for i, word in enumerate(word_list) if (
                        keyword.strip() == re.sub(r'[^A-Za-z0-9 /-]+', '', word).upper())]

                # Find Partial Hits - corruption in 'anti-corruption' and add to database for disposal except for word "IT"
               #########################################
                keyword_cleaned = keyword.strip().upper()
                if (keyword_cleaned != 'IT'):
                    related_keyword_list = []
                    for word in word_list:
                        word_cleaned = word.replace('.', '').replace(',', '').replace(
                            ')', '').replace(';', '').replace(':', '').strip().upper()
                        word_cleaned = re.sub(
                            r'[^A-Za-z0-9 /-]+', '', word_cleaned)

                        if (keyword_cleaned in word_cleaned and keyword_cleaned != word_cleaned):
                            if (word_cleaned not in related_keyword_list and word_cleaned.upper() not in key_words):
                                # print("OROGINAL WORD:"+word)
                                related_keyword_list.append(word_cleaned)

                    contextResolver = ContextResolver()

                    if (len(related_keyword_list) > 0):
                        for related_keyword in related_keyword_list:
                            if not contextResolver.is_keyword_in_exclusion_list(keyword, related_keyword):
                                if contextResolver.is_keyword_in_inclusion_list(keyword, related_keyword):
                                    related_word_indices = [i+1 for i, word in enumerate(word_list) if (
                                        related_keyword.strip().upper() == re.sub(r'[^A-Za-z0-9 /-]+', '', word).upper())]

                                    for i in related_word_indices:
                                        indices.append(i)
                                else:
                                    # DEBUG HERE FOR RESULTS STRAY CHARACTER"

                                    # print('Add \'' + keyword + '\''+': [\''+related_keyword+'\']' + ' to ContextResolver - Inclusion OR Exclusion for Dictionary ID: ' + str(
                                    #     DictionaryTermList.dictionary_id))
                                  #  self.log_generator.log_details( '\''+keyword + '\''+': [\''+related_keyword+'\'],', False)
                                    self.add_new_terms_to_include_exclude_dictionary_file(
                                        keyword, related_keyword)
                                    self.is_related_keywords_need_to_be_addressed = True
                ###############################################

                keyword_location_entity = KeyWordLocationsEntity(key_word=keyword, locations=indices, frequency=len(
                    indices), dictionary_id=DictionaryTermList.dictionary_id, dictionary_type=Lookups().Exposure_Pathway_Dictionary_Type)

                if (keyword_location_entity.frequency > 0):
                    proximity_entity.key_word_bunch.append(
                        keyword_location_entity)
                    total_dictionary_hits = total_dictionary_hits + 1

            proximity_entity = self.combine_singular_plural_words(
                proximity_entity)

            self.proximity_entity_list.append(proximity_entity)
        self.log_generator.log_details(
            '################################################################################################')
        self.log_generator.log_details(
            "Document In Progress:" + self.document_name)
        self.log_generator.log_details(
            "Total keywords found:" + str(total_dictionary_hits))

        # print("Total key words found for "+self.document_name +
        #       ':' + str(total_dictionary_hits))
        return self.is_related_keywords_need_to_be_addressed

# Search all internalization pathway dictionary terms in the document and save locations

    def generate_keyword_location_map_for_internalization(self, document_List=[], batch_num=0, validation_mode=False):
        self.validation_mode = validation_mode
        # self.keyword_search_logfile_init()
        self.proximity_entity_list = []
        self.document_list = document_List
        if (len(self.document_list) == 0):
            print(
                "All documents processed: No new documents to process - Exiting generate_keyword_location_map_for_internalization")
            return

        retry_for_new_dicitonary_items = False
        document_count = 0
        for document in self.document_list:
            self.document_id = document.document_id
            self.document_name = document.document_name
            self.company_id = document.company_id
            self.reporting_year = document.year
            document_count = document_count + 1

            self._load_content(document.document_name,
                               document.document_id, document.year)

           # Generate keyword location map for internalization pathway dictionary terms
            # print(
            #     'Generating keyword location map for internalization pathway dictionary terms')

            self._get_int_dictionary_term_list()
            self._create_int_dictionary_proximity_map()
            if not self.is_related_keywords_need_to_be_addressed and not self.validation_mode:
                self._save_dictionary_keyword_search_results(
                    Lookups().Internalization_Dictionary_Type)
                self.insightDBMgr.update_internalization_keyword_search_completed_ind(
                    self.document_id)

                print('Completed Keyword Search- Batch#:' + str(batch_num) +', Document:' +
                      str(document_count)+' of ' + str(len(self.document_list)))

            elif (not self.validation_mode):
                self.dictionary_Mgr.update_Dictionary()
                print("New Keywords added to Dictionary...Self Healing in effect...")
                retry_for_new_dicitonary_items = True
            elif (self.validation_mode):
                print('Completed Keyword Search- Batch#:' + str(batch_num) +', Document:' +
                      str(document_count)+' of ' + str(len(self.document_list)))
               # Add Logic to update  Validation Completed Flags
            else:
                print(
                    'No new words to be added to the validation: Please run Live mode for:'+self.document_name)

        # if (self.validation_mode and end_validation):
        #     self.dictionary_Mgr.send_Include_Exclude_Dictionary_Files_For_Validation()

        if (retry_for_new_dicitonary_items and not self.validation_mode):
            print("Rerunning..generate_keyword_location_map_for_internalization..")
            self.generate_keyword_location_map_for_internalization()

    def _get_int_dictionary_term_list(self):
        # DEBUG Code
        # self.int_dictionary_term_list.append(DictionaryEntity(dictionary_id=1001,keywords='materials', exposure_pathway_id=10102))

        insightDBMgr = InsightGeneratorDBManager(self.database_context)
        self.int_dictionary_term_list = self.insightDBMgr.get_int_dictionary_term_list()

    def _create_int_dictionary_proximity_map(self):
        # print('################################################################################################')
        # print("Document In Progress:" + self.document_name)

        self.is_related_keywords_need_to_be_addressed = False

        self.proximity_entity_list.clear()
        total_dictionary_hits = 0
        for DictionaryTermList in self.int_dictionary_term_list:
            proximity_entity = ProximityEntity(dictionary_id=DictionaryTermList.dictionary_id, doc_header_id=self.document_id,
                                               internalization_id=DictionaryTermList.internalization_id
                                               )
            key_word_list = DictionaryTermList.keywords

            key_words_natural = key_word_list.split(',')
            key_words = []
            for keyword in key_words_natural:
                key_words.append(keyword.upper())

            key_words = sorted(key_words)

            indices: any
            word_list = self.current_data.split()

            for keyword in key_words:

                indices: any

                # Find Exact Match
                if keyword in ('IT'):
                    indices = [i+1 for i, word in enumerate(word_list) if (
                        keyword.strip() == re.sub(r'[^A-Za-z0-9 /-]+', '', word))]

                else:

                    indices = [i+1 for i, word in enumerate(word_list) if (
                        keyword.strip() == re.sub(r'[^A-Za-z0-9 /-]+', '', word).upper())]

                # Find Partial Hits - corruption in 'anti-corruption' and add to database for disposal except for word "IT"
               #########################################
                keyword_cleaned = keyword.strip().upper()
                if (keyword_cleaned != 'IT'):
                    related_keyword_list = []
                    for word in word_list:
                        word_cleaned = word.replace('.', '').replace(',', '').replace(
                            ')', '').replace(';', '').replace(':', '').strip().upper()
                        word_cleaned = re.sub(
                            r'[^A-Za-z0-9 /-]+', '', word_cleaned)

                        if (keyword_cleaned in word_cleaned and keyword_cleaned != word_cleaned):
                            if (word_cleaned not in related_keyword_list and word_cleaned.upper() not in key_words):
                                # print("OROGINAL WORD:"+word)
                                related_keyword_list.append(word_cleaned)

                    contextResolver = ContextResolver()

                    if (len(related_keyword_list) > 0):
                        for related_keyword in related_keyword_list:
                            if not contextResolver.is_keyword_in_exclusion_list(keyword, related_keyword):
                                if contextResolver.is_keyword_in_inclusion_list(keyword, related_keyword):
                                    related_word_indices = [i+1 for i, word in enumerate(word_list) if (
                                        related_keyword.strip().upper() == re.sub(r'[^A-Za-z0-9 /-]+', '', word).upper())]

                                    for i in related_word_indices:
                                        indices.append(i)
                                else:
                                    # DEBUG HERE FOR RESULTS STRAY CHARACTER"

                                    print('Add \'' + keyword + '\''+': [\''+related_keyword+'\']' + ' to ContextResolver - Inclusion OR Exclusion for Dictionary ID: ' + str(
                                        DictionaryTermList.dictionary_id))
                                    # self.log_generator.log_details( '\''+keyword + '\''+': [\''+related_keyword+'\'],', False)
                                    self.add_new_terms_to_include_exclude_dictionary_file(
                                        keyword, related_keyword)

                                    self.is_related_keywords_need_to_be_addressed = True
                ###############################################

                keyword_location_entity = KeyWordLocationsEntity(key_word=keyword, locations=indices, frequency=len(
                    indices), dictionary_id=DictionaryTermList.dictionary_id, dictionary_type=Lookups().Exposure_Pathway_Dictionary_Type)

                if (keyword_location_entity.frequency > 0):
                    proximity_entity.key_word_bunch.append(
                        keyword_location_entity)
                    total_dictionary_hits = total_dictionary_hits + 1

            proximity_entity = self.combine_singular_plural_words(
                proximity_entity)

            self.proximity_entity_list.append(proximity_entity)
        self.log_generator.log_details(
            '################################################################################################')
        self.log_generator.log_details(
            "Document In Progress:" + self.document_name)
        self.log_generator.log_details(
            "Total keywords found:" + str(total_dictionary_hits))

        # print("Total key words found for "+self.document_name +
        #       ':' + str(total_dictionary_hits))f
        return self.is_related_keywords_need_to_be_addressed

    def combine_singular_plural_words(self, proximity_entity: ProximityEntity):
        combined_entity = ProximityEntity()
        child_entity = copy.deepcopy(proximity_entity)
        for master_item in proximity_entity.key_word_bunch:
            for child_item in child_entity.key_word_bunch:

                if (master_item.key_word != child_item.key_word and master_item.key_word in child_item.key_word):
                    temp_item = copy.deepcopy(master_item)
                    temp_item.key_word = child_item.key_word
                    temp_item.temp_place_holder = master_item.key_word
                    for location in child_item.locations:
                        if location not in master_item.locations:
                            temp_item.locations.append(location)

                    temp_item.dictionary_id = master_item.dictionary_id
                    temp_item.frequency = len(temp_item.locations)

                    combined_entity.esg_category_id = proximity_entity.esg_category_id
                    combined_entity.impact_category_id = proximity_entity.impact_category_id
                    combined_entity.exposure_path_id = proximity_entity.exposure_path_id
                    combined_entity.dictionary_id = proximity_entity.dictionary_id
                    combined_entity.doc_header_id = proximity_entity.doc_header_id
                    combined_entity.internalization_id = proximity_entity.internalization_id

                    combined_entity.key_word_bunch.append(temp_item)

        # print("Singular/Plural keywords merged:" + str(len(combined_entity.key_word_bunch)))
        for master_item in proximity_entity.key_word_bunch:
            found = False
            for child_item in combined_entity.key_word_bunch:
                if (master_item.key_word not in child_item.key_word):
                    found = False
                else:
                    found = True
                    break
            if (not found):
                temp_item = copy.deepcopy(master_item)
                combined_entity.esg_category_id = proximity_entity.esg_category_id
                combined_entity.impact_category_id = proximity_entity.impact_category_id
                combined_entity.exposure_path_id = proximity_entity.exposure_path_id
                combined_entity.dictionary_id = proximity_entity.dictionary_id
                combined_entity.doc_header_id = proximity_entity.doc_header_id
                combined_entity.internalization_id = combined_entity.internalization_id

                combined_entity.key_word_bunch.append(temp_item)

        index = 0
        for child_item in combined_entity.key_word_bunch:
            if (combined_entity.key_word_bunch[index].temp_place_holder != ''):
                combined_entity.key_word_bunch[index].key_word = combined_entity.key_word_bunch[index].temp_place_holder

        return combined_entity

# Search all mitigation dictionary terms in the document and save locations

    def generate_keyword_location_map_for_mitigation(self, document_List=[], batch_num=0, validation_mode=False):
        # self.keyword_search_logfile_init()
        self.validation_mode = validation_mode
        self.proximity_entity_list = []
        self.document_list = document_List
        if (len(self.document_list) == 0):
            print(
                "All documents processed: No new documents to process - Exiting generate_keyword_location_map_for_mitigation")
            return

        retry_for_new_dicitonary_items = False
        document_count = 0
        for document in self.document_list:
            self.document_id = document.document_id
            self.document_name = document.document_name
            self.company_id = document.company_id
            self.reporting_year = document.year
            document_count = document_count + 1

            self._load_content(document.document_name,
                               document.document_id, document.year)

           # Generate keyword location map for Mitigation pathway dictionary terms
            # print('Generating keyword location map for mitigation dictionary terms')
            self._get_mitigation_dictionary_term_list()
            self._create_mitigation_dictionary_proximity_map()

            if not self.is_related_keywords_need_to_be_addressed and not self.validation_mode:
                self._save_dictionary_keyword_search_results(
                    Lookups().Mitigation_Dictionary_Type)
                self.insightDBMgr.update_mitigation_keyword_search_completed_ind(
                    self.document_id)

                print('Completed Keyword Search- Batch#:' + str(batch_num) +', Document:' +
                      str(document_count)+' of ' + str(len(self.document_list)))
            elif (not self.validation_mode):
                self.dictionary_Mgr.update_Dictionary()
                print("New Keywords added to Dictionary...Self Healing in effect...")
                retry_for_new_dicitonary_items = True
            elif (self.validation_mode):
                print('Completed Keyword Search- Batch#:' + str(batch_num) +', Document:' +
                      str(document_count)+' of ' + str(len(self.document_list)))
                # Add logic to update Valdiation Flags
            else:
                print(
                    'No new words to be added to the validation: Please run Live mode for:'+self.document_name)

        # if (self.validation_mode and end_validation):
        #     self.dictionary_Mgr.send_Include_Exclude_Dictionary_Files_For_Validation()
        if (retry_for_new_dicitonary_items and not self.validation_mode):
            print("Rerunning..generate_keyword_location_map_for_mitigation..")
            self.generate_keyword_location_map_for_mitigation()

    def _get_mitigation_dictionary_term_list(self):

        insightDBMgr = InsightGeneratorDBManager(self.database_context)
        self.mitigation_dictionary_term_list = self.insightDBMgr.get_mitigation_dictionary_term_list()

    def _create_mitigation_dictionary_proximity_map(self):

        # print('################################################################################################')
        # print("Document In Progress:" + self.document_name)

        self.is_related_keywords_need_to_be_addressed = False

        self.proximity_entity_list.clear()
        total_dictionary_hits = 0
        for DictionaryTermList in self.mitigation_dictionary_term_list:
            proximity_entity = ProximityEntity(
                DictionaryTermList.dictionary_id, self.document_id)
            key_word_list = DictionaryTermList.keywords

            key_words_natural = key_word_list.split(',')
            key_words = []
            for keyword in key_words_natural:
                key_words.append(keyword.upper())

            key_words = sorted(key_words)

            indices: any
            word_list = self.current_data.split()

            for keyword in key_words:

                indices: any

                # Find Exact Match
                if keyword in ('IT'):
                    indices = [i+1 for i, word in enumerate(word_list) if (
                        keyword.strip() == re.sub(r'[^A-Za-z0-9 /-]+', '', word))]

                else:

                    indices = [i+1 for i, word in enumerate(word_list) if (
                        keyword.strip() == re.sub(r'[^A-Za-z0-9 /-]+', '', word).upper())]

                # Find Partial Hits - corruption in 'anti-corruption' and add to database for disposal except for word "IT"
               #########################################
                keyword_cleaned = keyword.strip().upper()
                if (keyword_cleaned != 'IT'):
                    related_keyword_list = []
                    for word in word_list:
                        word_cleaned = word.replace('.', '').replace(',', '').replace(
                            ')', '').replace(';', '').replace(':', '').strip().upper()
                        word_cleaned = re.sub(
                            r'[^A-Za-z0-9 /-]+', '', word_cleaned)

                        if (keyword_cleaned in word_cleaned and keyword_cleaned != word_cleaned):
                            if (word_cleaned not in related_keyword_list and word_cleaned.upper() not in key_words):
                                # print("OROGINAL WORD:"+word)
                                related_keyword_list.append(word_cleaned)

                    contextResolver = ContextResolver()

                    if (len(related_keyword_list) > 0):
                        for related_keyword in related_keyword_list:
                            if not contextResolver.is_keyword_in_exclusion_list(keyword, related_keyword):
                                if contextResolver.is_keyword_in_inclusion_list(keyword, related_keyword):
                                    related_word_indices = [i+1 for i, word in enumerate(word_list) if (
                                        related_keyword.strip().upper() == re.sub(r'[^A-Za-z0-9 /-]+', '', word).upper())]

                                    for i in related_word_indices:
                                        indices.append(i)
                                else:
                                    # DEBUG HERE FOR RESULTS STRAY CHARACTER"

                                    print('Add \'' + keyword + '\''+': [\''+related_keyword+'\']' + ' to ContextResolver - Inclusion OR Exclusion for Dictionary ID: ' + str(
                                        DictionaryTermList.dictionary_id))
                                    # self.log_generator.log_details( '\''+keyword + '\''+': [\''+related_keyword+'\'],', False)
                                    self.add_new_terms_to_include_exclude_dictionary_file(
                                        keyword, related_keyword)

                                    self.is_related_keywords_need_to_be_addressed = True
                ###############################################

                keyword_location_entity = KeyWordLocationsEntity(key_word=keyword, locations=indices, frequency=len(
                    indices), dictionary_id=DictionaryTermList.dictionary_id, dictionary_type=Lookups().Exposure_Pathway_Dictionary_Type)

                if (keyword_location_entity.frequency > 0):
                    proximity_entity.key_word_bunch.append(
                        keyword_location_entity)
                    total_dictionary_hits = total_dictionary_hits + 1

            proximity_entity = self.combine_singular_plural_words(
                proximity_entity)

            self.proximity_entity_list.append(proximity_entity)
        self.log_generator.log_details(
            '################################################################################################')
        self.log_generator.log_details(
            "Document In Progress:" + self.document_name)
        self.log_generator.log_details(
            "Total keywords found:" + str(total_dictionary_hits))

        # print("Total key words found for "+self.document_name +
        #       ':' + str(total_dictionary_hits))

    def _save_dictionary_keyword_search_results(self, dictionary_type: int):
        # Save Keyword search Results to Database
        if (self.proximity_entity_list):
            self.insightDBMgr.save_key_word_hits(self.proximity_entity_list, self.company_id, self.document_id,
                                                 self.document_name, self.reporting_year, dictionary_type=dictionary_type)

    def send_Include_Exclude_Dictionary_Files_For_Validation(self):
        self.dictionary_Mgr.send_Include_Exclude_Dictionary_Files_For_Validation()


class db_Insight_keyWordSearchManager(keyWordSearchManager):
    def __init__(self) -> None:
        super().__init__()

    def _load_content(self, document_name: str, document_id: int, year: int, qtr: int):

        self.document_id = document_id
        document_name = document_name.replace('.txt', '.xml')

        f_input_file_path = f'{PARM_TENK_OUTPUT_PATH}Year{year}Q{qtr}/{document_name}'

        with open(f_input_file_path, 'r') as fin:
            # self.current_data = fin.read()
            sourcedata = fin.read()
            self.current_data_encoded = sourcedata.encode(('ascii', 'ignore'))
            self.current_data = self.current_data_encoded.decode(
                'ascii', errors='ignore')


class file_folder_keyWordSearchManager(keyWordSearchManager):
    def __init__(self, folder_path: str, database_context: None) -> None:
        super().__init__(database_context)
        self.folder_path = folder_path

    def _load_content(self, document_name: str, document_id: int, year: int):

        self.document_id = document_id
        self.document_name = document_name

        f_input_file_path = f'{self.folder_path}/{year}/{document_name}'

        with open(f_input_file_path, 'r') as fin:
          # self.current_data = fin.read()
            sourcedata = fin.read()
            current_data_encoded = sourcedata.encode('ascii', 'replace')
            current_data_decoded = current_data_encoded.decode(
                'ascii', errors='replace')
            self.current_data = current_data_decoded.replace('?', ' ')

    def _get_document_id(self, file: str):
        document: KeyWordLocationsEntity

        for document in self.document_list:
            current_id = document.document_id
            if (document.document_name == file):
                return document.document_id
        # If document not configured in table  abort
        print("Document not configured in t_document table")
        raise Exception("Document not configured in t_document table")


class Insight_Generator(keyWordSearchManager):

    # Generate Insights for two keyword combinations
    def generate_insights_with_2_factors(self, dictionary_type: int, document_keyword_list=[], batch_num=0):

        # print('Generating insights for Dictionary Type:' +
        #       str(dictionary_type))

        document_keyword_list = document_keyword_list

        if len(document_keyword_list) < 1:
            print('Document List with Zero Documents:WHY?????:' + str(dictionary_type))
            return

        document_item: KeyWordLocationsEntity
        for document_item in document_keyword_list:
            self.log_generator.log_details("Processing Batch:"+str(batch_num)+", Document ID:"+str(
                document_item.document_id)+", dictionary_type:"+str(document_item.dictionary_type)+", Dictionary ID:" + str(document_item.dictionary_id))
            # print("Processing Batch:"+str(document_item.batch_id)+", Document ID:"+str(document_item.document_id) +
            #       ", dictionary_type:"+str(document_item.dictionary_type)+", Dictionary ID:" + str(document_item.dictionary_id))
            self._generate_insights_with_2_factors_by_dictionary_id(dictionary_type=document_item.dictionary_type,
                                                                    dictionary_id=document_item.dictionary_id, document_id=document_item.document_id, document_name=document_item.document_name)
             

    def _generate_insights_with_2_factors_by_dictionary_id(self, dictionary_type=0, dictionary_id=0, document_id=0, document_name=''):
        keyword_location_list = self._load_keyword_location_list(
            dictionary_type, dictionary_id, document_id)
        insightList = []
        keyword_location: KeyWordLocationsEntity
        for keyword_location in keyword_location_list:
            master_locations = keyword_location.locations.strip(
                '[').strip(']').split(',')
            int_master_locations = np.asarray(master_locations, dtype=np.int32)
            child_node: KeyWordLocationsEntity
            for child_node in keyword_location_list:
                radius_locations = []
                factor1_frequency = 0
                factor2_distance_list = []
                factor2_average_distance = 0.0
                score = 0.0

                if (child_node.key_word_hit_id > keyword_location.key_word_hit_id):
                    child_locations = child_node.locations.strip(
                        '[').strip(']').split(',')
                    int_child_locations = np.asarray(
                        child_locations, dtype=np.int32)
                    for int_master_location in int_master_locations:

                        radius_location_partial = (self._get_related_word_locations_in_Radius_for_child_list(
                            int_master_location, int_child_locations))
                        # factor1_frequency = factor1_frequency + \
                        #     len(radius_location_partial)

                        for location in radius_location_partial:
                            distance = abs(int_master_location - location)
                            try:
                                if (distance == 0):
                                    self.log_generator.log_details("Distance 0 - Ignoring Weight Calculation: Keyword:" + keyword_location.key_word +
                                                                   ", Child Key word:" + child_node.key_word+", Location:"+str(location))
                                else:
                                    ratio = 1/distance
                                    factor2_distance_list.append(ratio)
                                    factor1_frequency = factor1_frequency + 1
                            except Exception as exc:
                                # Rollback the transaction if any error occurs
                                print(f"Error: {str(exc)}")
                                print("Error Processing Key Word:" +
                                      keyword_location.key_word)
                                raise exc
                            # ratio = distance/WORD_RADIUS

                    if (len(factor2_distance_list) > 0):
                        factor2_average_distance = np.average(
                            factor2_distance_list)
                        if (factor2_average_distance > 0.0):
                            score = factor1_frequency * \
                                (1/factor2_average_distance)

                    if (score > 0.0):
                        insight = Insight(keyword_hit_id1=keyword_location.key_word_hit_id, keyword1=keyword_location.key_word,
                                          keyword_hit_id2=child_node.key_word_hit_id, keyword2=child_node.key_word, score=score,
                                          factor1=factor1_frequency, factor2=factor2_average_distance, document_name=document_name, document_id=document_id,
                                          exposure_path_id=keyword_location.exposure_path_id, internalization_id=keyword_location.internalization_id
                                          )
                        insightList.append(insight)
        self.log_generator.log_details(
            "Total Insights generated:" + str(len(insightList)))
        self.log_generator.log_details(
            '################################################################################################')

        insights_genetated = len(insightList)
        # print("Total Insights generated:" + str(insights_genetated))

        if (insights_genetated > 0):
            self.insightDBMgr.save_insights(
                insightList=insightList, dictionary_type=dictionary_type)

            self.insightDBMgr.update_insights_generated_from_keyword_hits_batch(
                dictionary_type=dictionary_type, dictionary_id=dictionary_id, document_id=document_id)

            self.insightDBMgr.normalize_document_score(
                dictionary_type=dictionary_type, document_id=document_id)

    def _load_keyword_location_list(self, dictionary_type=0, dictionary_id=0, document_id=0):
        return (self.insightDBMgr.get_keyword_location_list(dictionary_type, dictionary_id, document_id))

    def _get_related_word_locations_in_Radius_for_child_list(self, int_keyword_location: int, int_child_locations: any):
        radius_upper = int_keyword_location + WORD_RADIUS
        radius_lower: int

        if (int_keyword_location - WORD_RADIUS < 0):
            radius_lower = 0
        else:
            radius_lower = int_keyword_location - WORD_RADIUS

        radius_locations = [location for location in int_child_locations if location >=
                            radius_lower and location <= radius_upper]

        # print(radius_locations)
        return radius_locations


# Generate Aggregate Insights


    def generate_aggregate_insights_from_keyword_location_details(self):

        # Create a sorted array of all locations found for a given dictionary list
        self.big_int_location_list.clear()
        big_int_location_list = []
        big_list = []
        keyword_location_list = self._load_keyword_location_list()
        keyword_location: KeyWordLocationsEntity
        for keyword_location in keyword_location_list:
            locations = keyword_location.locations.strip(
                '[').strip(']').split(',')
            big_list = np.append(big_list, locations)
            # print('Current Big List Count:'+ str(len(big_list)))
        self.big_int_location_list = np.sort(
            np.asarray(big_list, dtype=np.int32))

        # For each keyword in the dictionary list, compute the Distance Factor as 1 * 10000 / word distance
        # Try for Supply: 1002
        for keyword_location in keyword_location_list:
            # print('Processing:'+ keyword_location.key_word)
            self._compute_FD_Factor(keyword_location)

    def _get_related_word_locations_in_Radius(self, int_keyword_location: int):
        radius_upper = int_keyword_location + WORD_RADIUS
        radius_lower: int

        if (int_keyword_location - WORD_RADIUS < 0):
            radius_lower = 0
        else:
            radius_lower = int_keyword_location - WORD_RADIUS

        radius_locations = [location for location in self.big_int_location_list if location >=
                            radius_lower and location <= radius_upper]

        # print(radius_locations)
        return radius_locations

    def _compute_FD_Factor(self, keyword_location: KeyWordLocationsEntity):
        # print('Computing Frequency Distance Factor for:'+ keyword_location.key_word)
        fd_factors_for_keyword = []

        keyword_hit_id = keyword_location.key_word_hit_id
        keyword = keyword_location.key_word
        frequency = keyword_location.frequency
        locations = keyword_location.locations.strip('[').strip(']').split(',')

        int_keyword_locations = np.asarray(locations, dtype=np.int32)
        fd_factor1 = FD_Factor(keyword_hit_id=keyword_hit_id,
                               keyword=keyword, frequency=frequency)
        for int_keyword_location in int_keyword_locations:

            # print(int_keyword_location)
            related_word_locations = self._get_related_word_locations_in_Radius(
                int_keyword_location=int_keyword_location)

            # Compute the Distance Factor as 1 * 10000 / word distance
            calculated_factor = 0.00
            for related_word_location in related_word_locations:
                distance = abs(int_keyword_location - related_word_location)
                if (distance != 0):
                    calculated_factor = calculated_factor + (1*(1/distance))
            fd_factor1.add_fd_factor(
                round(calculated_factor, 2), len(related_word_locations))
        fd_factors_for_keyword.append(fd_factor1)

        # print("Frequency Distance Factors:"+str(fd_factors_for_keyword))

        fd_factor2: FD_Factor
        for fd_factor2 in fd_factors_for_keyword:
            print("Key Word:"+fd_factor2.keyword)
            print("FD Factors:"+str(fd_factor2.fd_factor))


class triangulation_Insight_Generator(keyWordSearchManager):

    def _get_distance_list_for_locations_in_Radius(self, int_keyword_location: int, int_child_locations: any):
        radius_upper = int_keyword_location + WORD_RADIUS
        radius_lower: int

        if (int_keyword_location - WORD_RADIUS < 0):
            radius_lower = 0
        else:
            radius_lower = int_keyword_location - WORD_RADIUS

        radius_locations = [location for location in int_child_locations if location >=
                            radius_lower and location <= radius_upper]

        distance_list = [abs(int_keyword_location - location)
                         for location in radius_locations]

        # print(radius_locations)
        return distance_list

    # EXP VS. INT
    def generate_exp_int_insights(self, document_list:[], batch_num=0):
        self.log_generator.log_details(
            "Generating Exposure Pathway ->Internalization Insights")
        print("###########################################################")
        print("Generating Exposure Pathway ->Internalization Insights")
        document_list = self.insightDBMgr.get_exp_int_document_list()

        if (len(document_list) == 0):
            print(
                'No new document available to process Exposure Pathway-Internalization Insights')
            return

        document_item: KeyWordLocationsEntity
        document_count = 0
        for document_item in document_list:
            self.log_generator.log_details(
                "Document ID:"+str(document_item.document_id)+", Document Name:"+str(document_item.document_name))
            # print("Document ID:"+str(document_item.document_id) +
            #       ", Document Name:"+str(document_item.document_name))

            self.exp_insight_location_list, self.int_insight_location_list = self.insightDBMgr.get_exp_int_lists(
                document_item.document_id)
            # print("Exp Insight locations:"+str(len(self.exp_insight_location_list)) +
            #       ", Int Insight locations:"+str(len(self.int_insight_location_list)))

            exp_insight_entity: Insight
            self.int_exp_insightList = []

            record_count = len(self.exp_insight_location_list)
            # current_count = 1
            for exp_insight_entity in self.exp_insight_location_list:
                # print('Processing '+str(current_count) +
                #       ' of ' + str(record_count)+'  Insights')

                combined_exp_insight_location_list = (exp_insight_entity.locations1.strip(
                    ']').strip('[') + ',' + exp_insight_entity.locations2.strip(']').strip('[')).split(',')
                # print("EXP INSIGHT LOCATIONS for "+exp_insight_entity.keyword1+','+exp_insight_entity.keyword2+':'+str(combined_exp_insight_location_list))
                for int_insight_entity in self.int_insight_location_list:
                    combined_int_insight_location_list = (int_insight_entity.locations1.strip(
                        ']').strip('[') + ',' + int_insight_entity.locations2.strip(']').strip('[')).split(',')
                    # print("INT INSIGHT LOCATIONS for"+int_insight_entity.keyword1+','+int_insight_entity.keyword2+':'+str(combined_int_insight_location_list))
                    self._create_exp_int_insights_for_document(combined_exp_insight_location_list, combined_int_insight_location_list, document_item.document_id,
                                                               document_item.document_name, exp_insight_entity, int_insight_entity)
                # current_count = current_count + 1

            self.log_generator.log_details("Dcoument:"+document_item.document_name +
                                           ", Total Exp Int Insights generated:" + str(len(self.int_exp_insightList)))
            document_count = document_count + 1
            print('Completed Keyword Search- Batch#:' + str(batch_num) +', Document:' +
                      str(document_count)+' of ' + str(len(self.document_list)))

            # print("Dcoument:"+document_item.document_name +
            #       ", Total Exp Int Insights generated:" + str(len(self.int_exp_insightList)))

            self.insightDBMgr.cleanup_insights_for_document(Lookups().Exp_Int_Insight_Type,document_item.document_id)

            self.insightDBMgr.save_Exp_Int_Insights(
                insightList=self.int_exp_insightList, dictionary_type=Lookups().Exp_Int_Insight_Type)

            self.insightDBMgr.update_triangulation_insights_generated_batch(dictionary_type=Lookups(
            ).Exp_Int_Insight_Type, document_id=document_item.document_id)

            self.insightDBMgr.normalize_document_score(dictionary_type=Lookups(
            ).Exp_Int_Insight_Type, document_id=document_item.document_id)

    def _create_exp_int_insights_for_document(self, exp_insight_keyword_locations: None, int_insight_keyword_locations: None, document_id=0, document_name='', exp_insight_entity=None,   int_insight_entity=None):

        integer_exp_insight_keyword_locations = np.asarray(
            exp_insight_keyword_locations, dtype=np.int32)

        integer_int_insight_keyword_locations = np.asarray(
            int_insight_keyword_locations, dtype=np.int32)

        # Remove Duplicates - In case of related words: For ex- Forest, Deforestation
        integer_exp_insight_keyword_locations = list(
            set(integer_exp_insight_keyword_locations))
        integer_int_insight_keyword_locations = list(
            set(integer_int_insight_keyword_locations))

        distance_list = np.array([])
        for integer_exp_insight_keyword_location in integer_exp_insight_keyword_locations:
            distance_list = np.append(distance_list, self._get_distance_list_for_locations_in_Radius(
                integer_exp_insight_keyword_location, integer_int_insight_keyword_locations))

        factor1_frequency = 0
        factor2_distance_list = []
        factor2_average_distance = 0.0
        score = 0.0

        factor1_frequency = factor1_frequency + len(distance_list)

        for distance in distance_list:
            try:
                if distance > 0.00:
                    ratio = 1/distance
                    factor2_distance_list.append(ratio)
            except Exception as exc:
                # Rollback the transaction if any error occurs
                print(f"Error: {str(exc)}")
                print("Error Processing Exp Key Words:" +
                      exp_insight_entity.keyword1 + ',' + exp_insight_entity.keyword2)
                raise exc

        if (len(factor2_distance_list) > 0):
            factor2_average_distance = np.average(factor2_distance_list)
            if (factor2_average_distance > 0.0):
                score = factor1_frequency * (1/factor2_average_distance)

        if (score > 0.0):
            exp_int_insight = ExpIntInsight(
                exp_keyword_hit_id1=exp_insight_entity.keyword_hit_id1,
                exp_keyword1=exp_insight_entity.keyword1,
                exp_keyword_hit_id2=exp_insight_entity.keyword_hit_id2,
                exp_keyword2=exp_insight_entity.keyword2,
                int_key_word_hit_id1=int_insight_entity.keyword_hit_id1,
                int_key_word1=int_insight_entity.keyword1,
                int_key_word_hit_id2=int_insight_entity.keyword_hit_id2,
                int_key_word2=int_insight_entity.keyword2,
                factor1=factor1_frequency,
                factor2=factor2_average_distance,
                score=score,
                document_name=document_name,
                document_id=document_id,
                exposure_path_id=exp_insight_entity.exposure_path_id,
                internalization_id=int_insight_entity.internalization_id
            )

            self.int_exp_insightList.append(exp_int_insight)

            # self.log_generator.log_details("Exp Keywords:"+exp_insight_entity.keyword1+"," +exp_insight_entity.keyword2+"  "
            #                                "Int Keywords:"+int_insight_entity.keyword1+"," +int_insight_entity.keyword2+"  "+ " ,Score:"+str(score))

            # print("Exp Keywords:"+exp_insight_entity.keyword1+"," +exp_insight_entity.keyword2+"  "
            #       "Int Keywords:"+int_insight_entity.keyword1+"," +int_insight_entity.keyword2+"  "+ " ,Score:"+str(score))

    def _get_combined_insight_exp_keyword_location_list(self, keyword_hit_id1: int, keyword_hit_id2: int):
        location_list1: str
        location_list2: str
        keyword_location: KeyWordLocationsEntity
        for keyword_location in self.exp_keyword_location_list:
            if (keyword_location.key_word_hit_id == keyword_hit_id1):
                location_list1 = (keyword_location.locations).strip(
                    '[').strip(']')
            if (keyword_location.key_word_hit_id == keyword_hit_id2):
                location_list2 = (keyword_location.locations).strip(
                    '[').strip(']')
        combined_location_list = location_list1+','+location_list2
        # print('Combined Locations for '+str(keyword_hit_id1) + ','+ str(keyword_hit_id2)+': ' +combined_location_list)
        return (combined_location_list)

    def _get_combined_insight_int_keyword_location_list(self, keyword_hit_id1: int, keyword_hit_id2: int):
        location_list1: str
        location_list2: str
        keyword_location: KeyWordLocationsEntity
        for keyword_location in self.int_keyword_location_list:
            if (keyword_location.key_word_hit_id == keyword_hit_id1):
                location_list1 = (keyword_location.locations).strip(
                    '[').strip(']')
            if (keyword_location.key_word_hit_id == keyword_hit_id2):
                location_list2 = (keyword_location.locations).strip(
                    '[').strip(']')
        combined_location_list = location_list1+','+location_list2
        # print('Combined Locations for '+str(keyword_hit_id1) + ','+ str(keyword_hit_id2)+': ' +combined_location_list)
        return (combined_location_list)

    # MITIGATION

    def generate_mitigation_exp_insights(self):
        self.log_generator.log_details(
            "Generating  Exposure -> Mitigation Insights")
        print("###########################################################")
        print("Generating  Exposure -> Mitigation Insights")

        document_list = self.insightDBMgr.get_exp_mitigation_document_list()

        if (len(document_list) == 0):
            print('No new document available to process Mitigation-Exposure Insights')
            return

        document_item: KeyWordLocationsEntity
        for document_item in document_list:
            self.log_generator.log_details(
                "Document ID:"+str(document_item.document_id)+", Document Name:"+str(document_item.document_name))
            print("Document ID:"+str(document_item.document_id) +
                  ", Document Name:"+str(document_item.document_name))

            self.mitigation_keyword_location_list, self.exp_keyword_location_list, self.exp_insight_list = self.insightDBMgr.get_exp_mitigation_lists(
                document_item.document_id)
            print("Mitigation key word locations:"+str(len(self.mitigation_keyword_location_list)) +
                  ", Exp key word locations:"+str(len(self.exp_keyword_location_list))+", insights:"+str(len(self.exp_insight_list)))
            exp_insight_entity: Insight
            self.mitigation_comon_insightList = []

            record_count = len(self.exp_insight_list)
            current_count = 1

            for exp_insight_entity in self.exp_insight_list:

                # print('Processing '+str(current_count) +
                #       ' of ' + str(record_count)+'  Insights')

                # Get combined location list for each insight word combo
                doc_location_list = self._get_combined_insight_exp_keyword_location_list(
                    exp_insight_entity.keyword_hit_id1, exp_insight_entity.keyword_hit_id2)
                # compute score against each mitigation key word
                for mitigation_keyword_locations in self.mitigation_keyword_location_list:

                    self._create_mitigation_insights_for_document(mitigation_keyword_locations, doc_location_list, document_item.document_id,
                                                                  document_item.document_name, exp_insight_entity, mitigation_keyword_locations.key_word, mitigation_keyword_locations.key_word_hit_id,
                                                                  exposure_path_id=exp_insight_entity.exposure_path_id
                                                                  )
                current_count = current_count + 1

            self.log_generator.log_details("Dcoument:"+document_item.document_name +
                                           ", Total Mitigation Insights generated:" + str(len(self.mitigation_comon_insightList)))

            print("Dcoument:"+document_item.document_name +
                  ", Total Mitigation Insights generated:" + str(len(self.mitigation_comon_insightList)))

            self.insightDBMgr.save_insights(
                insightList=self.mitigation_comon_insightList, dictionary_type=Lookups().Mitigation_Exp_Insight_Type)

            self.insightDBMgr.update_triangulation_insights_generated_batch(dictionary_type=Lookups(
            ).Mitigation_Exp_Insight_Type, document_id=document_item.document_id)

            self.insightDBMgr.normalize_document_score(dictionary_type=Lookups(
            ).Mitigation_Exp_Insight_Type, document_id=document_item.document_id)

    def generate_mitigation_int_insights(self):
        self.log_generator.log_details(
            "Generating Mitigation Insights for Internalization Pathways")
        print("###########################################################")
        print("Generating  Internalization -> Mitigation Insights")

        document_list = self.insightDBMgr.get_int_mitigation_document_list()

        if (len(document_list) == 0):
            print(
                'No new document available to process Mitigation-Internalization Insights')
            return

        document_item: KeyWordLocationsEntity
        for document_item in document_list:
            self.log_generator.log_details(
                "Document ID:"+str(document_item.document_id)+", Document Name:"+str(document_item.document_name))
            print("Document ID:"+str(document_item.document_id) +
                  ", Document Name:"+str(document_item.document_name))

            self.mitigation_keyword_location_list, self.int_keyword_location_list, self.int_insight_list = self.insightDBMgr.get_int_mitigation_lists(
                document_item.document_id)
            print("Mitigation key word locations:"+str(len(self.mitigation_keyword_location_list)) +
                  ", Int key word locations:"+str(len(self.int_keyword_location_list))+", insights:"+str(len(self.int_insight_list)))
            int_insight_entity: Insight
            self.mitigation_comon_insightList = []

            record_count = len(self.int_insight_list)
            current_count = 1

            for int_insight_entity in self.int_insight_list:

                # print('Processing '+str(current_count) +
                #       ' of ' + str(record_count)+'  Insights')

                # Get combined location list for each insight word combo
                doc_location_list = self._get_combined_insight_int_keyword_location_list(
                    int_insight_entity.keyword_hit_id1, int_insight_entity.keyword_hit_id2)
                # compute score against each mitigation key word
                for mitigation_keyword_locations in self.mitigation_keyword_location_list:
                    self._create_mitigation_insights_for_document(mitigation_keyword_locations, doc_location_list, document_item.document_id,
                                                                  document_item.document_name, int_insight_entity, mitigation_keyword_locations.key_word, mitigation_keyword_locations.key_word_hit_id, internalization_id=int_insight_entity.internalization_id)
                current_count = current_count + 1

            self.log_generator.log_details("Dcoument:"+document_item.document_name +
                                           ", Total Mitigation Insights generated:" + str(len(self.mitigation_comon_insightList)))

            print("Dcoument:"+document_item.document_name +
                  ", Total Mitigation Insights generated:" + str(len(self.mitigation_comon_insightList)))

            self.insightDBMgr.save_insights(
                insightList=self.mitigation_comon_insightList, dictionary_type=Lookups().Mitigation_Int_Insight_Type)

            self.insightDBMgr.update_triangulation_insights_generated_batch(dictionary_type=Lookups(
            ).Mitigation_Int_Insight_Type, document_id=document_item.document_id)

            self.insightDBMgr.normalize_document_score(dictionary_type=Lookups(
            ).Mitigation_Int_Insight_Type, document_id=document_item.document_id)

    def _create_mitigation_insights_for_document(self, mitigation_keyword_locations: None, doc_location_list: None, document_id=0, document_name='', insight_entity=None,   mitigation_keyword='', mitigation_keyword_hit_id=0, exposure_path_id=0, internalization_id=0):

        mitigation_keyword_locations = mitigation_keyword_locations.locations.strip(
            '[').strip(']').split(',')
        int_mitigation_keyword_locations = np.asarray(
            mitigation_keyword_locations, dtype=np.int32)

        doc_location_list = doc_location_list.strip('[').strip(']').split(',')
        int_doc_location_list = np.asarray(doc_location_list, dtype=np.int32)

        # Remove Duplicates - In case of related words: For ex- Forest, Deforestation
        int_doc_location_list = list(set(int_doc_location_list))

        distance_list = np.array([])
        for int_mitigation_keyword_location in int_mitigation_keyword_locations:
            distance_list = np.append(distance_list, self._get_distance_list_for_locations_in_Radius(
                int_mitigation_keyword_location, int_doc_location_list))

        factor1_frequency = 0
        factor2_distance_list = []
        factor2_average_distance = 0.0
        score = 0.0

        factor1_frequency = factor1_frequency + len(distance_list)

        for distance in distance_list:
            try:
                if distance > 0.00:
                    ratio = 1/distance
                    factor2_distance_list.append(ratio)
            except Exception as exc:
                # Rollback the transaction if any error occurs
                print(f"Error: {str(exc)}")
                print("Error Processing Key Word:" + mitigation_keyword)
                raise exc

        if (len(factor2_distance_list) > 0):
            factor2_average_distance = np.average(factor2_distance_list)
            if (factor2_average_distance > 0.0):
                score = factor1_frequency * (1/factor2_average_distance)

        if (score > 0.0):
            insight = Insight(mitigation_keyword_hit_id=mitigation_keyword_hit_id, mitigation_keyword=mitigation_keyword,
                              keyword_hit_id1=insight_entity.keyword_hit_id1, keyword1=insight_entity.keyword1,
                              keyword_hit_id2=insight_entity.keyword_hit_id2, keyword2=insight_entity.keyword2, score=score,
                              factor1=factor1_frequency, factor2=factor2_average_distance, document_name=document_name, document_id=document_id,
                              exposure_path_id=exposure_path_id, internalization_id=internalization_id
                              )
            self.mitigation_comon_insightList.append(insight)
            self.log_generator.log_details("Mitigation:"+mitigation_keyword+", Keywords:" +
                                           insight_entity.keyword1+' ,'+insight_entity.keyword2 + " ,Score"+str(score))
            # print("Mitigation:"+mitigation_keyword+",Exp Keywords:"+exp_insight_entity.keyword1+' ,'+exp_insight_entity.keyword2, +" , Score"+score)

    def generate_mitigation_exp_int_insights(self):
        self.log_generator.log_details(
            "Generating Exposure Pathway, Internalization -> Mitigation Insights")
        print("###########################################################")
        print("Generating Exposure Pathway, Internalization -> Mitigation Insights")

        document_list = self.insightDBMgr.get_mitigation_exp_int_document_list()

        if (len(document_list) == 0):
            print(
                'No new document available to process Exposure Pathway-Internalization Insights')
            return

        document_item: KeyWordLocationsEntity
        for document_item in document_list:
            self.log_generator.log_details(
                "Document ID:"+str(document_item.document_id)+", Document Name:"+str(document_item.document_name))
            print("Document ID:"+str(document_item.document_id) +
                  ", Document Name:"+str(document_item.document_name))

            self.exp_int_insight_list, self.mitigation_keyword_list = self.insightDBMgr.get_mitigation_exp_int_lists(
                document_item.document_id)
            print("Exp Int Insight locations:"+str(len(self.exp_int_insight_list)) +
                  ", Mitigation Keyword locations:"+str(len(self.mitigation_keyword_list)))

            mitigation_exp_int_insight_entity: MitigationExpIntInsight()
            self.mitigation_comon_insightList = []

            record_count = len(self.exp_int_insight_list)
            current_count = 1
            for exp_int_insight_entity in self.exp_int_insight_list:
                print('Processing '+str(current_count) +
                      ' of ' + str(record_count)+'  Insights')

                combined_exp_int_insight_location_list = (exp_int_insight_entity.exp1_locations.strip(']').strip('[')
                                                          + ',' +
                                                          exp_int_insight_entity.exp2_locations.strip(
                                                              ']').strip('[')
                                                          + ',' +
                                                          exp_int_insight_entity.int1_locations.strip(
                                                              ']').strip('[')
                                                            + ',' +
                                                          exp_int_insight_entity.int2_locations.strip(
                                                              ']').strip('[')
                                                          ).split(',')
                # combined_exp_int_insight_location_list = (exp_int_insight_entity.int2_locations.strip(']').strip('[')
                #                                           ).split(',')

                # print("EXP INSIGHT LOCATIONS for "+exp_insight_entity.keyword1+','+exp_insight_entity.keyword2+':'+str(combined_exp_insight_location_list))
                mitigation_entity: MitigationExpIntInsight()
                for mitigation_entity in self.mitigation_keyword_list:
                    self._create_combined_exp_int_mitigation_insights_for_document(mitigation_keyword_locations=mitigation_entity.locations,
                                                                                   doc_location_list=combined_exp_int_insight_location_list, exp_int_insight_entity=exp_int_insight_entity, document_id=document_item.document_id, document_name=document_item.document_name,
                                                                                   mitigation_keyword_hit_id=mitigation_entity.key_word_hit_id, mitigation_keyword=mitigation_entity.key_word
                                                                                   )
                current_count = current_count + 1

            self.log_generator.log_details("Dcoument:"+document_item.document_name +
                                           ", Total Exp Int -> Mitigation Insights generated:" + str(len(self.mitigation_comon_insightList)))

            print("Dcoument:"+document_item.document_name +
                  ", Total Exp Int => Mitigation Insights generated:" + str(len(self.mitigation_comon_insightList)))

            self.insightDBMgr.save_Mitigation_Exp_Int_Insights(
                insightList=self.mitigation_comon_insightList, dictionary_type=Lookups().Mitigation_Exp_INT_Insight_Type)

            self.insightDBMgr.update_triangulation_insights_generated_batch(dictionary_type=Lookups(
            ).Mitigation_Exp_INT_Insight_Type, document_id=document_item.document_id)

            self.insightDBMgr.normalize_document_score(dictionary_type=Lookups(
            ).Mitigation_Exp_INT_Insight_Type, document_id=document_item.document_id)

    def _create_combined_exp_int_mitigation_insights_for_document(self, mitigation_keyword_locations: None, doc_location_list: None, exp_int_insight_entity: MitigationExpIntInsight, document_id=0, document_name='', mitigation_keyword='', mitigation_keyword_hit_id=0):

        mitigation_keyword_locations = mitigation_keyword_locations.strip(
            '[').strip(']').split(',')
        int_mitigation_keyword_locations = np.asarray(
            mitigation_keyword_locations, dtype=np.int32)

        # doc_location_list = doc_location_list.strip('[').strip(']').split(',')
        int_doc_location_list = np.asarray(doc_location_list, dtype=np.int32)

        # Remove Duplicates - In case of related words: For ex- Forest, Deforestation
        int_doc_location_list = list(set(int_doc_location_list))

        distance_list = np.array([])
        for int_mitigation_keyword_location in int_mitigation_keyword_locations:
            distance_list = np.append(distance_list, self._get_distance_list_for_locations_in_Radius(
                int_mitigation_keyword_location, int_doc_location_list))

        factor1_frequency = 0
        factor2_distance_list = []
        factor2_average_distance = 0.0
        score = 0.0

        factor1_frequency = factor1_frequency + len(distance_list)

        for distance in distance_list:
            try:
                if distance > 0.00:
                    ratio = 1/distance
                    factor2_distance_list.append(ratio)
            except Exception as exc:
                # Rollback the transaction if any error occurs
                print(f"Error: {str(exc)}")
                print("Error Processing Key Word:" + mitigation_keyword)
                raise exc

        if (len(factor2_distance_list) > 0):
            factor2_average_distance = np.average(factor2_distance_list)
            if (factor2_average_distance > 0.0):
                score = factor1_frequency * (1/factor2_average_distance)

        if (score > EXP_INT_MITIGATION_THRESHOLD):
            insight = MitigationExpIntInsight(mitigation_keyword_hit_id=mitigation_keyword_hit_id, mitigation_keyword=mitigation_keyword,
                                              exp_keyword_hit_id1=exp_int_insight_entity.exp_keyword_hit_id1,
                                              exp_keyword1=exp_int_insight_entity.exp_keyword1,
                                              exp_keyword_hit_id2=exp_int_insight_entity.exp_keyword_hit_id2,
                                              exp_keyword2=exp_int_insight_entity.exp_keyword2,
                                              int_key_word_hit_id1=exp_int_insight_entity.int_key_word_hit_id1,
                                              int_key_word1=exp_int_insight_entity.int_key_word1,
                                              int_key_word_hit_id2=exp_int_insight_entity.int_key_word_hit_id2,
                                              int_key_word2=exp_int_insight_entity.int_key_word2,
                                              factor1=factor1_frequency, factor2=factor2_average_distance, score=score,
                                              document_name=document_name, document_id=document_id,
                                              exposure_path_id=exp_int_insight_entity.exposure_path_id, internalization_id=exp_int_insight_entity.internalization_id
                                              )
            self.mitigation_comon_insightList.append(insight)
            # print("Mitigation:"+mitigation_keyword+",Exp Keywords:"+exp_insight_entity.keyword1+' ,'+exp_insight_entity.keyword2, +" , Score"+score)
