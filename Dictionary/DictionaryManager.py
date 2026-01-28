from Utilities.GCSFileManager import gcs_manager
from Utilities.PathConfiguration import PathConfiguration
from Utilities.LoggingServices import logGenerator
import ast
import sys
from pathlib import Path
import datetime as dt
import os
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


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
        self.gcs_manager = gcs_manager if gcs_manager.is_available() else None

    def _ensure_file_available(self, file_path: str, gcs_relative_path: str) -> bool:
        """Ensure file is available locally, download from GCS if needed"""
        # If file exists locally, use it
        if os.path.exists(file_path):
            return True

        # If GCS is available, try to download
        if self.gcs_manager:
            print(f"Downloading dictionary file from GCS: {gcs_relative_path}")
            return self.gcs_manager.download_file(gcs_relative_path, file_path, overwrite=False)

        return False

    def _sync_to_gcs(self, file_path: str, gcs_relative_path: str):
        """Upload file to GCS if available"""
        if self.gcs_manager and os.path.exists(file_path):
            try:
                self.gcs_manager.upload_file(file_path, gcs_relative_path)
            except Exception as e:
                print(f"Warning: Failed to sync dictionary to GCS: {e}")

    def _update_Dictionary_Items(self, new_dictionary_item_path, current_dictionary_item_path, bkp_file_path):
        # Determine GCS paths
        dict_filename = os.path.basename(current_dictionary_item_path)
        gcs_dict_path = f"Dictionary/{dict_filename}"

        # Ensure current dictionary is available locally
        if not self._ensure_file_available(current_dictionary_item_path, gcs_dict_path):
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

        # Sync backup to GCS
        bkp_filename = os.path.basename(bkp_file_path)
        gcs_bkp_path = f"Dictionary/Backups/{bkp_filename}"
        self._sync_to_gcs(bkp_file_path, gcs_bkp_path)

        log_generator = logGenerator(current_dictionary_item_path)
        log_generator.log_details('{', False)

        new_sorted_dict = dict(sorted(current_dict_items.items()))
        for key, value in new_sorted_dict.items():
            if isinstance(value, list):
                log_generator.log_details(
                    '\'' + key.strip()+'\':' + str(value) + ',', False)
            elif ('[' not in value):
                value_1 = '[\''+value+'\']'
                log_generator.log_details(
                    '\'' + key.strip()+'\':' + str(value_1) + ',', False)

        log_generator.log_details('}', False)

        # Sync updated dictionary to GCS
        self._sync_to_gcs(current_dictionary_item_path, gcs_dict_path)

    def update_Dictionary(self):
        # print('Update Dictionary Called..Check Why??')
        include_dict_bkp_path = f'{INCLUDE_LOG_FOLDER}{dt.datetime.now().strftime("%c")}.txt'
        exclude_dict_bkp_path = f'{EXCLUDE_LOG_FOLDER}{dt.datetime.now().strftime("%c")}.txt'

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
        dict_manager = DictionaryManager()

        # Ensure inclusion dictionary is available
        gcs_include_path = "Dictionary/InclusionDictionary.txt"
        if not dict_manager._ensure_file_available(CURRENT_INCLUDE_DITCTORY_ITEM_PATH, gcs_include_path):
            raise FileNotFoundError(
                f"Inclusion dictionary not found: {CURRENT_INCLUDE_DITCTORY_ITEM_PATH}. "
                f"Please ensure the file exists locally or in GCS at {gcs_include_path}"
            )

        with open(CURRENT_INCLUDE_DITCTORY_ITEM_PATH, 'r') as include_dict:
            include_dict_data = include_dict.read()
            self.Inclusion_Dictionary = ast.literal_eval(include_dict_data)

        # Ensure exclusion dictionary is available
        gcs_exclude_path = "Dictionary/ExclusionDictionary.txt"
        if not dict_manager._ensure_file_available(CURRENT_EXCLUDE_DITCTORY_ITEM_PATH, gcs_exclude_path):
            raise FileNotFoundError(
                f"Exclusion dictionary not found: {CURRENT_EXCLUDE_DITCTORY_ITEM_PATH}. "
                f"Please ensure the file exists locally or in GCS at {gcs_exclude_path}"
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
