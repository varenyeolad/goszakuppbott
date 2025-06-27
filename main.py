 # main.py 

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QListWidget, QListWidgetItem, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QTimer
from parser import parse_lots, fast_jump_to_application, select_and_add_lots

import threading
import time


class TenderBot(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Goszakup Tender Bot")
        self.resize(800, 600)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Вставьте ссылку на тендер")

        self.load_button = QPushButton("Загрузить тендер")
        self.load_button.clicked.connect(self.load_tender)

        self.lot_list = QListWidget()

        self.key_path_input = QLineEdit()
        self.key_path_input.setPlaceholderText("Путь к ЭЦП-файлу (.p12 или .pfx)")

        # 🔍 Ищем .p12 или .pfx в папке, где лежит .py/.exe
        self.default_key_path = self.find_key_file()
        if self.default_key_path:
            self.key_path_input.setText(self.default_key_path)

        self.browse_button = QPushButton("Обзор...")
        self.browse_button.clicked.connect(self.browse_key_file)

        self.save_button = QPushButton("Сохранить выбранные лоты")
        self.save_button.clicked.connect(self.save_selection)

        self.submit_button = QPushButton("Отправить заявку")
        self.submit_button.clicked.connect(self.start_submission_monitoring)
        


        layout = QVBoxLayout()
        layout.addWidget(QLabel("Ссылка на тендер:"))
        layout.addWidget(self.url_input)
        layout.addWidget(self.load_button)
        layout.addWidget(QLabel("Список лотов:"))
        layout.addWidget(self.lot_list)
        layout.addWidget(QLabel("Путь к ЭЦП-файлу:"))
        layout.addWidget(self.key_path_input)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.save_button)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def find_key_file(self):
        folder = os.path.dirname(os.path.abspath(sys.argv[0]))  # Папка .exe или .py
        for filename in os.listdir(folder):
            if filename.endswith(".p12") or filename.endswith(".pfx"):
                return os.path.join(folder, filename)
        return ""

    def browse_key_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите ЭЦП-файл", "", "Key Files (*.p12 *.pfx);;All Files (*)"
        )
        if file_path:
            self.key_path_input.setText(file_path)

    def load_tender(self):
        url = self.url_input.text().strip()
        if not url.startswith("http"):
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, вставьте корректную ссылку.")
            return
        try:
            self.driver, lots = parse_lots(url)
            self.lot_list.clear()
            for lot in lots:
                item = QListWidgetItem(lot["text"])
                item.setCheckState(Qt.Unchecked)
                item.setData(Qt.UserRole, lot["id"])
                self.lot_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def save_selection(self):
        selected_lots = []
        for i in range(self.lot_list.count()):
            item = self.lot_list.item(i)
            if item.checkState() == Qt.Checked:
                lot_id = item.data(Qt.UserRole)
                if lot_id:
                    selected_lots.append(lot_id)
        
        self.saved_lot_ids = selected_lots

        key_path = self.key_path_input.text().strip()
        if not key_path or not os.path.isfile(key_path):
            QMessageBox.warning(self, "Ошибка", "Не найден ЭЦП-файл рядом с программой.")
            return

        try:
            with open("submission_data.txt", "w", encoding="utf-8") as f:
                f.write(f"key_path={key_path}\n")
                for lot in selected_lots:
                    f.write(f"lot_id={lot}\n")
            QMessageBox.information(self, "Готово", "✅ Данные успешно сохранены.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка при сохранении", str(e))

    def start_submission_monitoring(self):
        url = self.url_input.text().strip()
        if not url.startswith("http"):
            QMessageBox.warning(self, "Ошибка", "Введите корректную ссылку на тендер.")
            return

        
        def monitor():
            QTimer.singleShot(0, lambda: self.submit_button.setEnabled(False))
            QTimer.singleShot(0, lambda: QMessageBox.information(
                self, "Мониторинг", "⏳ Проверка подачи заявки началась..."))

            while True:
                is_opened = fast_jump_to_application(url, self.saved_lot_ids, self.driver)
                if is_opened:
                    QTimer.singleShot(0, lambda: QMessageBox.information(
                        self, "Готово", "✅ Страница заявки доступна."))
                    break
                time.sleep(5)

            QTimer.singleShot(0, lambda: self.submit_button.setEnabled(True))



        threading.Thread(target=monitor, daemon=True).start()
            


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TenderBot()
    window.show()
    sys.exit(app.exec_())