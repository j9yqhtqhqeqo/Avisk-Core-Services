from Utilities.PathConfiguration import PathConfiguration
from Utilities.LoggingServices import logGenerator
import ast
import sys
from pathlib import Path
import datetime as dt
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


class DuplicateDictionaryTermsError(Exception):
    """Exception raised when same keywords exist in both include and exclude files"""
    def __init__(self, duplicate_terms):
        self.duplicate_terms = duplicate_terms
        message = f"Found {len(duplicate_terms)} duplicate keyword(s) in both include and exclude files. Please review and keep them in only ONE file."
        super().__init__(message)


# Initialize path configuration
path_config = PathConfiguration()

# Get paths from PathConfiguration
NEW_INCLUDE_DITCTORY_ITEM_PATH = path_config.get_new_include_dict_term_path()
CURRENT_INCLUDE_DITCTORY_ITEM_PATH = os.path.join(
    os.path.dirname(NEW_INCLUDE_DITCTORY_ITEM_PATH), 'InclusionDictionary.txt')

NEW_EXCLUDE_DITCTORY_ITEM_PATH = path_config.get_new_exclude_dict_term_path()
CURRENT_EXCLUDE_DITCTORY_ITEM_PATH = os.path.join(
    os.path.dirname(NEW_EXCLUDE_DITCTORY_ITEM_PATH), 'ExclusionDictionary.txt')

INCLUDE_LOG_FOLDER = os.path.join(
    path_config.get_include_logs_path(), 'InclusionDictionary_bkp_')

EXCLUDE_LOG_FOLDER = os.path.join(
    path_config.get_exclude_logs_path(), 'ExclusionDictionary_bkp_')

VALIDATION_FILES_FOLDER = path_config.get_validation_list_path()


class DictionaryManager:
    def __init__(self) -> None:
        pass  # Files are directly accessible via FUSE mount

    def _update_Dictionary_Items(self, new_dictionary_item_path, current_dictionary_item_path, bkp_file_path):
        # Files are directly accessible via FUSE mount
        # Ensure current dictionary exists
        if not os.path.exists(current_dictionary_item_path):
            print(
                f"Warning: Could not find dictionary file: {current_dictionary_item_path}")
            # Create empty dictionary if file doesn't exist
            os.makedirs(os.path.dirname(
                current_dictionary_item_path), exist_ok=True)
            with open(current_dictionary_item_path, 'w') as f:
                f.write('{}')

        with open(current_dictionary_item_path, 'r') as currentdict:
            current_data = currentdict.read()
            current_dict_items = ast.literal_eval(current_data)

        with open(new_dictionary_item_path, 'r') as file:
            lines = [line.strip() for line in file]
            for line in lines:
                # print("PRINTNG LINE....")
                # print(line)
                key_value = line.split(':')
                key = key_value[0].upper().strip()
                value = key_value[1].upper().strip()

                # FIND IF THE KEY EXISTS IN  DICT, If not Add new Entry. If exists, update the Dictionary Entry
                try:
                    current_values = (current_dict_items[key])
                    # Copy current values to a new list to append new values
                    new_list = (current_dict_items[key])

                    if isinstance(new_list, list):
                        if (value not in current_values):
                            new_list.append(value)
                            del current_dict_items[key]
                            current_dict_items[key] = new_list

                   # Dictionary returns string for a single entry - construct a list to append additional values
                    elif (value != current_values):
                        new_list_for_string = [value, current_values]
                        del current_dict_items[key]
                        current_dict_items[key] = new_list_for_string

                except KeyError as exc:
                    current_dict_items[key] = value

        # Backup Current Dictionary Files
        # Archive Processed Files
        os.makedirs(os.path.dirname(bkp_file_path), exist_ok=True)
        os.rename(current_dictionary_item_path, bkp_file_path)

        # Build dictionary content in memory first for better performance
        dict_lines = ['{']
        
        new_sorted_dict = dict(sorted(current_dict_items.items()))
        for key, value in new_sorted_dict.items():
            if isinstance(value, list):
                dict_lines.append('\'' + key.strip()+'\':' + str(value) + ',')
            else:
                # It's a string value - wrap it in list format
                value_1 = '[\''+value+'\']'
                dict_lines.append('\'' + key.strip()+'\':' + str(value_1) + ',')
        
        dict_lines.append('}')
        
        # Write all content at once
        os.makedirs(os.path.dirname(current_dictionary_item_path), exist_ok=True)
        with open(current_dictionary_item_path, 'w') as f:
            f.write('\n'.join(dict_lines))
            f.flush()
            os.fsync(f.fileno())

        # Files written to FUSE mount are automatically in GCS

    def _check_for_duplicate_terms(self):
        """Check if same keywords exist in both include and exclude files"""
        include_terms = set()
        exclude_terms = set()
        
        # Read include file if it exists
        if os.path.isfile(NEW_INCLUDE_DITCTORY_ITEM_PATH):
            with open(NEW_INCLUDE_DITCTORY_ITEM_PATH, 'r') as f:
                for line in f:
                    if line.strip():
                        key_value = line.strip().split(':')
                        if len(key_value) >= 2:
                            key = key_value[0].upper().strip()
                            value = key_value[1].upper().strip()
                            include_terms.add(f"{key}:{value}")
        
        # Read exclude file if it exists
        if os.path.isfile(NEW_EXCLUDE_DITCTORY_ITEM_PATH):
            with open(NEW_EXCLUDE_DITCTORY_ITEM_PATH, 'r') as f:
                for line in f:
                    if line.strip():
                        key_value = line.strip().split(':')
                        if len(key_value) >= 2:
                            key = key_value[0].upper().strip()
                            value = key_value[1].upper().strip()
                            exclude_terms.add(f"{key}:{value}")
        
        # Find duplicates
        duplicates = include_terms.intersection(exclude_terms)
        if duplicates:
            raise DuplicateDictionaryTermsError(list(duplicates))
    
    def update_Dictionary(self):
        print('Update Dictionary Called..Check Why??')
        
        # Check for duplicate terms before processing
        self._check_for_duplicate_terms()
        
        include_dict_bkp_path = f'{INCLUDE_LOG_FOLDER}{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        exclude_dict_bkp_path = f'{EXCLUDE_LOG_FOLDER}{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

        dictionary_manager = DictionaryManager()

        if os.path.isfile(f'{NEW_INCLUDE_DITCTORY_ITEM_PATH}'):
            dictionary_manager._update_Dictionary_Items(
                NEW_INCLUDE_DITCTORY_ITEM_PATH, CURRENT_INCLUDE_DITCTORY_ITEM_PATH, include_dict_bkp_path)
            print("New Inclusion keywords added to the dictionary")
        else:
            print(
                "No new Inclusion keywords found!!. Document(s) already validated or No documents to validate")

        if os.path.isfile(f'{NEW_EXCLUDE_DITCTORY_ITEM_PATH}'):
            dictionary_manager._update_Dictionary_Items(
                NEW_EXCLUDE_DITCTORY_ITEM_PATH, CURRENT_EXCLUDE_DITCTORY_ITEM_PATH, exclude_dict_bkp_path)
            print("New Exclusion keywords added to the dictionary")
        else:
            print(
                "No new Exclusion keywords found!!. Document(s) already validated or No documents to validate")

    def send_Include_Exclude_Dictionary_Files_For_Validation(self):

        current_dict_items = dict()
        # Remove duplciate Lines
        if not os.path.isfile(f'{NEW_INCLUDE_DITCTORY_ITEM_PATH}'):
            print(
                "No new Inclusion keywords found!!. Document(s) already validated or No documents to validate")

        else:
            with open(NEW_INCLUDE_DITCTORY_ITEM_PATH, 'r') as file:
                lines = [line.strip() for line in file]
                for line in lines:
                    key_value = line.split(':')
                    key = key_value[0].upper().strip()
                    value = key_value[1].upper().strip()

                    # FIND IF THE KEY EXISTS IN  DICT, If not Add new Entry
                    try:
                        current_values = (current_dict_items[key])
                        # Copy current values to a new list to append new values
                        new_list = (current_dict_items[key])
                        if isinstance(new_list, list):
                            if (value not in current_values):
                                new_list.append(value)
                                del current_dict_items[key]
                                current_dict_items[key] = new_list
                         # Dictionary returns string for a single entry - construct a list to append additional values
                        elif (value != current_values):
                            new_list_for_string = [value, current_values]
                            del current_dict_items[key]
                            current_dict_items[key] = new_list_for_string

                    except KeyError as exc:
                        current_dict_items[key] = value

            new_sorted_dict = dict(sorted(current_dict_items.items()))
            if os.path.isfile(f'{NEW_INCLUDE_DITCTORY_ITEM_PATH}'):
                os.remove(f'{NEW_INCLUDE_DITCTORY_ITEM_PATH}')
            log_generator = logGenerator(NEW_INCLUDE_DITCTORY_ITEM_PATH)

            for key, valuelist in new_sorted_dict.items():
                if isinstance(valuelist, list):
                    for value in valuelist:
                        log_generator.log_details(
                            key.strip()+':' + str(value), False)
                else:
                    log_generator.log_details(
                        key.strip()+':' + str(valuelist), False)

            new_include_file_name = 'new_include_list_' + \
                f'{dt.datetime.now()}.txt'
            os.rename(NEW_INCLUDE_DITCTORY_ITEM_PATH,
                      f'{VALIDATION_FILES_FOLDER}{new_include_file_name}')
            print('Sent File'+new_include_file_name+'for Validation')

        if not os.path.isfile(f'{NEW_EXCLUDE_DITCTORY_ITEM_PATH}'):
            print(
                "No new Exclusion keywords found!!. Document(s) already validated or No documents to validate ")
        else:
            with open(NEW_EXCLUDE_DITCTORY_ITEM_PATH, 'r') as file:
                lines = [line.strip() for line in file]
                for line in lines:
                    key_value = line.split(':')
                    key = key_value[0].upper().strip()
                    value = key_value[1].upper().strip()

                    # FIND IF THE KEY EXISTS IN  DICT, If not Add new Entry
                    try:
                        current_values = (current_dict_items[key])
                        # Copy current values to a new list to append new values
                        new_list = (current_dict_items[key])
                        if isinstance(new_list, list):
                            if (value not in current_values):
                                new_list.append(value)
                                del current_dict_items[key]
                                current_dict_items[key] = new_list
                          # Dictionary returns string for a single entry - construct a list to append additional values
                        elif (value != current_values):
                            new_list_for_string = [value, current_values]
                            del current_dict_items[key]
                            current_dict_items[key] = new_list_for_string

                    except KeyError as exc:
                        current_dict_items[key] = value

            new_sorted_dict = dict(sorted(current_dict_items.items()))
            if os.path.isfile(f'{NEW_EXCLUDE_DITCTORY_ITEM_PATH}'):
                os.remove(f'{NEW_EXCLUDE_DITCTORY_ITEM_PATH}')

            log_generator = logGenerator(NEW_EXCLUDE_DITCTORY_ITEM_PATH)

            for key, valuelist in new_sorted_dict.items():
                if isinstance(valuelist, list):
                    for value in valuelist:
                        log_generator.log_details(
                            key.strip()+':' + str(value), False)
                else:
                    log_generator.log_details(
                        key.strip()+':' + str(valuelist), False)

            new_exclude_file_name = 'new_exclude_list_' + \
                f'{dt.datetime.now()}.txt'
            os.rename(NEW_EXCLUDE_DITCTORY_ITEM_PATH,
                      f'{VALIDATION_FILES_FOLDER}{new_exclude_file_name}')
            print('Sent File:'+new_exclude_file_name+'for Validation')


class ContextResolver:

    def __init__(self) -> None:
        # Files are directly accessible via FUSE mount - just check if they exist

        # Ensure inclusion dictionary is available
        if not os.path.exists(CURRENT_INCLUDE_DITCTORY_ITEM_PATH):
            raise FileNotFoundError(
                f"Inclusion dictionary not found: {CURRENT_INCLUDE_DITCTORY_ITEM_PATH}"
            )

        with open(CURRENT_INCLUDE_DITCTORY_ITEM_PATH, 'r') as include_dict:
            include_dict_data = include_dict.read()
            self.Inclusion_Dictionary = ast.literal_eval(include_dict_data)

        # Ensure exclusion dictionary is available
        if not os.path.exists(CURRENT_EXCLUDE_DITCTORY_ITEM_PATH):
            raise FileNotFoundError(
                f"Exclusion dictionary not found: {CURRENT_EXCLUDE_DITCTORY_ITEM_PATH}"
            )

        with open(CURRENT_EXCLUDE_DITCTORY_ITEM_PATH, 'r') as exclude_dict:
            exclude_dict_data = exclude_dict.read()
            self.Exclusion_Dictionary = ast.literal_eval(exclude_dict_data)

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

# dict_mgr = DictionaryManager()
# dict_mgr.send_Include_Exclude_Dictionary_Files_For_Validation()
# dict_mgr.update_Dictionary()

# context_resolve = ContextResolver()
