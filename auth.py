import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pywinauto import Application

logging.basicConfig(level=logging.INFO)

CHROME_PROFILE_PATH = "C:/Users/aizha/goszakup-profile"
CHROMEDRIVER_PATH = "C:/Users/aizha/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe"
ECP_FILE = "C:/Users/aizha/Downloads/goszakupbot/ИП ДАНА GOST512_505941dcaade7bd7905fcb3964c8bdf5b40105b0.p12"
ECP_PASSWORD = "Aa1234"

def init_driver():
    opts = Options()
    opts.add_argument(f"user-data-dir={CHROME_PROFILE_PATH}")
    opts.add_argument("--disable-extensions")
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=opts)

def login_via_ecp(driver):
    try:
        driver.get("https://v3bl.goszakup.gov.kz/ru/user/login")
        logging.info("Ждём кнопку выбора ключа…")
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "selectP12File"))
        )
        btn.click()
        logging.info("Нажали «Выберите ключ» — ждём окно NCALayer…")
        time.sleep(1.5)

        app = Application(backend="uia").connect(title_re=".*(Формирование ЭЦП|Выберите сертификат).*", timeout=10)

        # Определяем, какое окно открылось
        windows = app.windows()
        dlg = None
        mode = None
        for w in windows:
            title = w.window_text()
            if "Формирование ЭЦП" in title:
                dlg = w
                mode = "saved_cert"
                break
            elif "Выберите сертификат" in title:
                dlg = w
                mode = "file_select"
                break

        if not dlg:
            raise Exception("Не удалось найти окно NCALayer")

        logging.info(f"Используем окно: {dlg.window_text()} (режим: {mode})")

        if mode == "saved_cert":
            # Нажимаем на жёлтую кнопку с сертификатом
            dlg.child_window(control_type="Button", found_index=0).click()
            logging.info("Клик по сохранённому ключу")
        elif mode == "file_select":
            # Вставляем путь к p12-файлу
            dlg.child_window(control_type="Edit", found_index=0).set_text(ECP_FILE)
            dlg.child_window(title_re=".*(Открыть|Open).*", control_type="Button").click()
            logging.info("Клик «Открыть» после вставки ключа")
        else:
            raise Exception("Неизвестный режим окна NCALayer")

        time.sleep(1.0)

        # Ждём окно ввода пароля
        pwd_dlg = WebDriverWait(None, 10).until(
            lambda x: app.window(title_re=".*пароль.*", timeout=1)
        )
        pwd_dlg.child_window(control_type="Edit", found_index=0).set_text(ECP_PASSWORD)
        pwd_dlg.child_window(title_re=".*(ОК|OK).*", control_type="Button").click()
        logging.info("Введён пароль к ЭЦП")

        # Ожидаем кнопку "Войти"
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@value='Войти' or @value='Login']"))
        ).click()
        logging.info("Нажата кнопка «Войти»")

        # Проверка перехода в личный кабинет
        WebDriverWait(driver, 10).until(
            EC.url_contains("/cabinet/profile")
        )
        logging.info("Авторизация завершена, вы в кабинете.")
        return driver

    except Exception as e:
        logging.error(f"Ошибка при авторизации: {str(e)}")
        raise

if __name__ == "__main__":
    driver = init_driver()
    try:
        login_via_ecp(driver)
        # Здесь можно вызвать parse_lots() или другие действия после входа
    except Exception as e:
        logging.error(f"Ошибка: {str(e)}")
    finally:
        driver.quit()