import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from multiprocessing import Process, Queue
import time
from Utilities.Lookups import Lookups
from DBEntities.SurrogateKeyManager import get_next_surrogate_key
import os


def get_next_guid(database_context):
    print('Getting Keys')
    print('PID:' + str(os.getpid()))
    print(get_next_surrogate_key(save_type=Lookups().Keyword_Hit_Save, database_context = database_context))

    # returned_key = get_next_surrogate_key(save_type=1000,database_context="Test")

if __name__ == "__main__":
    process_list = []
    for i in range(10):
        p = (Process(target=get_next_guid,
            args=("Test",)))
        p.start()
        process_list.append(p)

    for process in process_list:
        process.join()

