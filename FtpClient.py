from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from fync import *
from addedit import *
import threading
from threading2 import Thread

global toolbar, task_tray_menu
clear_old_log()


# Груповая установка статусов для действий
def groupSetEnabled(items, status):
    for item in items:
        item.setEnabled(status)


class BackupTask:

    def __init__(self, backup_data, time_left):
        self.timer = QTimer()
        self.backup_data = backup_data
        self.time_left = time_left
        self.initUI()

    def initUI(self):
        self.timer.timeout.connect(self.timeout_timer)
        # сюда дописать вычисление времени таймера
        self.timer.start(self.time_left*1000)

    def timeout_timer(self):
        query = "SELECT is_run FROM backup_tasks WHERE id=" + str(self.backup_data[0])
        data_cur.execute(query)
        is_run = data_cur.fetchall()
        if not is_run[0][0]:  # Проверяем не запущена ли уже задача
            # Ставим метку о запуске задачи
            query = "UPDATE backup_tasks SET is_run=1, status=1 WHERE id=" + str(self.backup_data[0])
            try:
                data_cur.execute(query)
                data_conn.commit()
            except:
                pass
            write_to_log(self.backup_data[1], 'Начинаем ' + self.backup_data[1])
            backup_list = self.backup_data[2].split('|')
            if self.backup_data[10]:
                run_after = self.backup_data[9]
            else:
                run_after = ''
            thr = threading.Thread(target=backup,
                                   args=(backup_list, self.backup_data[4], self.backup_data[3], run_after,
                                         self.backup_data[1]))
            thr.start()
            control_threads[self.backup_data[1]] = [thr, int(time.time())]
        # Высчитать оставшееся время и установить таймер
        next_time = get_next_time(self.backup_data[5])
        self.timer.setInterval(int(time.mktime(next_time.timetuple()) - time.time()) * 1000)

    def run_now(self):
        self.timer.setInterval(1)


class SyncTask:

    def __init__(self, sync_data):
        self.timer = QTimer()
        self.sync_data = sync_data
        self.delay = 0
        self.initUI()

    def initUI(self):
        clear_task_log(self.sync_data[1])
        # интервал синхронизации
        self.timer.timeout.connect(self.timeout_timer)
        if self.sync_data[10]:
            self.delay = self.sync_data[11].split(':')
            self.delay = int(self.delay[2]) + int(self.delay[1]) * 60 + int(self.delay[0]) * 3600
        else:                               # синхронизация раз в сутки
            next_time = get_next_time(self.sync_data[11])
            self.delay = int(time.mktime(next_time.timetuple()) - time.time())
        self.timer.start(self.delay*1000)

    " что делать когда закончится время "
    def timeout_timer(self):
        query = "SELECT is_run FROM sync_tasks WHERE id=" + str(self.sync_data[0])
        data_cur.execute(query)
        is_run = data_cur.fetchall()
        if not is_run[0][0]:                # Проверяем не запущена ли уже задача
            # Ставим метку о запуске задачи
            query = "UPDATE sync_tasks SET is_run=1, status=1 WHERE id=" + str(self.sync_data[0])
            try:
                data_cur.execute(query)
                data_conn.commit()
            except:
                pass
            write_to_log(self.sync_data[1], 'Начинаем ' + self.sync_data[1])
            if self.sync_data[9]:
                thr = Thread(target=sync_from_ftp,
                                       args=(self.sync_data[4], (self.sync_data[6], self.sync_data[7]),
                                             self.sync_data[8], self.sync_data[2], self.sync_data[1],
                                             self.sync_data[3]))
            else:
                thr = Thread(target=sync_to_ftp,
                                       args=(self.sync_data[4], (self.sync_data[6], self.sync_data[7]),
                                             self.sync_data[8], self.sync_data[2], self.sync_data[1],
                                             self.sync_data[3]))
            thr.start()
            control_threads[self.sync_data[1]] = [thr, int(time.time())]
        if self.sync_data[10]:
            self.timer.setInterval(self.delay * 1000)
        else:
            next_time = get_next_time(self.sync_data[11])
            self.timer.setInterval(int(time.mktime(next_time.timetuple()) - time.time())*1000)

    def run_now(self):
        self.timer.setInterval(1)


"""
    Отображает список подключений
"""


class TaskList(QTreeView):

    def __init__(self):
        super().__init__()
        self.tasks = {}
        self.model = QStandardItemModel(self)
        self.control_timer = QTimer()
        self.update_timer = QTimer()
        self.clear_log_timer = QTimer()
        self.fastrun_timer = QTimer()
        self.thread_control = QTimer()
        self.menu = QMenu(self)
        self.selected_name = ''
        self.last_update = 0
        self.initUI()

    " конструктор отображения "
    def initUI(self):
        # настройка отображения списка
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setIndentation(0)
        self.setSortingEnabled(True)
        self.setAllColumnsShowFocus(True)
        self.setAlternatingRowColors(True)
        # установка действий
        self.setActions()

        # установка модели и начальное заполнение таблицы
        self.setModel(self.model)
        self.setData()
        # Установка таймера контроля состояния
        self.control_timer.timeout.connect(self.run_timer)
        self.control_timer.start(500)
        # Установка таймера обновления логов
        self.update_timer.timeout.connect(self.update_timer_timeout)
        self.update_timer.start(500)
        # Установка таймера Очистки старых логов
        self.clear_log_timer.timeout.connect(self.clearlog_timer_timeout)
        self.clear_log_timer.start(60*60*1000)      # Раз в час
        # Установка таймера проверки зависания потоков
        self.thread_control.timeout.connect(control_thread_timeout)
        self.thread_control.start(60*1000)
        # Установка таймера для fastrun
        self.fastrun_timer.timeout.connect(self.fastrun_timer_timeout)
        self.fastrun_timer.start(5000)
        # контекстное меню
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.myMenu)

    " Заполнение списка задач "
    def setData(self):
        global task_tray_menu, update_task
        task_tray_menu.clear()
        self.model.clear()
        # Останавливаем таймеры на случай если сборщик мусора не успеет удалить екземпляр класса до таймаута таймера
        for task in self.tasks:
            self.tasks[task].timer.stop()
        self.tasks = {}

        self.model.setHorizontalHeaderLabels(['Наименование', 'Последний запуск', 'Следующий запуск', 'Статус'])
        self.setColumnWidth(0, 750)
        self.setColumnWidth(1, 150)
        self.setColumnWidth(2, 150)

        query = "SELECT * FROM sync_tasks"
        data_cur.execute(query)
        tasks = data_cur.fetchall()
        # Добавление задач FTP синхронизации
        for task in tasks:
            if task[10]:
                delay = task[11].split(':')
                delay = int(delay[2]) + int(delay[1])*60 + int(delay[0])*3600
                next_time = datetime.datetime.fromtimestamp(time.time() + delay)
            else:
                # Определяем время следующего запуска
                next_time = get_next_time(task[11])

            next_time = next_time.strftime('%d.%m.%Y %H:%M:%S')
            col1 = QStandardItem(task[1])
            col1.setIcon(QIcon('img\\task_complete.png'))
            self.model.appendRow((col1, QStandardItem(task[12]), QStandardItem(str(next_time)), QStandardItem('')))

            self.tasks[task[1]] = SyncTask(task)

            task_action = QAction(task[1], self)
            task_action.triggered.connect(self.tasks[task[1]].run_now)
            task_tray_menu.addAction(task_action)

        # Добавление задач резервного копирования
        query = "SELECT * FROM backup_tasks"
        data_cur.execute(query)
        tasks = data_cur.fetchall()
        for task in tasks:
            # Определяем время следующего запуска
            next_time = get_next_time(task[5])
            time_left = int(time.mktime(next_time.timetuple()) - time.time())
            next_time = next_time.strftime('%d.%m.%Y %H:%M:%S')

            col1 = QStandardItem(task[1])
            col1.setIcon(QIcon('img\\task_complete.png'))
            self.model.appendRow((col1, QStandardItem(task[6]), QStandardItem(str(next_time)), QStandardItem('')))

            self.tasks[task[1]] = BackupTask(task, time_left)

        self.model.sort(0)
        self.setCurrentIndex(self.model.index(0, 0))

    def setAction(self, text, shortcut, icon, action):
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(shortcut)
        if icon:
            act.setIcon(QIcon(icon))
        act.triggered.connect(action)
        return act

    # noinspection PyAttributeOutsideInit
    def setActions(self):
        self.newAction = self.setAction("Новая задача", 'Ctrl+N', 'img\\new_task.png', self.newTask)
        self.runAction = self.setAction("Выполнить", 'F5', 'img\\run_task.png', self.runTask)
        self.stopAction = self.setAction("Остановить", 'Esc', 'img\\stop_task.png', self.stopTask)
        self.delAction = self.setAction("Удалить", 'Del', 'img\\del_task.png', self.delTask)
        self.propAction = self.setAction("Свойства", 'Alt+Enter', 'img\\properties.png', self.properties)

    def stopTask(self):
        stop_task.append(self.selected_name)

    def newTask(self):
        msg = QMessageBox(self)
        msg.addButton("       Новая задача синхронизации        ", QMessageBox.AcceptRole)
        msg.addButton(" Новая задача резервного копирования ", QMessageBox.RejectRole)
        msg.setText('\t\t\tВыберите тип для новой задачи')
        msg.setWindowTitle('Новая задача')
        reply = msg.exec_()
        if reply:
            s = AddEditBackupWidget('', self)
        else:
            s = AddEditSyncWidget('', self)
        s.destroyed.connect(self.setData)                   # Обновить список задач после выхода
        s.show()

    def runTask(self):
        self.tasks[self.selected_name].run_now()

    def delTask(self):
        msg = QMessageBox(self)
        msg.addButton("Да", QMessageBox.AcceptRole)
        msg.addButton("Нет", QMessageBox.RejectRole)
        msg.setText('Вы действительно хотите удалить ' + self.selected_name + ' ?')
        msg.setWindowTitle('Удаление')
        msg.setIcon(QMessageBox.Question)
        reply = msg.exec_()
        if reply == 0:
            if self.tasks[self.selected_name].__class__.__name__ == 'SyncTask':
                query = "DELETE FROM sync_tasks WHERE name='" + self.selected_name + "'"
            else:
                query = "DELETE FROM backup_tasks WHERE name='" + self.selected_name + "'"
            data_cur.execute(query)
            data_conn.commit()
            # Удаляем логи по задаче
            query = "DELETE FROM task_log WHERE task_name='" + self.selected_name + "'"
            data_cur.execute(query)
            data_conn.commit()
            self.selected_name = ''                         # на случай удаления последней задачи
            self.setData()

    def properties(self):
        if self.tasks[self.selected_name].__class__.__name__ == 'SyncTask':     # Если задача синхронизации
            s = AddEditSyncWidget(self.selected_name, self)
        else:                                                                   # Задача резервного копирования
            s = AddEditBackupWidget(self.selected_name, self)
        s.destroyed.connect(self.setData)                   # Обновить список задач после выхода
        s.show()

    def addUserActions(self):
        self.menu.clear()
        self.menu.addAction(self.newAction)
        self.menu.addSeparator()
        self.menu.addAction(self.runAction)
        self.menu.addAction(self.stopAction)
        self.menu.addAction(self.delAction)
        self.menu.addSeparator()
        self.menu.addAction(self.propAction)
        # Добавление действий для быстрых клавиш
        self.addAction(self.newAction)
        self.addAction(self.runAction)
        self.addAction(self.stopAction)
        self.addAction(self.delAction)
        self.addAction(self.propAction)

        if self.model.item(self.selectedIndexes()[0].row(), 3).text() == 'Синхронизация':
            groupSetEnabled((self.stopAction, ), True)
            groupSetEnabled((self.runAction, self.delAction, self.propAction), False)
        else:
            groupSetEnabled((self.stopAction,), False)
            groupSetEnabled((self.runAction, self.delAction, self.propAction), True)

    " контекстное меню "
    def myMenu(self, pos):
        # добавление действий
        self.addUserActions()
        # отображение меню
        pos.setY(pos.y() + 22)
        self.menu.exec_(self.mapToGlobal(pos))

    " Основной таймер для обновления активности в списке "
    def run_timer(self):
        global task_tray_menu, ex
        run = 0
        # Проверяем статус задач синхронизации
        query = "SELECT name, status, last_sync, time, scheduler_type FROM sync_tasks WHERE status > 0"
        data_cur.execute(query)
        tasks = data_cur.fetchall()
        for task in tasks:
            if task[1] == 1:                                        # если началась синхронизация
                for i in range(self.model.rowCount()):
                    if self.model.item(i, 0).text() == task[0]:
                        self.model.item(i, 0).setIcon(QIcon('img\\task_run.png'))
                        self.model.item(i, 3).setText('Синхронизация')
                for action in task_tray_menu.actions():     # Делаем неактивным действие в трее
                    if action.text() == task[0]:
                        action.setDisabled(True)
                run = 1
            else:                                                   # если закончилась синхронизация
                for i in range(self.model.rowCount()):
                    if self.model.item(i, 0).text() == task[0]:
                        if task[1] == 2:
                            self.model.item(i, 0).setIcon(QIcon('img\\task_complete.png'))
                            self.model.item(i, 3).setText('Успех')
                        elif task[1] == 3:
                            self.model.item(i, 0).setIcon(QIcon('img\\task_error.png'))
                            self.model.item(i, 3).setText('Ошибка')
                        else:
                            self.model.item(i, 0).setIcon(QIcon('img\\task_stopped.png'))
                            self.model.item(i, 3).setText('Остановлено')
                        self.model.item(i, 1).setText(task[2])
                        # Определяем время следующего запуска
                        if task[4]:
                            delay = task[3].split(':')
                            delay = int(delay[2]) + int(delay[1]) * 60 + int(delay[0]) * 3600
                            self.tasks[task[0]].timer.setInterval(delay*1000)
                            next_time = datetime.datetime.fromtimestamp(time.time() + delay)
                        else:
                            next_time = get_next_time(task[3])
                        next_time = next_time.strftime('%d.%m.%Y %H:%M:%S')

                        self.model.item(i, 2).setText(next_time)
                        query = "UPDATE sync_tasks SET status=0 WHERE name='" + task[0] + "'"
                        try:
                            data_cur.execute(query)
                            data_conn.commit()
                        except:
                            pass
                for action in task_tray_menu.actions():     # Делаем активным действие в трее
                    if action.text() == task[0]:
                        action.setDisabled(False)
        # Проверяем статус задач резервного копирования
        query = "SELECT name, status, last_sync, time FROM backup_tasks WHERE status > 0"
        data_cur.execute(query)
        tasks = data_cur.fetchall()
        for task in tasks:
            if task[1] == 1:  # если началась синхронизация
                for i in range(self.model.rowCount()):
                    if self.model.item(i, 0).text() == task[0]:
                        self.model.item(i, 0).setIcon(QIcon('img\\task_run.png'))
                        self.model.item(i, 3).setText('Синхронизация')
                run = 1
            else:  # если закончилась синхронизация
                for i in range(self.model.rowCount()):
                    if self.model.item(i, 0).text() == task[0]:
                        if task[1] == 2:
                            self.model.item(i, 0).setIcon(QIcon('img\\task_complete.png'))
                            self.model.item(i, 3).setText('Успех')
                        elif task[1] == 3:
                            self.model.item(i, 0).setIcon(QIcon('img\\task_error.png'))
                            self.model.item(i, 3).setText('Ошибка')
                        else:
                            self.model.item(i, 0).setIcon(QIcon('img\\task_stopped.png'))
                            self.model.item(i, 3).setText('Остановлено')
                        self.model.item(i, 1).setText(task[2])
                        # Определяем время следующего запуска
                        next_time = get_next_time(task[3])
                        next_time = next_time.strftime('%d.%m.%Y %H:%M:%S')

                        self.model.item(i, 2).setText(next_time)
                        query = "UPDATE backup_tasks SET status=0 WHERE name='" + task[0] + "'"
                        try:
                            data_cur.execute(query)
                            data_conn.commit()
                        except:
                            pass
        if run:
            ex.tray_icon.setIcon(QIcon('img\\mainicon_run.ico'))
        else:
            ex.tray_icon.setIcon(QIcon('img\\mainicon.ico'))
        # Установка активности тулбара
        if self.selected_name:
            if self.model.item(self.selectedIndexes()[0].row(), 3).text() == 'Синхронизация':
                groupSetEnabled((toolbar.stopAction, ), True)
                groupSetEnabled((toolbar.runAction, toolbar.delAction, toolbar.propAction), False)
            else:
                groupSetEnabled((toolbar.stopAction,), False)
                groupSetEnabled((toolbar.runAction, toolbar.delAction, toolbar.propAction), True)
        else:
            groupSetEnabled((toolbar.runAction, toolbar.delAction, toolbar.stopAction, toolbar.propAction), False)

    " Действие для таймера логов "
    def update_timer_timeout(self):
        query = "SELECT * FROM task_log WHERE task_name = '" + self.selected_name + "' AND date > " \
                + str(self.last_update)
        logs = data_cur.execute(query)
        for log in logs:
            text = datetime.datetime.fromtimestamp(log[1]).strftime('%d.%m.%Y %H:%M:%S') + '   ' + log[2]
            taskText.append(text)
        self.last_update = time.time()

    " Раз в час очищаем старые и накопившиеся логи "
    def clearlog_timer_timeout(self):
        clear_old_log()
        for i in range(self.model.rowCount()):
            clear_task_log(self.model.item(i, 0).text())
        clear_task_log('AutoUpdateProg')
        # shrink
        query = "VACUUM"
        try:
            data_cur.execute(query)
            data_conn.commit()
        except:
            pass
        # обновленеи программы
        threading.Thread(target=sync_from_ftp,
                         args=(ftp_path[0], (ftp_path[1], ftp_path[2]), ftp_path[3],
                               '', 'AutoUpdateProg', '*.*')).start()

    " Действия для таймера быстрого выполнения задач "
    def fastrun_timer_timeout(self):
        if not os.path.exists('fast_run'):
            os.mkdir('fast_run')
        fastrun_files = os.listdir('fast_run')
        for file in fastrun_files:
            if os.path.isdir('fast_run\\' + file):
                os.rmdir('fast_run\\' + file)
            else:
                for i in range(self.model.rowCount()):
                    if self.model.item(i, 0).text().lower() == file.split('.')[0].lower():
                        self.tasks[self.model.item(i, 0).text()].run_now()
                        os.remove('fast_run\\' + file)

    " двойной клик "
    def mouseDoubleClickEvent(self, e):
        self.properties()

    " При изменении выбора задачи "
    def selectionChanged(self, sel1, sel2):
        if len(self.selectedIndexes()) > 0:
            taskText.clear()
            self.selected_name = self.selectedIndexes()[0].data()
            self.last_update = 0
        else:
            self.selected_name = ''
        super().selectionChanged(sel1, sel2)


"""
    Главное меню
"""


class MyMenu(QMenuBar):

    def __init__(self):
        super().__init__()
        self.fileMenu = QMenu("Файл")
        self.initUI()

    " Создание меню "
    def initUI(self):
        self.clear()
        self.setActions()

        self.fileMenu.addAction(self.importAction)
        self.fileMenu.addAction(self.exportAction)

        self.addMenu(self.fileMenu)
        self.addAction(self.exitAction)

    " Установка действий для меню "
    # noinspection PyAttributeOutsideInit
    def setActions(self):
        self.exitAction = QAction('Выход', self)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.triggered.connect(app.exit)

        self.importAction = QAction('Загрузить задачи из файла', self)
        self.importAction.triggered.connect(self.importTasks)

        self.exportAction = QAction('Сохранить задачи в файл', self)
        self.exportAction.triggered.connect(self.exportTasks)

    @staticmethod
    def importTasks():
        zip_name = QFileDialog.getOpenFileName(QWidget(), 'Открыть файл', 'D:', '*.zip')[0]
        if zip_name:
            zip_name = os.path.abspath(zip_name)
            with zipfile.ZipFile(zip_name, 'r', zipfile.ZIP_DEFLATED, True) as myzip:
                for name in myzip.namelist():
                    task_text = myzip.read(name).decode()
                    task_text = task_text.split(',')
                    task_name = name.split('.')
                    # Проверяем на дублирование названия задачи
                    data_correct = True
                    query = "SELECT name FROM sync_tasks WHERE name='" + task_name[0] + "'"
                    data_cur.execute(query)
                    name = data_cur.fetchone()
                    if name:
                        data_correct = False
                    query = "SELECT name FROM backup_tasks WHERE name='" + task_name[0] + "'"
                    data_cur.execute(query)
                    name = data_cur.fetchone()
                    if name:
                        data_correct = False
                    if data_correct:  # Если нет задачи с таким назваием - добавляем
                        if task_name[1] == 'sync':
                            try:
                                query = """INSERT INTO sync_tasks(name, folder1, mask, ftp_adr, ftp_port, ftp_login, 
                                ftp_pass, ftp_folder, sync_direction, scheduler_type, time, last_sync, is_run, status) 
                                VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', {}, {}, '{}', '{}', {}, {})"""
                                query = query.format(task_name[0], *task_text)
                                data_cur.execute(query)
                                data_conn.commit()
                            except:
                                pass
                        elif task_name[1] == 'backup':
                            try:
                                query = """INSERT INTO backup_tasks(name, backup_list, folder, zip_name, time, 
                                last_sync, is_run, status, run_after, need_run_after)
                                VALUES ('{}', '{}', '{}', '{}', '{}', '{}', {}, {}, '{}', {})"""
                                query = query.format(task_name[0], *task_text)
                                data_cur.execute(query)
                                data_conn.commit()
                            except:
                                pass
        global taskList
        taskList.setData()

    @staticmethod
    def exportTasks():
        zip_name = QFileDialog.getSaveFileName(QWidget(), 'Сохранить файл', 'D:', '*.zip')[0]
        if zip_name:
            zip_name = os.path.abspath(zip_name)
            if os.path.exists(zip_name):
                os.remove(zip_name)
            with zipfile.ZipFile(zip_name, 'a', zipfile.ZIP_DEFLATED, True) as myzip:
                # Добавляем задачи синхронизации
                query = "SELECT * FROM sync_tasks"
                data_cur.execute(query)
                sync_data = data_cur.fetchall()
                for task in sync_data:
                    with open(task[1]+'.sync', 'w') as myfile:
                        text = []
                        for s in task:
                            text.append(str(s))
                        text = ','.join(text[2:])
                        myfile.write(text)
                    myzip.write(task[1]+'.sync')
                    os.remove(task[1]+'.sync')

                query = "SELECT * FROM backup_tasks"
                data_cur.execute(query)
                backup_data = data_cur.fetchall()
                for task in backup_data:
                    with open(task[1]+'.backup', 'w') as myfile:
                        text = []
                        for s in task:
                            text.append(str(s))
                        text = ','.join(text[2:])
                        myfile.write(text)
                    myzip.write(task[1]+'.backup')
                    os.remove(task[1]+'.backup')


class MyToolBar(QToolBar):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setActions()
        self.setMovable(False)
        self.setIconSize(QSize(20, 20))

        self.addAction(self.newAction)
        self.addSeparator()
        self.addAction(self.runAction)
        self.addAction(self.stopAction)
        self.addAction(self.delAction)
        self.addSeparator()
        self.addAction(self.propAction)

    @staticmethod
    def setAction(icon, action):
        act = QAction(QIcon(icon), '')
        act.triggered.connect(action)
        return act

    # noinspection PyAttributeOutsideInit
    def setActions(self):
        self.newAction = self.setAction('img\\new_task_big.png', taskList.newTask)
        self.runAction = self.setAction('img\\run_task_big.png', taskList.runTask)
        self.stopAction = self.setAction('img\\stop_task_big.png', taskList.stopTask)
        self.delAction = self.setAction('img\\del_task_big.png', taskList.delTask)
        self.propAction = self.setAction('img\\properties_big.png', taskList.properties)


"""
    Отображает центальный экран 
"""


class MainWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        global taskList, taskText
        taskText = QTextEdit(self)
        taskText.setReadOnly(True)
        taskText.setFrameShape(QFrame.StyledPanel)

        taskList = TaskList()
        taskList.setFrameShape(QFrame.StyledPanel)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(taskList)
        splitter.addWidget(taskText)
        splitter.setSizes([400, 100])

        hbox = QVBoxLayout()
        hbox.setSpacing(0)
        hbox.setContentsMargins(3, 0, 3, 0)
        hbox.addWidget(splitter)
        self.setLayout(hbox)


"""
    Главное окно программы
"""


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.tray_icon = QSystemTrayIcon(self)
        self.initUI()

    def initUI(self):
        global toolbar
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)

        my_menu = MyMenu()
        self.setMenuBar(my_menu)
        self.setTryMenu()

        self.setCentralWidget(MainWidget())

        toolbar = MyToolBar()
        self.addToolBar(toolbar)

        self.setGeometry(0, 0, 1000, 800)
        self.setWindowIcon(QIcon('img\\mainicon.ico'))
        self.setWindowTitle('Клиент для FTP синхронизации и резервного копирования')

    def setTryMenu(self):
        global task_tray_menu
        show_action = QAction("Открыть", self)
        quit_action = QAction("Выход", self)
        show_action.triggered.connect(self.showMaximized)
        show_action.setFont(QFont('Times', 8, 75))
        quit_action.triggered.connect(qApp.quit)
        tray_menu = QMenu()

        tray_menu.addAction(show_action)
        task_tray_menu = tray_menu.addMenu("Выполнить")
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip('Клиент для FTP синхронизации и резервного копирования')
        self.tray_icon.setIcon(QIcon('img\\mainicon.ico'))
        self.tray_icon.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    wnd = win32gui.FindWindow(None, 'Клиент для FTP синхронизации и резервного копирования')
    if wnd:                             # Повторный запуск запрещен
        app.exit()
    else:
        global ex
        ex = MainWindow()
        sys.exit(app.exec_())
