from ftplib import FTP
import win32file
import win32con
import datetime
import time
import os
import sys
import sqlite3
import zipfile
import fnmatch
import win32gui
import shutil
# Если нет базы данных - создаем пустую
if not os.path.exists('ftp.db'):
    conn1 = sqlite3.connect('ftp.db')
    cur1 = conn1.cursor()
    query1 = "CREATE TABLE task_log(task_name TEXT, date REAL, action TEXT)"
    cur1.execute(query1)
    conn1.commit()

    query1 = """CREATE TABLE backup_tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, backup_list TEXT, folder TEXT, 
    zip_name TEXT, time TEXT, last_sync TEXT, is_run INTEGER, status INTEGER, run_after TEXT, need_run_after INTEGER)"""
    cur1.execute(query1)
    conn1.commit()

    query1 = """CREATE TABLE sync_tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, folder1 TEXT, mask TEXT, 
    ftp_adr TEXT, ftp_port TEXT, ftp_login TEXT, ftp_pass TEXT, ftp_folder TEXT, 
    sync_direction INTEGER, scheduler_type INTEGER, time TEXT, last_sync TEXT, is_run INTEGER, status INTEGER)"""
    cur1.execute(query1)
    conn1.commit()
    conn1.close()

if not os.path.exists('settings.ini'):
    with open('settings.ini', 'w') as inifile:
        inifile.write('ftp_address,user,password,ftp_folder')

with open('settings.ini', 'r') as inifile:
    ftp_path = inifile.read().split(',')

data_conn = sqlite3.connect('ftp.db')
data_cur = data_conn.cursor()

# начальное обнуление выполненых задач (на случай некорректного завершения роботы)
q = "UPDATE sync_tasks SET is_run=0, status=0"
data_cur.execute(q)
q = "UPDATE backup_tasks SET is_run=0, status=0"
data_cur.execute(q)
data_conn.commit()

stop_task = []                  # для остановки задач
update_task = []                # для обновления задачи
control_threads = {}


class StopTask(Exception):
    pass


# возвращает время следующего запуска для задач, выполняемых раз в сутки
def get_next_time(run_time):
    time_now = datetime.datetime.now()
    delay_1 = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
    delay_2 = int(run_time[0:2]) * 3600 + int(run_time[3:5]) * 60 + int(run_time[6:8])
    day = datetime.datetime.now()
    if delay_1 > delay_2:  # добавляем 1 день, если время выполнения меньше текущего времени
        day += datetime.timedelta(1)
    next_time = datetime.datetime(day.year, day.month, day.day, int(run_time[0:2]), int(run_time[3:5]),
                                  int(run_time[6:8]))
    return next_time


# Запись в лог
def write_to_log(task_name, text):
    conn = sqlite3.connect('ftp.db')
    cur = conn.cursor()
    query = "INSERT INTO task_log(task_name, date, action) VALUES('" + task_name + "', " + str(time.time()) + \
            ", '" + text + "')"
    try:
        cur.execute(query)
        conn.commit()
    except:
        pass


# Очистка логов старше 20 дней
def clear_old_log():
    conn = sqlite3.connect('ftp.db')
    cur = conn.cursor()
    clear_time = int(time.time()) - 20*24*60*60
    query = "DELETE FROM task_log WHERE date<" + str(clear_time)
    try:
        cur.execute(query)
        conn.commit()
    except:
        pass
    conn.close()


# Очистка логов для конкретной задачи (оставляем 500 записей)
def clear_task_log(task_name):
    conn = sqlite3.connect('ftp.db')
    cur = conn.cursor()
    query = "SELECT * FROM task_log WHERE task_name='" + task_name + "' ORDER BY date ASC"
    cur.execute(query)
    logs = cur.fetchall()
    if logs and len(logs) > 600:
        clear_time = logs[-500][1]
        query = "DELETE FROM task_log WHERE date<" + str(clear_time)
        try:
            cur.execute(query)
            conn.commit()
        except:
            pass
    conn.close()


def control_thread_timeout():
    for task in dict.keys(control_threads):
        if control_threads[task][1] + 3600 < int(time.time()):          # Если запущено больше часа
            control_threads[task][0].terminate()                        # Остановить
            write_to_log(task, 'Завершаем аварийно по истечении таймаута ' + task)


# изменяет дату создания и изменения файла
def change_file_creation_time(fname, newtime):
    winfile = win32file.CreateFile(fname, win32con.GENERIC_WRITE,
                                   win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                                   None, win32con.OPEN_EXISTING, win32con.FILE_ATTRIBUTE_NORMAL, None)

    win32file.SetFileTime(winfile, newtime, newtime, newtime)
    winfile.close()


def sync_file_from_ftp(ftp_conn, file, dest_folder, ftp_date, name_):
    write_to_log(name_, 'Синхронизируем файл ' + file)
    with open(dest_folder + file, 'wb') as local:
        ftp_conn.retrbinary('RETR ' + file, local.write, 1024)
    ftime = datetime.datetime.fromtimestamp(ftp_date)
    change_file_creation_time(dest_folder+file, ftime)              # изменить дату создания локального файла


def sync_folders_from_ftp(ftp_conn, dest_folder, folder, name_, mask):
    ftp_conn.cwd(folder)
    write_to_log(name_, 'Переходим в папку ' + folder)
    lines = []
    ftp_conn.dir(lines.append)
    for line in lines:
        # Проверка не нужно ли остановить задачу
        if len(stop_task) > 0:
            stop_task.clear()
            raise StopTask()    # Остановить задачу
        parsed = line.split()
        permiss = parsed[0]
        fname = ' '.join(parsed[8:])
        if fname in ('.', '..'):                                    # пропускаем
            continue
        elif permiss[0] != 'd':                                     # файл: синхронизировать
            # проверка на необходимость синхронизации (дата создания)
            need_sync = False
            # получить дату изменения на FTP и преобразовать
            ctime = ftp_conn.sendcmd('MDTM ' + fname)
            ftp_date = time.mktime(datetime.datetime.strptime(ctime[4:], "%Y%m%d%H%M%S").timetuple()) + 7200

            if not os.path.isfile(dest_folder + fname):                 # если файла нет то синхронизируем
                need_sync = True
            else:
                if ftp_date > os.path.getmtime(dest_folder + fname):    # если файл на фтп новее синхронизируем
                    need_sync = True
            if need_sync:
                if fnmatch.fnmatch(fname, mask):
                    sync_file_from_ftp(ftp_conn, fname, dest_folder, ftp_date, name_)
        else:                                                           # каталог: копировать рекурсивно
            if not os.path.isdir(dest_folder + fname):
                os.mkdir(dest_folder + fname)
            sync_folders_from_ftp(ftp_conn, dest_folder + fname + '\\', fname, name_, mask)
            write_to_log(name_, 'Выходим из папки ' + fname)
            ftp_conn.cwd('..')


def sync_from_ftp(ftp, user, folder, dest_folder, name_, mask):
    errors = False
    stopped = False
    try:
        write_to_log(name_, 'Подключаемся к ФТП ' + ftp)
        ftp_conn = FTP(ftp)
        write_to_log(name_, 'Успешное подключение')
        write_to_log(name_, 'Пользователь: ' + user[0])
        ftp_conn.login(*user)
        write_to_log(name_, 'Успешная аутентификация')
        ftp_conn.encoding = 'cp1251'
        sync_folders_from_ftp(ftp_conn, dest_folder, folder, name_, mask)
        ftp_conn.quit()
    except StopTask:
        stopped = True
        errors = True
    except:
        errors = True
    # записываем состояние выполнения
    time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y %H:%M:%S')
    conn = sqlite3.connect('ftp.db')
    cur = conn.cursor()
    if not errors:
        query = "UPDATE sync_tasks SET is_run=0, last_sync='" + time_now + "', status=2 WHERE name='" + str(name_) + "'"
        write_to_log(name_, 'Закончили ' + name_)
    elif not stopped:
        query = "UPDATE sync_tasks SET is_run=0, last_sync='" + time_now + "', status=3 WHERE name='" + str(name_) + "'"
        write_to_log(name_, 'Закончили ' + name_ + ' с ошибками.')
    else:
        query = "UPDATE sync_tasks SET is_run=0, last_sync='" + time_now + "', status=4 WHERE name='" + str(name_) + "'"
        write_to_log(name_, 'Задача ' + name_ + ' остановлена вручную.')
    try:
        cur.execute(query)
        conn.commit()
    except:
        pass
    conn.close()
    try:
        control_threads.pop(name_)
    except:
        pass


def sync_file_to_ftp(ftp_conn, file, dest_folder, name_):
    write_to_log(name_, 'Синхронизируем файл ' + file)
    with open(dest_folder + file, 'rb') as local:
        try:
            ftp_conn.storbinary('STOR ' + file, local, 1024)
        except:
            write_to_log(name_, 'Ошибка синхронизации. Пропускаем файл ' + file)


def sync_folders_to_ftp(ftp_conn, dest_folder, folder, name_, mask):
    ftp_conn.cwd(folder)
    write_to_log(name_, 'Переходим в папку ' + folder)
    localfiles = os.listdir(dest_folder)
    for localname in localfiles:
        # Проверка не нужно ли остановить задачу
        if len(stop_task) > 0:
            stop_task.clear()
            raise StopTask()  # Остановить задачу
        localpath = os.path.join(dest_folder, localname)
        if not os.path.isdir(localpath):                                # файл: синхронизировать
            # проверка на необходимость синхронизации (дата создания)
            need_sync = False
            # получить дату изменения на FTP и преобразовать
            try:
                ctime = ftp_conn.sendcmd('MDTM ' + localname)
                ftp_date = time.mktime(datetime.datetime.strptime(ctime[4:], "%Y%m%d%H%M%S").timetuple()) + 7200
                if ftp_date < os.path.getmtime(localpath):              # если файл на фтп новее синхронизируем
                    need_sync = True
            except:                                                     # файла не существует
                need_sync = True
            if need_sync:
                if fnmatch.fnmatch(localname, mask):
                    sync_file_to_ftp(ftp_conn, localname, dest_folder, name_)
        else:                                                           # каталог: копировать рекурсивно
            try:
                ftp_conn.mkd(localname)
            except:
                pass
            sync_folders_to_ftp(ftp_conn, dest_folder + localname + '\\', localname, name_, mask)
            write_to_log(name_, 'Выходим из папки ' + localname)
            ftp_conn.cwd('..')


def sync_to_ftp(ftp, user, folder, dest_folder, name_, mask):
    errors = False
    stopped = False
    try:
        write_to_log(name_, 'Подключаемся к ФТП ' + ftp)
        ftp_conn = FTP(ftp)
        write_to_log(name_, 'Успешное подключение')
        write_to_log(name_, 'Пользователь: ' + user[0])
        ftp_conn.login(*user)
        write_to_log(name_, 'Успешная аутентификация')
        ftp_conn.encoding = 'cp1251'
        sync_folders_to_ftp(ftp_conn, dest_folder, folder, name_, mask)
        ftp_conn.quit()
    except StopTask:
        stopped = True
        errors = True
    except:
        errors = True
    # записываем состояние выполнения
    time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y %H:%M:%S')
    conn = sqlite3.connect('ftp.db')
    cur = conn.cursor()
    if not errors:
        query = "UPDATE sync_tasks SET is_run=0, last_sync='" + time_now + "', status=2 WHERE name='" + str(name_) + "'"
        write_to_log(name_, 'Закончили ' + name_)
    elif not stopped:
        query = "UPDATE sync_tasks SET is_run=0, last_sync='" + time_now + "', status=3 WHERE name='" + str(name_) + "'"
        write_to_log(name_, 'Закончили ' + name_ + 'с ошибками.')
    else:
        query = "UPDATE sync_tasks SET is_run=0, last_sync='" + time_now + "', status=4 WHERE name='" + str(name_) + "'"
        write_to_log(name_, 'Задача ' + name_ + ' остановлена вручную.')
    try:
        cur.execute(query)
        conn.commit()
    except:
        pass
    conn.close()
    try:
        control_threads.pop(name_)
    except:
        pass


def backup_file(file_name, folder, zip_name, name_):
    write_to_log(name_, 'Добавляем в архив: ' + folder + os.path.basename(file_name))
    with zipfile.ZipFile(zip_name, 'a', zipfile.ZIP_DEFLATED, True) as myzip:
        myzip.write(file_name, folder + os.path.basename(file_name))


def backup_folders(folder_name, folder, zip_name, name_):
    files = os.listdir(folder_name)
    for file_name in files:
        # Проверка не нужно ли остановить задачу
        if len(stop_task) > 0:
            stop_task.clear()
            raise StopTask()  # Остановить задачу
        file_path = os.path.join(folder_name, file_name)
        if not os.path.isdir(file_path):                # Если файл
            backup_file(file_path, folder + folder_name.split('\\')[-1] + '\\', zip_name, name_)
        else:                                           # Если папка - обойти рекурсивно
            backup_folders(file_path, folder + folder_name.split('\\')[-1] + '\\', zip_name, name_)


def backup(backup_list, zip_name, backup_folder, run_after, name_):
    errors = False
    stopped = False
    try:
        write_to_log(name_, 'Создаем архив: ' + zip_name)
        for item in backup_list:
            if os.path.isfile(item):
                backup_file(item, '', 'D:\\' + zip_name, name_)
            else:
                backup_folders(item, '', 'D:\\' + zip_name, name_)
    except StopTask:
        stopped = True
        errors = True
    except:
        errors = True
    # записываем состояние выполнения
    time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%d.%m.%Y %H:%M:%S')
    conn = sqlite3.connect('ftp.db')
    cur = conn.cursor()
    if not errors:
        query = "UPDATE backup_tasks SET is_run=0, last_sync='" + time_now + "', status=2 WHERE name='" + str(
                name_) + "'"
        write_to_log(name_, 'Перемещаем архив ' + zip_name + ' в папку: ' + backup_folder)
        try:
            shutil.copy2('D:\\' + zip_name, backup_folder + '\\' + zip_name)
            write_to_log(name_, 'Успешное перемещение архива ' + zip_name)
        except:
            write_to_log(name_, 'Не удалось переместить архив ' + zip_name)
        if run_after:
            write_to_log(name_, 'Запускаем: ' + run_after)
            try:
                os.startfile(run_after)
            except:
                pass

        write_to_log(name_, 'Закончили ' + name_)
    elif not stopped:
        query = "UPDATE backup_tasks SET is_run=0, last_sync='" + time_now + "', status=3 WHERE name='" + str(
                name_) + "'"
        write_to_log(name_, 'Закончили ' + name_ + 'с ошибками.')
    else:
        query = "UPDATE backup_tasks SET is_run=0, last_sync='" + time_now + "', status=4 WHERE name='" + str(
                name_) + "'"
        write_to_log(name_, 'Задача ' + name_ + ' остановлена вручную.')
    os.remove('D:\\' + zip_name)
    try:
        cur.execute(query)
        conn.commit()
    except:
        pass
    conn.close()
    try:
        control_threads.pop(name_)
    except:
        pass


if __name__ == "__main__":
    pass
