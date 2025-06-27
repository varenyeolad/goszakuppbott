import os
import time
import pyautogui
import pyperclip
from time import time as now
from logging import getLogger, basicConfig, INFO
from pywinauto.application import Application

# Setup logging
basicConfig(level=INFO)
logger = getLogger("eds")

# Required for confidence matching
# Make sure you have opencv-python installed: pip install opencv-python
pyautogui_images = os.path.join(os.path.dirname(__file__), "screens")


class ProjectError(Exception):
    """Custom exception for project-related errors."""
    pass


class EdsManager:
    def __init__(self, eds_path: str, eds_pass: str):
        self.eds_path = eds_path
        self.eds_pass = eds_pass

    def wait_for_ncalayer_window(self, timeout=10):
        try:
            self.app = Application(backend="uia").connect(
                title_re=".*(Формирование ЭЦП|Выберите сертификат).*", timeout=timeout
            )
            self.window = self.app.top_window()
            self.window.set_focus()
            logger.info("🪟 Окно NCALayer найдено и активировано")
            return self.window.window_text()
        except Exception as e:
            logger.warning(f"⚠️ Окно NCALayer не найдено: {e}")
            return None

    def execute_sign_by_eds(self):
        try:
            window_title = self.wait_for_ncalayer_window()
            if not window_title:
                raise ProjectError("Окно NCALayer не обнаружено")

            if "Формирование ЭЦП" in window_title:
                logger.info("🟡 Режим: Сохранённый сертификат")
                self.try_click_yellow_iin()
                self.click_password_form()
                self.enter_password_form()

            elif "Выберите сертификат" in window_title:
                logger.info("📁 Режим: Выбор нового сертификата")
                self.indicate_eds_path()
                self.click_password_form()
                self.enter_password_form()

        except Exception as e:
            logger.exception("❌ Ошибка при подаче ЭЦП: %s", e)

    def click_obj(self, image_name: str, timeout=10):
        image_path = os.path.join(pyautogui_images, image_name)
        start = now()
        while now() - start < timeout:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=0.7)
            if location:
                pyautogui.click(location)
                logger.info(f"✅ Клик по {image_name}")
                logger.info(f"✅ Клик по {image_name} в координатах {location}")
                return True
            time.sleep(1)
        logger.warning(f"📷 Не найдено изображение: {image_path}")
        return False

    def try_click_yellow_iin(self):
        return self.click_obj("yellow_button.png", timeout=3)

    def click_choose_btn(self):
        time.sleep(0.5)
        self.window.set_focus()
        if not self.click_obj("personal_comp.png"):
            raise FileNotFoundError("Кнопка выбора файла не найдена")

    def click_path_form(self):
        time.sleep(0.5)
        self.window.set_focus()
        self.click_obj("form_exist.png")

    def indicate_eds_path(self):
        time.sleep(0.5)
        pyperclip.copy(self.eds_path)
        pyautogui.hotkey("ctrl", "v")
        pyautogui.press("enter")
        logger.info("📋 Вставлен путь к ЭЦП")

    def click_password_form(self):
        time.sleep(0.5)
        self.window.set_focus()
        self.click_obj("form_pass.png")

    def enter_password_form(self):
        time.sleep(0.5)
        pyperclip.copy(self.eds_pass)
        pyautogui.hotkey("ctrl", "v")
        pyautogui.press("enter")
        logger.info("🔑 Пароль вставлен")
