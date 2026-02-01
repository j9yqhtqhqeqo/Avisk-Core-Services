from Utilities.MultiProcessing import get_process_buffer
from Utilities.Lookups import Lookups
import multiprocessing
from DBEntities.LookupsDBManager import LookupsDBManager
import time
from multiprocessing import Process, Queue, Pool
from DBEntities.ProximityEntity import DocumentEntity
from Services.InsightGenerator import file_folder_keyWordSearchManager, PARM_STAGE1_FOLDER
from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager
import sys
from pathlib import Path
import warnings
import logging

# Suppress Streamlit ScriptRunContext warnings
warnings.filterwarnings('ignore', message='.*ScriptRunContext.*')
logging.getLogger(
    'streamlit.runtime.scriptrunner.script_runner').setLevel(logging.ERROR)

sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


def load_document_cache_for_exposure_pathway(validation_mode, queue: Queue, queue_size=Queue):
    exposure_document_list = InsightGeneratorDBManager().get_exp_pathway_document_list(validation_mode)
    for document in exposure_document_list:
        queue.put(document)

    queue_size.put(len(exposure_document_list))
    print('Documents Loaded for Exposure Pathway Keyword Search:',
          len(exposure_document_list))


def process_next_unprocessed_exposure_document_list(batch_size, queue: Queue, batch_num, validation_mode):
    Document_List = []
    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        Document_List.append(document)

    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER)

    key_word_search_mgr.generate_keyword_location_map_for_exposure_pathway(
        Document_List, batch_num, validation_mode)
    if (validation_mode):
        InsightGeneratorDBManager().update_validation_keywords_generated_status(
            Document_List, Lookups().Exposure_Pathway_Dictionary_Type, 2)


def process_exposure_pathway_document_list(validation_mode=False):
    print("Creating Batches for Exposure Pathway Keyword Search -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_exposure_pathway,
                           args=(validation_mode, queue, queue_size,))
    cache_loader.start()
    # cache_loader.join()

    queue_size_int = queue_size.get()
    batches = get_process_buffer(queue_size_int, io_bound=True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager()
        process_state = (l_dbmgr.get_exposure_pathway_search_status())
        if (process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_exposure_document_list,
                         args=(batches[i], queue, i+1, validation_mode,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))
        else:
            print(
                'Process Not in Run Stat - Exiting process_exposure_pathway_document_list')
            break

    cache_loader.join()
    for process in process_list:
        process.join()

    print('All documents processed:Check for documents failed keyword validation')


def load_document_cache_for_internalization(validation_mode, queue: Queue, queue_size=Queue):
    internalization_document_list = InsightGeneratorDBManager(
        ).get_internalization_document_list(validation_mode)
    for document in internalization_document_list:
        queue.put(document)

    queue_size.put(len(internalization_document_list))
    print('Documents Loaded for Internalization Keyword Search')


def process_next_unprocessed_internalization_document_list(batch_size, queue: Queue, batch_num, validation_mode):
    Document_List = []
    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        Document_List.append(document)

    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER)

    key_word_search_mgr.generate_keyword_location_map_for_internalization(
        Document_List, batch_num, validation_mode)
    if (validation_mode):
        InsightGeneratorDBManager().update_validation_keywords_generated_status(
            Document_List, Lookups().Internalization_Dictionary_Type, 2)


def process_internalization_document_list(validation_mode=False):
    print("Creating Batches for Internalization Keyword Search - ")

    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_internalization,
                           args=(validation_mode, queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()

    batches = get_process_buffer(queue_size_int, io_bound=True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager()
        process_state = (l_dbmgr.get_exposure_pathway_search_status())
        if (process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_internalization_document_list,
                         args=(batches[i], queue, i+1, validation_mode,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))
        else:
            print(
                'Process Not in Run Stat - Exiting process_exposure_pathway_document_list')
            break

    cache_loader.join()
    for process in process_list:
        process.join()

    print('All documents processed:Check for documents failed keyword validation')


def load_document_cache_for_mitigation(validation_mode, queue_mit: Queue, queue_size_mit=Queue):
    mitigation_document_list = InsightGeneratorDBManager(
        ).get_mitigation_document_list(validation_mode)
    for document in mitigation_document_list:
        queue_mit.put(document)

    queue_size_mit.put(len(mitigation_document_list))
    print('Documents Loaded for Mitigation Keyword Search')


def process_next_unprocessed_mitigation_document_list(batch_size, queue: Queue, batch_num, validation_mode):
    Document_List = []

    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        Document_List.append(document)

    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER)

    key_word_search_mgr.generate_keyword_location_map_for_mitigation(
        Document_List, batch_num, validation_mode)
    if (validation_mode):
        InsightGeneratorDBManager().update_validation_keywords_generated_status(
            Document_List, Lookups().Mitigation_Dictionary_Type, 2)


def process_mitigation_document_list( validation_mode=False):
    print("Creating Batches for Mitigation Keyword Search -")

    queue = Queue()
    queue_size = Queue()

    cache_loader = Process(target=load_document_cache_for_mitigation,
                           args=(validation_mode, queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()

    batches = get_process_buffer(queue_size_int, True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager()
        process_state = (l_dbmgr.get_exposure_pathway_search_status())
        if (process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_mitigation_document_list,
                         args=(batches[i], queue, i+1, validation_mode,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))
        else:
            print(
                'Process Not in Run Stat - Exiting process_exposure_pathway_document_list')
            break

    cache_loader.join()
    for process in process_list:
        process.join()

    print('All documents processed:Check for documents failed keyword validation')


def update_validation_completed_status():
    # print("✅ Processed Dictionary Terms Successfully - DEBUG -- SINGLETON")

    InsightGeneratorDBManager().update_validation_completed_status()


def update_sector_stats(sector, year: int, generate_exp_sector_insights: bool, generate_int_sector_insights: bool, generate_exp_mit_sector_insights: bool, generate_exp_int_mit_sector_insights: bool, update_all: bool):
    InsightGeneratorDBManager().update_sector_stats(sector, year, generate_exp_sector_insights, generate_int_sector_insights, generate_exp_mit_sector_insights, generate_exp_int_mit_sector_insights, update_all)


def update_reporting_tables( sector, year: int, generate_exp_sector_insights: bool, generate_int_sector_insights: bool, generate_mit_sector_insights: bool, update_all: bool, keywords_only: bool):
    InsightGeneratorDBManager().update_reporting_tables(sector, year, generate_exp_sector_insights, generate_int_sector_insights, generate_mit_sector_insights, update_all, keywords_only)


def update_chart_tables(generate_top10_exposure_chart_data: bool, generate_triangulation_data: bool, generate_yoy_chart_data: bool):
    InsightGeneratorDBManager().update_chart_tables(generate_top10_exposure_chart_data, generate_triangulation_data, generate_yoy_chart_data)


def get_sector_list():
    return InsightGeneratorDBManager().get_sector_list()


def get_year_list():
    return InsightGeneratorDBManager().get_year_list()


# sector_list = get_sector_list('Test')
# print(sector_list)

# InsightGeneratorDBManager("Test").update_sector_stats(
#     'Mining and Metals(ICMM)', 2022)
