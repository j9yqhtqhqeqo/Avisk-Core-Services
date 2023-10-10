import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from Services.InsightGenerator import file_folder_keyWordSearchManager, PARM_STAGE1_FOLDER
from DBEntities.ProximityEntity import DocumentEntity
from multiprocessing import Process, Queue
import time
from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager
from DBEntities.LookupsDBManager import LookupsDBManager
import multiprocessing


def load_document_cache_for_exposure_pathway(database_context, validation_mode, queue: Queue, queue_size=Queue):
    exposure_document_list = InsightGeneratorDBManager(
        database_context).get_exp_pathway_document_list(validation_mode)
    for document in exposure_document_list:
        queue.put(document)

    queue_size.put(len(exposure_document_list))
    print('Documents Loaded for Exposure Pathway Keyword Search')

def load_document_cache_for_internalization(database_context, validation_mode, queue: Queue, queue_size=Queue):
    internalization_document_list = InsightGeneratorDBManager(
        database_context).get_internalization_document_list(validation_mode)
    for document in internalization_document_list:
        queue.put(document)

    queue_size.put(len(internalization_document_list))
    print('Documents Loaded for Internalization Keyword Search')

def load_document_cache_for_mitigation(database_context, validation_mode, queue: Queue, queue_size=Queue):
    mitigation_document_list = InsightGeneratorDBManager(
        database_context).get_mitigation_document_list(validation_mode)
    for document in mitigation_document_list:
        queue.put(document)

    queue_size.put(len(mitigation_document_list))
    print('Documents Loaded for Mitigation Keyword Search')


def process_next_unprocessed_exposure_document_list(batch_size, database_context, queue: Queue, batch_num):
    Document_List = []
    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        Document_List.append(document)
        
    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER, database_context=database_context)
    

    key_word_search_mgr.generate_keyword_location_map_for_exposure_pathway(
        Document_List, batch_num)

def process_next_unprocessed_internalization_document_list(batch_size, database_context, queue: Queue, batch_num):
    Document_List = []
    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        Document_List.append(document)

    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER, database_context=database_context)
    
    key_word_search_mgr.generate_keyword_location_map_for_internalization(
        Document_List, batch_num)

def process_next_unprocessed_mitigation_document_list(batch_size, database_context, queue: Queue, batch_num):
    Document_List = []

    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        Document_List.append(document)

    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER, database_context=database_context)
    
    key_word_search_mgr.generate_keyword_location_map_for_mitigation(
        Document_List, batch_num)

def process_exposure_pathway_document_list(database_context):
    print("Creating Batches for Exposure Pathway Keyword Search -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_exposure_pathway,
                           args=(database_context, False, queue, queue_size,))
    cache_loader.start()
    cache_loader.join()

    queue_size_int = queue_size.get()
    batches = get_process_buffer(queue_size_int)
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
                args=(batches[i], database_context, queue, i+1,)))
            p.start()
            process_list.append(p)
        else:
            print('Process Not in Run Stat - Exiting process_exposure_pathway_document_list')
            break

    for process in process_list:
        process.join()
    
    print("All Batches processed successfully")

def process_internalization_document_list(database_context):
    print("Creating Batches for Internalization Keyword Search -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_internalization,
                           args=(database_context, False, queue, queue_size,))
    cache_loader.start()
    cache_loader.join()

    queue_size_int = queue_size.get()
    batches = get_process_buffer(queue_size_int)
    num_batches = len(batches)

    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager(database_context=database_context)
        process_state = (l_dbmgr.get_internalization_search_status())
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_internalization_document_list,
                args=(batches[i], database_context, queue, i+1,)))
            p.start()
            process_list.append(p)
        else:
            print('Process Not in Run Stat - Exiting process_internalization_document_list')
            break

    for process in process_list:
        process.join()
    
    print("All Batches processed successfully")

def process_mitigation_document_list(database_context):
    print("Creating Batches for Mitigation Keyword Search -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_mitigation,
                           args=(database_context, False, queue, queue_size,))
    cache_loader.start()
    cache_loader.join()

    queue_size_int = queue_size.get()
    batches = get_process_buffer(queue_size_int)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager(database_context=database_context)
        process_state = (l_dbmgr.get_mitigation_search_status())
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_mitigation_document_list,
                args=(batches[i], database_context, queue, i+1,)))
            p.start()
            process_list.append(p)
        else:
            print('Process Not in Run Status - Exiting process_mitigation_document_list')
            break

    for process in process_list:
        process.join()
    
    print("All Batches processed successfully")

def get_process_buffer(queue_length:int):

    process_count = multiprocessing.cpu_count()

    buffer =[0]*process_count

    for i in range(queue_length):
        j = i % process_count
        buffer[j] = buffer[j] + 1
    return buffer

# process_exposure_pathway_document_list("Development")