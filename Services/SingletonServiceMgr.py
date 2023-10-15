import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from Services.InsightGenerator import file_folder_keyWordSearchManager, PARM_STAGE1_FOLDER
from DBEntities.ProximityEntity import DocumentEntity
from multiprocessing import Process, Queue, Pool
import time
from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager
from DBEntities.LookupsDBManager import LookupsDBManager
import multiprocessing
from Utilities.Lookups import Lookups



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

def load_document_cache_for_mitigation(database_context, validation_mode, queue_mit: Queue, queue_size_mit=Queue):
    mitigation_document_list = InsightGeneratorDBManager(
        database_context).get_mitigation_document_list(validation_mode)
    for document in mitigation_document_list:
        queue_mit.put(document)

    queue_size_mit.put(len(mitigation_document_list))
    print('Documents Loaded for Mitigation Keyword Search')

def process_next_unprocessed_exposure_document_list(batch_size, database_context, queue: Queue, batch_num, validation_mode):
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
    

def pool_process_next_unprocessed_internalization_document_list(database_context, document_num,total_documents, validation_mode):
    global queue

    Document_List = []
   
    if (queue.empty()):
        return
    document: DocumentEntity = queue.get()
    Document_List.append(document)

    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER, database_context=database_context)
    
    key_word_search_mgr.generate_keyword_location_map_for_internalization(
        Document_List, document_num,total_documents,validation_mode)
    if(validation_mode):
        InsightGeneratorDBManager(database_context).update_validation_keywords_generated_status(Document_List, Lookups().Internalization_Dictionary_Type,2)
    
def pool_process_next_unprocessed_mitigation_document_list(database_context, document_num,total_documents, validation_mode):
    global queue_mit
    Document_List = []

    if (queue_mit.empty()):
        return
    document: DocumentEntity = queue.get()
    Document_List.append(document)

    key_word_search_mgr = file_folder_keyWordSearchManager(
        folder_path=PARM_STAGE1_FOLDER, database_context=database_context)
    
    key_word_search_mgr.generate_keyword_location_map_for_mitigation(
        Document_List,document_num,total_documents,validation_mode)
    if(validation_mode):
        InsightGeneratorDBManager(database_context).update_validation_keywords_generated_status(Document_List, Lookups().Mitigation_Dictionary_Type,2)


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

def process_exposure_pathway_document_list(database_context, validation_mode = False):
    print("Creating Batches for Exposure Pathway Keyword Search -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_exposure_pathway,
                           args=(database_context, validation_mode, queue, queue_size,))
    cache_loader.start()
    # cache_loader.join()

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
    
    print("All Batches processed successfully")

def pool_process_internalization_document_list(database_context, validation_mode = False):
    print("Creating Batches for Internalization Keyword Search using pool process manager - ")

    multiprocessing.set_start_method("fork")
    global queue
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_internalization,
                           args=(database_context, validation_mode, queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()

    print("Number of Documents to Process:" + str(queue_size_int))

    pool_mgr = Pool(processes=multiprocessing.cpu_count())
    for i in range(queue_size_int):
        pool_mgr.starmap_async(process_next_unprocessed_internalization_document_list,
                [( database_context, i+1,queue_size_int,validation_mode)])
        
    cache_loader.join()
    
    print("Batch Processing Started")
    return queue_size_int

def process_internalization_document_list(database_context, validation_mode = False):
    print("Creating Batches for Internalization Keyword Search - ")

    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_internalization,
                           args=(database_context, validation_mode, queue, queue_size,))
    cache_loader.start()

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
    
    print("All Batches processed successfully")

def pool_process_mitigation_document_list(database_context, validation_mode = False):
    print("Creating Batches for Mitigation Keyword Search -")

    multiprocessing.set_start_method("spawn")
    global queue_mit

    queue_mit = Queue()
    queue_size_mit = Queue()
    cache_loader = Process(target=load_document_cache_for_mitigation,
                           args=(database_context, validation_mode, queue_mit, queue_size_mit,))
    cache_loader.start()

    queue_size_int = queue_size_mit.get()
    print("Number of Documents to Process:" + str(queue_size_int))
    pool_mgr = Pool(processes=multiprocessing.cpu_count())

    for i in range(queue_size_int):
          pool_mgr.starmap_async(process_next_unprocessed_mitigation_document_list,
                [( database_context, i+1,queue_size_int,validation_mode)])
          
    # cache_loader.join()
    print("Batch Processing Started")
    return queue_size_int

def process_mitigation_document_list(database_context, validation_mode = False):
    print("Creating Batches for Mitigation Keyword Search -")

    queue = Queue()
    queue_size = Queue()

    cache_loader = Process(target=load_document_cache_for_mitigation,
                           args=(database_context, validation_mode, queue, queue_size,))
    cache_loader.start()

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
    
    print("All Batches processed successfully")

def get_process_buffer(queue_length:int):

    process_count = multiprocessing.cpu_count()
    buffer =[]
    if(queue_length >= 10):
        buffer =[0]*process_count
    else:
        for i in range(queue_length):
            # buffer[i] = 0
            buffer.append(0)

    for i in range(queue_length):
        j = i % process_count
        buffer[j] = buffer[j] + 1
    return buffer

def update_validation_completed_status(database_context):
    InsightGeneratorDBManager(
        database_context).update_validation_completed_status()

def test_database_update(database_context, validation_mode):
    exposure_document_list = InsightGeneratorDBManager(
        database_context).get_exp_pathway_document_list(validation_mode)
   
    # key_word_search_mgr = file_folder_keyWordSearchManager(
    #     folder_path=PARM_STAGE1_FOLDER, database_context=database_context)
   
    if(validation_mode):
        InsightGeneratorDBManager(database_context).update_validation_keywords_generated_status(exposure_document_list, Lookups().Exposure_Pathway_Dictionary_Type,2)

# test_database_update("Development",True)