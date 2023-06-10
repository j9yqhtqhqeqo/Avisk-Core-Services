import datetime as dt


class logGenerator:
    def __init__(self, file_path) -> None:
        self.file_path = file_path

    def log_details(self,message: str):
        f_log = open(self.file_path, 'a')
        f_log.write(f'{dt.datetime.now()} : {message}')
        f_log.write('\n')
        f_log.flush()
        f_log.close()
