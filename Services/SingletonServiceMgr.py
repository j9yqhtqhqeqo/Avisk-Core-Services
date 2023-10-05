import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from DBEntities.InsightGeneratorDBManager import InsightGeneratorDBManager
import time
from multiprocessing import Process, Queue
from DBEntities.ProximityEntity import DocumentEntity

# internalization_document_list = InsightGeneratorDBManager("Test").get_internalization_document_list(validation_mode=True)
# mitigation_document_list = InsightGeneratorDBManager("Test").get_mitigation_document_list(validation_mode=True)


def load_document_cache(database_context,validation_mode, queue: Queue, queue_size=Queue):
    print('loading documents')
    exposure_document_list = InsightGeneratorDBManager(database_context).get_exp_pathway_document_list(validation_mode)
    for document in exposure_document_list:
        queue.put(document)
    
    queue_size.put(len(exposure_document_list))
    print('Documents Loaded for EXP')


def get_next_unprocessed_exposure_document(queue:Queue):
    document: DocumentEntity = queue.get()
    print("Document Retrived:"+ str(document.document_name))
    # time.sleep(5)

# def get_next_unprocessed_mitigation_document_list():
#     print("Original INT Doclist length:"+ str(len(internalization_document_list)))


# def get_next_unprocessed_mitigation_document_list():
#     print("Original Mitigation Doclist length:"+ str(len(mitigation_document_list)))

# defget_next_unprocessed_exposure_document_list("Test",True)
if __name__ == '__main__':
    queue = Queue()
    queue_size = Queue()
    cache_loader = Process(target=load_document_cache, args=("Test",False,queue, queue_size,))
    cache_loader.start()
    cache_loader.join()

    queue_size_int = queue_size.get()
    print("Items retrived total:"+ str(queue_size_int))
    process_list =[]
    for i in range(queue_size_int):
        p = (Process(target=get_next_unprocessed_exposure_document, args=(queue,)))
        print("Process ID:"+ str(p.pid))
        p.start()
        process_list.append(p)
    for process in process_list:
        process.join()
    print("Graceful exit")

    # p1.start()
    # p2 = Process(target=get_next_unprocessed_exposure_document, args=(queue,))
    # p2.start()
    # p1.join()
    # p2.join()