import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager

from Services.InsightGenerator import file_folder_keyWordSearchManager, PARM_STAGE1_FOLDER
from DBEntities.ProximityEntity import DocumentEntity
from multiprocessing import Process, Queue, Pool
import time
from DBEntities.LookupsDBManager import LookupsDBManager
import multiprocessing
from Utilities.Lookups import Lookups
from Utilities.MultiProcessing import get_process_buffer




def load_document_cache_for_exposure_pathway(database_context, validation_mode, queue: Queue, queue_size=Queue):
    exposure_document_list = InsightGeneratorDBManager(
        database_context).get_exp_pathway_document_list(validation_mode)
    for document in exposure_document_list:
        queue.put(document)

    queue_size.put(len(exposure_document_list))
    print('Documents Loaded for Exposure Pathway Keyword Search')

def process_next_unprocessed_exposure_document_list(batch_size, database_context, queue: Queue, batch_num, validation_mode ):
    Document_List = []
    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        Document_List.append(document)
        
    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER, database_context=database_context)
    
    key_word_search_mgr.generate_keyword_location_map_for_exposure_pathway(
        Document_List, batch_num, validation_mode)
    if(validation_mode):
        InsightGeneratorDBManager(database_context).update_validation_keywords_generated_status(Document_List, Lookups().Exposure_Pathway_Dictionary_Type,2)

def process_exposure_pathway_document_list(database_context, validation_mode = False):
    print("Creating Batches for Exposure Pathway Keyword Search -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_exposure_pathway,
                           args=(database_context, validation_mode, queue, queue_size,))
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
        l_dbmgr = LookupsDBManager(database_context=database_context)
        process_state = (l_dbmgr.get_exposure_pathway_search_status())
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_exposure_document_list,
                args=(batches[i], database_context, queue, i+1,validation_mode,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))
        else:
            print('Process Not in Run Stat - Exiting process_exposure_pathway_document_list')
            break

    cache_loader.join()
    for process in process_list:
        process.join()

    print('All documents processed:Check for documents failed keyword validation')


def load_document_cache_for_internalization(database_context, validation_mode, queue: Queue, queue_size=Queue):
    internalization_document_list = InsightGeneratorDBManager(
        database_context).get_internalization_document_list(validation_mode)
    for document in internalization_document_list:
        queue.put(document)

    queue_size.put(len(internalization_document_list))
    print('Documents Loaded for Internalization Keyword Search')

def process_next_unprocessed_internalization_document_list(batch_size, database_context, queue: Queue, batch_num, validation_mode):
    Document_List = []
    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        Document_List.append(document)
        
    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER, database_context=database_context)
    
    key_word_search_mgr.generate_keyword_location_map_for_internalization(
       Document_List, batch_num, validation_mode)
    if(validation_mode):
        InsightGeneratorDBManager(database_context).update_validation_keywords_generated_status(Document_List, Lookups().Internalization_Dictionary_Type,2)

def process_internalization_document_list(database_context, validation_mode = False):
    print("Creating Batches for Internalization Keyword Search - ")

    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_internalization,
                           args=(database_context, validation_mode, queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()

    batches = get_process_buffer(queue_size_int, io_bound=True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager(database_context=database_context)
        process_state = (l_dbmgr.get_exposure_pathway_search_status())
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_internalization_document_list,
                args=(batches[i], database_context, queue, i+1,validation_mode,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))
        else:
            print('Process Not in Run Stat - Exiting process_exposure_pathway_document_list')
            break

    cache_loader.join()
    for process in process_list:
        process.join()
    
    print('All documents processed:Check for documents failed keyword validation')


def load_document_cache_for_mitigation(database_context, validation_mode, queue_mit: Queue, queue_size_mit=Queue):
    mitigation_document_list = InsightGeneratorDBManager(
        database_context).get_mitigation_document_list(validation_mode)
    for document in mitigation_document_list:
        queue_mit.put(document)

    queue_size_mit.put(len(mitigation_document_list))
    print('Documents Loaded for Mitigation Keyword Search')
  
def process_next_unprocessed_mitigation_document_list(batch_size, database_context, queue: Queue, batch_num, validation_mode):
    Document_List = []

    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        Document_List.append(document)

    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER, database_context=database_context)
    
    key_word_search_mgr.generate_keyword_location_map_for_mitigation(
       Document_List, batch_num, validation_mode)
    if(validation_mode):
        InsightGeneratorDBManager(database_context).update_validation_keywords_generated_status(Document_List, Lookups().Mitigation_Dictionary_Type,2)

def process_mitigation_document_list(database_context, validation_mode = False):
    print("Creating Batches for Mitigation Keyword Search -")

    queue = Queue()
    queue_size = Queue()

    cache_loader = Process(target=load_document_cache_for_mitigation,
                           args=(database_context, validation_mode, queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()

    batches = get_process_buffer(queue_size_int,True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager(database_context=database_context)
        process_state = (l_dbmgr.get_exposure_pathway_search_status())
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_mitigation_document_list,
                args=(batches[i], database_context, queue, i+1,validation_mode,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))
        else:
            print('Process Not in Run Stat - Exiting process_exposure_pathway_document_list')
            break

    cache_loader.join()
    for process in process_list:
        process.join()
    
    print('All documents processed:Check for documents failed keyword validation')

def update_validation_completed_status(database_context):
    InsightGeneratorDBManager(
        database_context).update_validation_completed_status()


def update_sector_stats(database_context, sector, year: int, generate_exp_sector_insights: bool, generate_int_sector_insights: bool, generate_exp_mit_sector_insights: bool, generate_exp_int_mit_sector_insights: bool, update_all: bool):
    InsightGeneratorDBManager(
        database_context).update_sector_stats(sector, year, generate_exp_sector_insights, generate_int_sector_insights,generate_exp_mit_sector_insights, generate_exp_int_mit_sector_insights, update_all)


def update_reporting_tables(database_context, sector, year: int, generate_exp_sector_insights: bool, generate_int_sector_insights: bool, generate_mit_sector_insights: bool, update_all: bool, keywords_only:bool):
    InsightGeneratorDBManager(
        database_context).update_reporting_tables(sector, year, generate_exp_sector_insights, generate_int_sector_insights, generate_mit_sector_insights, update_all, keywords_only)


def update_chart_tables(database_context, generate_top10_exposure_chart_data: bool, generate_triangulation_data: bool, generate_yoy_chart_data:bool):
    InsightGeneratorDBManager(
        database_context).update_chart_tables(generate_top10_exposure_chart_data, generate_triangulation_data, generate_yoy_chart_data)



def get_sector_list(database_context):
    return InsightGeneratorDBManager(
        database_context).get_sector_list()


def get_year_list(database_context):
    return InsightGeneratorDBManager(
        database_context).get_year_list()
    

# sector_list = get_sector_list('Test')
# print(sector_list)

# InsightGeneratorDBManager("Test").update_sector_stats(
#     'Mining and Metals(ICMM)', 2022)
