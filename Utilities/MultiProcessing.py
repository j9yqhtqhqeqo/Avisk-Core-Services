import multiprocessing
from multiprocessing import Process, Queue


##  COMMON SERVICE
def get_process_buffer(queue_length:int, io_bound = False):

    processor_count = multiprocessing.cpu_count()
    if(io_bound):
                default_process_count = processor_count * 5
                if(queue_length < default_process_count):
                       process_count = queue_length
                else:
                       process_count = default_process_count
    else:
                process_count = processor_count
    buffer =[]
    
    if(queue_length >= 10):
            buffer =[0]*(process_count)
    else:
        for i in range(queue_length):
            buffer.append(0)

    for i in range(queue_length):
        j = i % process_count
        buffer[j] = buffer[j] + 1
    return buffer
