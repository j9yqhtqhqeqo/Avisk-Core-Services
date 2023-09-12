import ast
import sys
from pathlib import Path
import datetime as dt
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


from Utilities.LoggingServices import logGenerator
from Utilities.LoggingServices import logGenerator



NEW_INCLUDE_DITCTORY_ITEM_PATH = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/Dictionary/new_include_list.txt')

CURRENT_INCLUDE_DITCTORY_ITEM_PATH = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/Dictionary/InclusionDictionary.txt')

NEW_EXCLUDE_DITCTORY_ITEM_PATH = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/Dictionary/new_exclude_list.txt')

CURRENT_EXCLUDE_DITCTORY_ITEM_PATH = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/Dictionary/ExclusionDictionary.txt')


INCLUDE_LOG_FOLDER = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/Dictionary/IncludeLogs/InclusionDictionary_bkp_')

EXCLUDE_LOG_FOLDER = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/Dictionary/ExcludeLogs/ExclusionDictionary_bkp_')

VALIDATION_FILES_FOLDER = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Source Code/Data-Company/Dictionary/Validation_Files/')



class DictionaryManager:
    def __init__(self) -> None:
        pass

    def _update_Dictionary_Items(self, new_dictionary_item_path, current_dictionary_item_path, bkp_file_path):

        with open(current_dictionary_item_path, 'r') as currentdict:
            current_data  = currentdict.read()
            current_dict_items = ast.literal_eval(current_data)

        with open(new_dictionary_item_path, 'r') as file:
            lines = [line.strip() for line in file]
            for line in lines:
                key_value = line.split(':')
                key = key_value[0].upper().strip()
                value = key_value[1].upper().strip()

                ##FIND IF THE KEY EXISTS IN  DICT, If not Add new Entry. If exists, update the Dictionary Entry
                try:
                    current_values = (current_dict_items[key])
                    #Copy current values to a new list to append new values
                    new_list = (current_dict_items[key])

                    if isinstance(new_list, list):
                        if(value not in current_values):
                            new_list.append(value)
                            del current_dict_items[key]
                            current_dict_items[key] = new_list
                            
                   ## Dictionary returns string for a single entry - construct a list to append additional values
                    elif(value != current_values):
                        new_list_for_string = [value,current_values]
                        del current_dict_items[key]
                        current_dict_items[key] = new_list_for_string

                   
                except KeyError as exc:
                    current_dict_items[key] = value

        #Backup Current Dictionary Files
        #Archive Processed Files    
        os.rename(current_dictionary_item_path,bkp_file_path)

        log_generator = logGenerator(current_dictionary_item_path)
        log_generator.log_details('{',False)

        new_sorted_dict = dict(sorted(current_dict_items.items())) 
        for key, value in new_sorted_dict.items():
            if isinstance(value, list):
                log_generator.log_details('\''+ key.strip()+'\':'+ str(value) +',',False)   
            elif('[' not in value):
                value_1 = '[\''+value+'\']'
                log_generator.log_details('\''+ key.strip()+'\':'+ str(value_1) +',',False)

        log_generator.log_details('}',False)

    def update_Dictionary(self):
        include_dict_bkp_path = f'{INCLUDE_LOG_FOLDER}{dt.datetime.now().strftime("%c")}.txt' 
        exclude_dict_bkp_path = f'{EXCLUDE_LOG_FOLDER}{dt.datetime.now().strftime("%c")}.txt'  

        dictionary_manager = DictionaryManager()

        if os.path.isfile(f'{NEW_INCLUDE_DITCTORY_ITEM_PATH}'):
            dictionary_manager._update_Dictionary_Items(NEW_INCLUDE_DITCTORY_ITEM_PATH, CURRENT_INCLUDE_DITCTORY_ITEM_PATH, include_dict_bkp_path)

        if os.path.isfile(f'{NEW_EXCLUDE_DITCTORY_ITEM_PATH}'):
            dictionary_manager._update_Dictionary_Items(NEW_EXCLUDE_DITCTORY_ITEM_PATH,CURRENT_EXCLUDE_DITCTORY_ITEM_PATH, exclude_dict_bkp_path)

    def send_Include_Exclude_Dictionary_Files_For_Validation(self, document_name):

        new_include_file_name = 'Include_Recommendation_'+ document_name
        new_exclude_file_name = 'Exclude_Recommendation_'+ document_name
        os.rename(NEW_INCLUDE_DITCTORY_ITEM_PATH,f'{VALIDATION_FILES_FOLDER}/{new_include_file_name}')
        os.rename(NEW_EXCLUDE_DITCTORY_ITEM_PATH,f'{VALIDATION_FILES_FOLDER}/{new_exclude_file_name}')

        print('Sent File'+document_name+'for Validation')

                
class ContextResolver:

    def __init__(self) -> None:

        with open(CURRENT_INCLUDE_DITCTORY_ITEM_PATH, 'r') as include_dict:
            include_dict_data  = include_dict.read()
            self.Inclusion_Dictionary =  ast.literal_eval(include_dict_data)

        with open(CURRENT_EXCLUDE_DITCTORY_ITEM_PATH, 'r') as exclude_dict:
            exclude_dict_data  = exclude_dict.read()
            self.Exclusion_Dictionary =  ast.literal_eval(exclude_dict_data)

    def is_keyword_in_exclusion_list(self, keyword: str, related_word: str):

        try:

            related_words = self.Exclusion_Dictionary[keyword.upper()]

        except:
            return False

        if related_word.upper() in related_words:
            return True

        return False

    def is_keyword_in_inclusion_list(self, keyword: str, related_word: str):
        try:

            related_words = self.Inclusion_Dictionary[keyword.upper()]

        except:
            return False

        if related_word.upper() in related_words:
            return True

        return False

dict_mgr = DictionaryManager()
dict_mgr.update_Dictionary()