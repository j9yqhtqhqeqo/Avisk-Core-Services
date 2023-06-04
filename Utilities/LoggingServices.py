import datetime as dt


class logGenerator:
    pass

    def log_details(message: str, file_path=None):
        f_log = open(file_path, 'a')
        print(f'{dt.datetime.now()} : ' + {message})
        f_log.write(f'{dt.datetime.now()} : ' + {message})
        f_log.write('\n')
        f_log.flush()
        f_log.close()
