import datetime as dt


class logGenerator:
    def __init__(self, file_path) -> None:
        self.file_path = file_path

    def log_details(self,message: str, stamp_date_time = True):
        f_log = open(self.file_path, 'a')
        if(stamp_date_time):
            f_log.write(f'{dt.datetime.now()} : {message}')
        else:
            f_log.write(f'{message}')
        f_log.write('\n')
        f_log.flush()
        f_log.close()
