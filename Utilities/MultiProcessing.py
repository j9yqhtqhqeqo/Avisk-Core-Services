

my_dict = {'GAS':['GAS46', 'GAS35', 'NATURAL-GAS-ACTIVATED'],'ICE':['OPERATORS/LICENSEES', 'LICENSEE-SPECIFIC']}

for key, value in my_dict.items():
    for i in value:
        print(key+':'+i)

# from multiprocessing import Process
# import os

# def info(title):
#     print(title)
#     print('module name:', __name__)
#     print('parent process:', os.getppid())
#     print('process id:', os.getpid())

# def f(name):
#     info('function f')
#     print('hello', name)

# if __name__ == '__main__':
#     info('main line')
#     p = Process(target=f, args=('bob',))
#     p.start()
#     p.join()

# from multiprocessing import Process

# def f(name):
#     print('hello', name)

# if __name__ == '__main__':
#     p = Process(target=f, args=('bob',))
#     p.start()
#     p.join()

# from multiprocessing import Process, Manager

# def show_var(a, lock):
#     for x in range(10):
#         with lock:
#             print(a.value)

# def set_var(a, lock):
#     for x in range(10):
#         with lock:
#             a.value += 1

# if __name__ =="__main__":
#     with Manager() as manager:
#         a = manager.Value('i', 0)
#         lock = manager.Lock()

#         p1 = Process(target=show_var, args=(a, lock))
#         p2 = Process(target=set_var, args=(a, lock))

#         p1.start()
#         p2.start()

#         p1.join()
#         p2.join()