from fync import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


class AddEditSyncWidget(QWidget):

    def __init__(self, task='', parent=None):
        super().__init__(parent, Qt.Window)
        self.task = task
        self.cancelButton = QPushButton("Закрыть")
        self.okButton = QPushButton("Сохранить")
        self.panel = QFrame()
        self.taskNameEdit = QLineEdit(self.panel)
        self.taskFolderEdit = QLineEdit(self.panel)
        self.folderButton = QPushButton(self.panel)
        self.ftpAdrEdit = QLineEdit(self.panel)
        self.ftpPortEdit = QLineEdit(self.panel)
        self.ftpLoginEdit = QLineEdit(self.panel)
        self.ftpPassEdit = QLineEdit(self.panel)
        self.ftpFolderEdit = QLineEdit(self.panel)
        self.syncDirCombo = QComboBox(self.panel)
        self.maskEdit = QLineEdit(self.panel)
        self.syncTypeCombo = QComboBox(self.panel)
        self.periodEdit = QTimeEdit(self.panel)
        self.initUI()

    def initUI(self):
        self.okButton.clicked.connect(self.okAction)

        self.cancelButton.clicked.connect(self.closeWin)
        self.setStyleSheet("QComboBox { background-color: #ffffff;}")

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.setContentsMargins(10, 0, 10, 10)
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.cancelButton)

        self.panel.setFrameShadow(QFrame.Raised)
        self.panel.setFrameShape(QFrame.Panel)
        self.panel.setFixedSize(320, 365)
        self.setPanelItems()
        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.panel)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.setFixedSize(320, 405)
        if self.task:
            self.setWindowTitle('Свойства задачи ' + self.task)
        else:
            self.setWindowTitle('Новая задача синхронизации')
        self.setWindowModality(Qt.WindowModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

    def setPanelItems(self):
        QLabel('Название задачи:', self.panel).move(10, 11)
        self.taskNameEdit.move(120, 8)
        self.taskNameEdit.setFixedWidth(190)

        QLabel('Папка синхронизации:', self.panel).move(10, 35)
        self.taskFolderEdit.move(10, 55)
        self.taskFolderEdit.setFixedWidth(280)
        self.folderButton.move(290, 54)
        self.folderButton.setFixedSize(22, 22)
        self.folderButton.setIcon(QIcon('img\\folder.png'))
        self.folderButton.clicked.connect(self.fldbtnClick)

        line = QFrame(self.panel)
        line.setGeometry(QRect(5, 80, 310, 4))
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        QLabel('Настройки FTP:', self.panel).move(10, 90)
        QLabel('Адрес:', self.panel).move(10, 113)
        self.ftpAdrEdit.move(60, 110)
        self.ftpAdrEdit.setFixedWidth(160)

        QLabel('Порт:', self.panel).move(230, 113)
        self.ftpPortEdit.move(270, 110)
        self.ftpPortEdit.setFixedWidth(40)

        QLabel('Логин:', self.panel).move(10, 138)
        self.ftpLoginEdit.move(60, 135)
        self.ftpLoginEdit.setFixedWidth(250)

        QLabel('Пароль:', self.panel).move(10, 163)
        self.ftpPassEdit.move(60, 160)
        self.ftpPassEdit.setFixedWidth(250)
        self.ftpPassEdit.setEchoMode(QLineEdit.Password)

        QLabel('Папка:', self.panel).move(10, 188)
        self.ftpFolderEdit.move(60, 185)
        self.ftpFolderEdit.setFixedWidth(250)

        line1 = QFrame(self.panel)
        line1.setGeometry(QRect(5, 210, 310, 4))
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)

        QLabel('Направление синхронизации:', self.panel).move(10, 220)
        self.syncDirCombo.move(10, 240)
        self.syncDirCombo.setFixedSize(300, 22)
        self.syncDirCombo.addItems(['Копировать из папки синхронизации на FTP',
                                    'Копировать из FTP в папку синхронизации'])

        QLabel('Маска файлов:', self.panel).move(10, 273)
        self.maskEdit.move(100, 270)
        self.maskEdit.setFixedWidth(210)

        line1 = QFrame(self.panel)
        line1.setGeometry(QRect(5, 295, 310, 4))
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)

        QLabel('Период синхронизации:', self.panel).move(10, 308)
        self.syncTypeCombo.move(140, 305)
        self.syncTypeCombo.setFixedSize(170, 22)
        self.syncTypeCombo.addItems(['Ежедневно', 'Выбраный период'])

        self.periodEdit.move(10, 335)
        self.periodEdit.setFixedWidth(120)
        self.periodEdit.setDisplayFormat('HH:mm:ss')

        # Заполнение формы
        if self.task:                                       # Если редактирование
            query = "SELECT * FROM sync_tasks WHERE name='" + self.task + "'"
            data_cur.execute(query)
            task_data = data_cur.fetchall()
            task_data = task_data[0]

            self.taskNameEdit.setText(task_data[1])
            self.taskFolderEdit.setText(task_data[2])
            self.ftpAdrEdit.setText(task_data[4])
            self.ftpPortEdit.setText(task_data[5])
            self.ftpLoginEdit.setText(task_data[6])
            self.ftpPassEdit.setText(task_data[7])
            self.ftpFolderEdit.setText(task_data[8])
            self.syncDirCombo.setCurrentIndex(task_data[9])
            self.maskEdit.setText(task_data[3])
            self.syncTypeCombo.setCurrentIndex(task_data[10])
            task_time = task_data[11].split(':')
            self.periodEdit.setTime(QTime(int(task_time[0]), int(task_time[1]), int(task_time[2])))

        else:                                               # Если новая задача
            self.syncTypeCombo.setCurrentIndex(1)
            self.periodEdit.setTime(QTime(0, 5))
            self.ftpPortEdit.setText('21')
            self.maskEdit.setText('*.*')

    def fldbtnClick(self):
        folder = QFileDialog.getExistingDirectory(QWidget(), 'Выбор папки')
        self.taskFolderEdit.setText(os.path.abspath(folder) + '\\')

    " сохранить и закрыть "
    def okAction(self):
        data_correct = True
        # Проверяем заполнение всех полей
        if (not self.taskNameEdit.text()) or (not self.taskFolderEdit.text()) or (not self.ftpAdrEdit.text()) or \
            (not self.ftpPortEdit.text()) or (not self.ftpLoginEdit.text()) or (not self.ftpPassEdit.text()) or \
                (not self.ftpFolderEdit.text()) or (not self.maskEdit.text()):
            data_correct = False
        # Проверяем на дублирование названия задачи
        query = "SELECT name FROM sync_tasks WHERE name='" + self.taskNameEdit.text() + "'"
        data_cur.execute(query)
        name = data_cur.fetchone()
        if name and (name[0] != self.task):
            data_correct = False
        query = "SELECT name FROM backup_tasks WHERE name='" + self.taskNameEdit.text() + "'"
        data_cur.execute(query)
        name = data_cur.fetchone()
        if name:
            data_correct = False
        # Если данные корректны
        if data_correct:
            if self.task:
                query = """UPDATE sync_tasks SET name='{}', folder1='{}', mask='{}', ftp_adr='{}', ftp_port='{}', 
                ftp_login='{}', ftp_pass='{}', ftp_folder='{}', sync_direction={}, scheduler_type={}, time='{}' 
                WHERE name='{}'"""
                query = query.format(self.taskNameEdit.text(), self.taskFolderEdit.text(), self.maskEdit.text(),
                                     self.ftpAdrEdit.text(), self.ftpPortEdit.text(), self.ftpLoginEdit.text(),
                                     self.ftpPassEdit.text(), self.ftpFolderEdit.text(),
                                     str(self.syncDirCombo.currentIndex()), str(self.syncTypeCombo.currentIndex()),
                                     self.periodEdit.text(), self.task)
            else:
                query = """INSERT INTO sync_tasks(name, folder1, mask, ftp_adr, ftp_port, ftp_login, ftp_pass, 
                ftp_folder, sync_direction, scheduler_type, time, last_sync, is_run, status) 
                VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', {}, {}, '{}', '01.01.2018 00:00:00', 0, 0)"""
                query = query.format(self.taskNameEdit.text(), self.taskFolderEdit.text(), self.maskEdit.text(),
                                     self.ftpAdrEdit.text(), self.ftpPortEdit.text(), self.ftpLoginEdit.text(),
                                     self.ftpPassEdit.text(), self.ftpFolderEdit.text(),
                                     str(self.syncDirCombo.currentIndex()), str(self.syncTypeCombo.currentIndex()),
                                     self.periodEdit.text())
            data_cur.execute(query)
            data_conn.commit()
            self.close()
        else:
            QMessageBox.warning(self, 'Некорректные данные',
                                'Заполнены не все поля или задача с таким названием уже существует')

    " выход по ескейпу "
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()

    " закрытие окна"
    def closeWin(self):
        self.close()


class AddEditBackupWidget(QWidget):

    def __init__(self, task='', parent=None):
        super().__init__(parent, Qt.Window)
        self.task = task
        self.cancelButton = QPushButton("Закрыть")
        self.okButton = QPushButton("Сохранить")
        self.panel = QFrame()

        self.taskNameEdit = QLineEdit(self.panel)
        self.backupList = QListView(self.panel)
        self.listModel = QStandardItemModel()
        self.addfileButton = QPushButton("Добавить файл", self.panel)
        self.addfolderButton = QPushButton("Добавить папку", self.panel)
        self.delButton = QPushButton("Удалить", self.panel)

        self.backupFolderEdit = QLineEdit(self.panel)
        self.backupFolderButton = QPushButton(self.panel)
        self.zipnameEdit = QLineEdit(self.panel)
        self.periodEdit = QTimeEdit(self.panel)
        self.needrunCheck = QCheckBox("Выполнить после резервного копирования", self.panel)
        self.runafterEdit = QLineEdit(self.panel)
        self.runafterButton = QPushButton("Выбрать", self.panel)
        self.initUI()

    def initUI(self):
        self.okButton.clicked.connect(self.okAction)

        self.cancelButton.clicked.connect(self.closeWin)
        self.setStyleSheet("QComboBox { background-color: #ffffff;}")

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.setContentsMargins(10, 0, 10, 10)
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.cancelButton)

        self.panel.setFrameShadow(QFrame.Raised)
        self.panel.setFrameShape(QFrame.Panel)
        self.panel.setFixedSize(320, 340)
        self.setPanelItems()
        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.panel)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.setFixedSize(320, 380)
        if self.task:
            self.setWindowTitle('Свойства задачи ' + self.task)
        else:
            self.setWindowTitle('Новая задача резервного копирования')
        self.setWindowModality(Qt.WindowModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

    def setPanelItems(self):
        QLabel('Название задачи:', self.panel).move(10, 11)
        self.taskNameEdit.move(120, 8)
        self.taskNameEdit.setFixedWidth(190)

        line = QFrame(self.panel)
        line.setGeometry(QRect(5, 35, 310, 4))
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        QLabel('Список для резервного копирования:', self.panel).move(10, 42)

        self.backupList.move(10, 60)
        self.backupList.setFixedSize(300, 80)
        self.backupList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.backupList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.backupList.setModel(self.listModel)

        self.addfileButton.move(10, 145)
        self.addfileButton.setFixedWidth(96)
        self.addfileButton.clicked.connect(self.addfileAction)

        self.addfolderButton.move(112, 145)
        self.addfolderButton.setFixedWidth(96)
        self.addfolderButton.clicked.connect(self.addfolderAction)

        self.delButton.move(214, 145)
        self.delButton.setFixedWidth(96)
        self.delButton.clicked.connect(self.delAction)
        self.delButton.setDisabled(True)

        line1 = QFrame(self.panel)
        line1.setGeometry(QRect(5, 172, 310, 4))
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)

        QLabel('Папка для резервного копирования:', self.panel).move(10, 180)
        self.backupFolderEdit.move(10, 200)
        self.backupFolderEdit.setFixedWidth(280)
        self.backupFolderButton.move(290, 199)
        self.backupFolderButton.setFixedSize(22, 22)
        self.backupFolderButton.setIcon(QIcon('img\\folder.png'))
        self.backupFolderButton.clicked.connect(self.bfldbtnClick)

        QLabel('Имя файла архива:', self.panel).move(10, 230)
        self.zipnameEdit.move(140, 227)
        self.zipnameEdit.setFixedWidth(170)

        QLabel('Время планировщика:', self.panel).move(10, 258)
        self.periodEdit.move(140, 255)
        self.periodEdit.setFixedWidth(170)
        self.periodEdit.setDisplayFormat('HH:mm:ss')

        line2 = QFrame(self.panel)
        line2.setGeometry(QRect(5, 280, 310, 4))
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)

        self.needrunCheck.move(10, 287)
        self.needrunCheck.stateChanged.connect(self.runafterChecked)

        self.runafterEdit.move(10, 310)
        self.runafterEdit.setFixedWidth(240)
        self.runafterButton.move(250, 309)
        self.runafterButton.setFixedSize(62, 22)
        self.runafterButton.clicked.connect(self.runbtnClick)

        # Заполнение данных
        if self.task:                                   # Если редактирование
            query = "SELECT * FROM backup_tasks WHERE name='" + self.task + "'"
            data_cur.execute(query)
            task_data = data_cur.fetchall()
            task_data = task_data[0]
            self.taskNameEdit.setText(task_data[1])
            for item in task_data[2].split('|'):
                self.listModel.appendRow(QStandardItem(item))
            self.backupList.setCurrentIndex(self.listModel.index(0, 0))
            self.delButton.setDisabled(False)

            self.backupFolderEdit.setText(task_data[3])
            self.zipnameEdit.setText(task_data[4])
            task_time = task_data[5].split(':')
            self.periodEdit.setTime(QTime(int(task_time[0]), int(task_time[1]), int(task_time[2])))
            if task_data[10]:
                self.needrunCheck.setCheckState(Qt.Unchecked)
                self.needrunCheck.setCheckState(Qt.Checked)
            else:
                self.needrunCheck.setCheckState(Qt.Checked)
                self.needrunCheck.setCheckState(Qt.Unchecked)
            self.runafterEdit.setText(task_data[9])
        else:                                           # Если новая задача
            self.needrunCheck.setCheckState(Qt.Checked)
            self.needrunCheck.setCheckState(Qt.Unchecked)
            self.periodEdit.setTime(QTime(2, 0))
            self.zipnameEdit.setText('newarhiv.zip')

    " Действия для галочки действия после резервного копирования "
    def runafterChecked(self, state):
        if state == Qt.Checked:
            self.runafterEdit.setDisabled(False)
            self.runafterButton.setDisabled(False)
        else:
            self.runafterEdit.setDisabled(True)
            self.runafterButton.setDisabled(True)

    " Кнопка выбора действия после бекапа "
    def runbtnClick(self):
        run_file = QFileDialog.getOpenFileName(QWidget(), 'Выбрать файл', 'D:')[0]
        if run_file:
            self.runafterEdit.setText(os.path.abspath(run_file))

    " Кнопка выбора папки для резервного копирования "
    def bfldbtnClick(self):
        folder = QFileDialog.getExistingDirectory(QWidget(), 'Выбор папки', self.backupFolderEdit.text())
        if folder:
            self.backupFolderEdit.setText(os.path.abspath(folder))

    " Кнопка добавления файла "
    def addfileAction(self):
        file = QFileDialog.getOpenFileName(QWidget(), 'Добавить файл')[0]
        if file:
            self.listModel.appendRow((QStandardItem(os.path.abspath(file))))
            self.backupList.setCurrentIndex(self.listModel.index(0, 0))
            self.delButton.setDisabled(False)

    " Кнопка добавления папки "
    def addfolderAction(self):
        folder = QFileDialog.getExistingDirectory(QWidget(), 'Добавить папку')
        if folder:
            self.listModel.appendRow((QStandardItem(os.path.abspath(folder))))
            self.backupList.setCurrentIndex(self.listModel.index(0, 0))
            self.delButton.setDisabled(False)

    " Кнопка удаления из списка "
    def delAction(self):
        self.listModel.removeRow(self.backupList.selectedIndexes()[0].row())
        if self.listModel.rowCount() == 0:
            self.delButton.setDisabled(True)

    " сохранить и закрыть "
    def okAction(self):
        data_correct = True
        # Проверяем заполнение всех полей
        if (not self.taskNameEdit.text()) or (not self.backupFolderEdit.text()) or (not self.zipnameEdit.text()) or \
                (self.listModel.rowCount() == 0):
            data_correct = False
        if self.needrunCheck.checkState() > 0 and (not self.runafterEdit.text()):
            data_correct = False
        # Проверяем на дублирование названия задачи
        query = "SELECT name FROM backup_tasks WHERE name='" + self.taskNameEdit.text() + "'"
        data_cur.execute(query)
        name = data_cur.fetchone()
        if name and (name[0] != self.task):
            data_correct = False
        query = "SELECT name FROM sync_tasks WHERE name='" + self.taskNameEdit.text() + "'"
        data_cur.execute(query)
        name = data_cur.fetchone()
        if name:
            data_correct = False
        # Если данные корректны
        if data_correct:
            backup_list = []
            for i in range(self.listModel.rowCount()):
                backup_list.append(self.listModel.item(i, 0).text())
            backup_list = '|'.join(backup_list)
            if self.needrunCheck.checkState() > 0:
                need_run = '1'
            else:
                need_run = '0'
            if self.task:
                query = """UPDATE backup_tasks SET name='{}', backup_list='{}', folder='{}', zip_name='{}', 
                time='{}', run_after='{}', need_run_after={} WHERE name='{}'"""
                query = query.format(self.taskNameEdit.text(), backup_list, self.backupFolderEdit.text(),
                                     self.zipnameEdit.text(), self.periodEdit.text(), self.runafterEdit.text(),
                                     need_run, self.task)
            else:
                query = """INSERT INTO backup_tasks(name, backup_list, folder, zip_name, time, last_sync, is_run, 
                status, run_after, need_run_after) 
                VALUES ('{}', '{}', '{}', '{}', '{}', '01.01.2018 00:00:00', 0, 0, '{}', {})"""
                query = query.format(self.taskNameEdit.text(), backup_list, self.backupFolderEdit.text(),
                                     self.zipnameEdit.text(), self.periodEdit.text(), self.runafterEdit.text(),
                                     need_run)
            data_cur.execute(query)
            data_conn.commit()
            self.close()
        else:
            QMessageBox.warning(self, 'Некорректные данные',
                                'Заполнены не все поля или задача с таким названием уже существует')

    " выход по ескейпу "
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()

    " закрытие окна"
    def closeWin(self):
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AddEditBackupWidget()
    ex.show()
    sys.exit(app.exec_())
