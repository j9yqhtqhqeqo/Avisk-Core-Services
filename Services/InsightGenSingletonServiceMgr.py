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
from Utilities.Lookups import Lookups
from Services.InsightGenerator import Insight_Generator
from Services.InsightGenerator import triangulation_Insight_Generator
from Utilities.MultiProcessing import get_process_buffer




## EXPOSURE INSIGHTS
def load_document_cache_for_exposure_pathway( queue: Queue, queue_size=Queue):
    
    exposure_document_list = InsightGeneratorDBManager(
        ).get_unprocessed_document_items_for_insight_gen(dictionary_type=Lookups().Exposure_Pathway_Dictionary_Type)
    for document in exposure_document_list:
        queue.put(document)

    queue_size.put(len(exposure_document_list))
    print('Documents Loaded for Exposure Pathway Insight Generation')

def process_next_unprocessed_exposure_document_list(batch_size, queue: Queue, batch_num, validation_mode):
    exp_int_insght_generator = Insight_Generator()
    insight_generator_db_mgr = InsightGeneratorDBManager()

    document_count = 0
    document_list :any
    for i in range(batch_size):
        if (queue.empty()):
            break
        document_count = document_count + 1
        document: DocumentEntity = queue.get()
        document_keyword_list =  insight_generator_db_mgr.get_keyword_hits_for_insight_gen(Lookups().Exposure_Pathway_Dictionary_Type, document.document_id)
        doc_list = []
        doc_list.append(document)
        insight_generator_db_mgr.cleanup_insights_for_document(Lookups().Exposure_Pathway_Dictionary_Type,doc_list)
        exp_int_insght_generator.generate_insights_with_2_factors(
                Lookups().Exposure_Pathway_Dictionary_Type, document_keyword_list,batch_num=batch_num, year=document.year, document_id=document.document_id )
        print('Completed Insight Generation - Batch#:' + str(batch_num) +', Document:' +
                      str(document_count)+' of ' + str(batch_size))
                      
def batch_process_generate_insights_for_exposure( validation_mode = False):
    print("Creating Batches for Exposure Insight Generation -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_exposure_pathway,
                           args=( queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()
    batches = get_process_buffer(queue_size_int,io_bound=True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager()
        process_state = (l_dbmgr.get_insight_gen_status(Lookups().Exposure_Pathway_Dictionary_Type))
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_exposure_document_list,
                args=(batches[i], queue, i+1,validation_mode,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))

        else:
            print('Process Not in Run State - Exiting batch_process_generate_insights_for_exposure')
            break

    cache_loader.join()
    for process in process_list:
        process.join()
    
    print("All Batches processed successfully")

## INTERNALIZATION INSIGHTS
def load_document_cache_for_internalization( queue: Queue, queue_size=Queue):
    
    document_list = InsightGeneratorDBManager(
        ).get_unprocessed_document_items_for_insight_gen(dictionary_type=Lookups().Internalization_Dictionary_Type)
    for document in document_list:
        queue.put(document)

    queue_size.put(len(document_list))
    print('Documents Loaded for Internalization  Insight Generation')

def process_next_unprocessed_internalization_document_list(batch_size, queue: Queue, batch_num, validation_mode):
    exp_int_insght_generator = Insight_Generator()
    insight_generator_db_mgr = InsightGeneratorDBManager()

    document_count = 0
    document_list :any
    for i in range(batch_size):
        if (queue.empty()):
            break
        document_count = document_count + 1
        document: DocumentEntity = queue.get()
        document_keyword_list =  insight_generator_db_mgr.get_keyword_hits_for_insight_gen(Lookups().Internalization_Dictionary_Type, document.document_id)
        doc_list = []
        doc_list.append(document)
        insight_generator_db_mgr.cleanup_insights_for_document(
            Lookups().Internalization_Dictionary_Type, doc_list)
        exp_int_insght_generator.generate_insights_with_2_factors(
            Lookups().Internalization_Dictionary_Type, document_keyword_list, batch_num=batch_num, year=document.year, document_id=document.document_id)
        print('Completed Insight Generation - Batch#:' + str(batch_num) +', Document:' +
                      str(document_count)+' of ' + str(batch_size))
                      
def batch_process_generate_insights_for_internalization( validation_mode = False):
    print("Creating Batches for Internalization Insight Generation -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_internalization,
                           args=( queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()
    batches = get_process_buffer(queue_size_int,io_bound=True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager()
        process_state = (l_dbmgr.get_insight_gen_status(Lookups().Internalization_Dictionary_Type))
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_internalization_document_list,
                args=(batches[i], queue, i+1,validation_mode,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))

        else:
            print('Process Not in Run State - Exiting batch_process_generate_insights_for_exposure')
            break

    cache_loader.join()
    for process in process_list:
        process.join()
    
    print("All Batches processed successfully")

## EXPOSURE -> INTERNALIZATION

def load_document_cache_for_exposure_internalization( queue: Queue, queue_size=Queue):
    
    exposure_document_list = InsightGeneratorDBManager(
        ).get_exp_int_document_list()
    for document in exposure_document_list:
        queue.put(document)

    queue_size.put(len(exposure_document_list))
    print('Documents Loaded for Exposure ->Internalization Insight Generation')

def process_next_unprocessed_exp_int_document_list(batch_size, queue: Queue, batch_num):
    triangulation_insight_gen = triangulation_Insight_Generator()
    document_List = []

    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        document_List.append(document)
    triangulation_insight_gen.generate_exp_int_insights(document_List, batch_num)
                  
def batch_process_generate_insights_for_exposure_internalization():
    print("Creating Batches for Exposure ->Internalization Insight Generation -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_exposure_internalization,
                           args=( queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()
    batches = get_process_buffer(queue_size_int,io_bound=True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager()
        process_state = (l_dbmgr.get_insight_gen_status(Lookups().Exp_Int_Insight_Type))
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_exp_int_document_list,
                args=(batches[i], queue, i+1,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))

        else:
            print('Process Not in Run State - Exiting batch_process_generate_insights_for_exposure_internalization')
            break

    cache_loader.join()
    for process in process_list:
        process.join()
    
    print("All Batches processed successfully")


## EXPOSURE -> MITIGATION

def load_document_cache_for_exposure_mitigation_insights( queue: Queue, queue_size=Queue):
    
    exposure_mit_document_list = InsightGeneratorDBManager(
        ).get_exp_mitigation_document_list()
    for document in exposure_mit_document_list:
        queue.put(document)

    queue_size.put(len(exposure_mit_document_list))
    print('Documents Loaded for Exposure ->Mitigation Insight Generation')

def process_next_unprocessed_exp_mit_document_list(batch_size, queue: Queue, batch_num):
    triangulation_insight_gen = triangulation_Insight_Generator()
    document_List = []

    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        document_List.append(document)
    triangulation_insight_gen.generate_mitigation_exp_insights(document_List, batch_num)
                   
def batch_process_generate_insights_for_exposure_mitigation_insights():
    print("Creating Batches for Exposure ->Mitigation Insight Generation -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_exposure_mitigation_insights,
                           args=(queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()
    batches = get_process_buffer(queue_size_int,io_bound=True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager()
        process_state = (l_dbmgr.get_insight_gen_status(Lookups().Mitigation_Exp_Insight_Type))
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_exp_mit_document_list,
                args=(batches[i], queue, i+1,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))

        else:
            print('Process Not in Run State - Exiting batch_process_generate_insights_for_exposure_mitigation_insights')
            break

    cache_loader.join()
    for process in process_list:
        process.join()
    
    print("All Batches processed successfully")


## INTERNALIZATION -> MITIGATION

def load_document_cache_for_internalization_mitigation_insights(queue: Queue, queue_size=Queue):
    
    int_mit_document_list = InsightGeneratorDBManager(
        ).get_int_mitigation_document_list()
    for document in int_mit_document_list:
        queue.put(document)

    queue_size.put(len(int_mit_document_list))
    print('Documents Loaded for Internalization ->Mitigation Insight Generation')

def process_next_unprocessed_int_mit_document_list(batch_size,  queue: Queue, batch_num):
    triangulation_insight_gen = triangulation_Insight_Generator()
    document_List = []

    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        document_List.append(document)
    triangulation_insight_gen.generate_mitigation_int_insights(document_List, batch_num)
                   
def batch_process_generate_insights_for_internalization_mitigation_insights():
    print("Creating Batches for Internalization -> Mitigation Insight Generation -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_internalization_mitigation_insights,
                           args=( queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()
    batches = get_process_buffer(queue_size_int,io_bound=True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager()
        process_state = (l_dbmgr.get_insight_gen_status(Lookups().Mitigation_Int_Insight_Type))
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_int_mit_document_list,
                args=(batches[i], queue, i+1,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))

        else:
            print('Process Not in Run State - Exiting batch_process_generate_insights_for_internalization_mitigation_insights')
            break

    cache_loader.join()
    for process in process_list:
        process.join()
    
    print("All Batches processed successfully")


## EXPOSURE->INTERNALIZATION -> MITIGATION

def load_document_cache_for_exp_int_mitigation_insights( queue: Queue, queue_size=Queue):
    
    exp_int_mit_document_list = InsightGeneratorDBManager(
        ).get_mitigation_exp_int_document_list()
    for document in exp_int_mit_document_list:
        queue.put(document)

    queue_size.put(len(exp_int_mit_document_list))
    print('Documents Loaded for Exposure -> Internalization -> Mitigation Insight Generation')

def process_next_unprocessed_exp_int_mitigation_document_list(batch_size, queue: Queue, batch_num):
    triangulation_insight_gen = triangulation_Insight_Generator()
    document_List = []

    for i in range(batch_size):
        if (queue.empty()):
            break
        document: DocumentEntity = queue.get()
        document_List.append(document)
    triangulation_insight_gen.generate_mitigation_exp_int_insights(document_List, batch_num)
                   
def batch_process_generate_insights_for_exp_int_mitigation_insights():
    print("Creating Batches for Exposure->Internalization -> Mitigation Insight Generation -")
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache_for_exp_int_mitigation_insights,
                           args=( queue, queue_size,))
    cache_loader.start()

    queue_size_int = queue_size.get()
    batches = get_process_buffer(
        queue_size_int, io_bound=True)
    num_batches = len(batches)
    print("Number of Documents to Process:" + str(queue_size_int))
    print("Total Number of Batches:" + str(num_batches))

    process_list = []
    for i in range(num_batches):
        # Check if the batch is set to run, if not exit
        l_dbmgr = LookupsDBManager()
        process_state = (l_dbmgr.get_insight_gen_status(Lookups().Mitigation_Exp_Insight_Type))
        if(process_state == 'Run'):
            p = (Process(target=process_next_unprocessed_exp_int_mitigation_document_list,
                args=(batches[i], queue, i+1,)))
            p.start()
            process_list.append(p)
            print('Started Batch: ' + str(i+1))

        else:
            print('Process Not in Run State - Exiting batch_process_generate_insights_for_internalization_mitigation_insights')
            break

    cache_loader.join()
    for process in process_list:
        process.join()
    
    print("All Batches processed successfully")


# buffer = get_process_buffer(100, True)
# print(buffer)

# batch_process_generate_insights_for_internalization("Test")
# triangulation_insight_gen = triangulation_Insight_Generator("Development")

# exp_int_document_list = InsightGeneratorDBManager(
#         "Development").get_exp_int_document_list()
# triangulation_insight_gen.generate_exp_int_insights(exp_int_document_list,1)

# exp_int_mit_document_list = InsightGeneratorDBManager(
#         "Development").get_mitigation_exp_int_document_list()
# triangulation_insight_gen.generate_mitigation_exp_int_insights(exp_int_mit_document_list, 1)

