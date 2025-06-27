 # parser.py
import logging
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from pywinauto.application import Application
from pywinauto import Desktop
from signer import EdsManager

logging.basicConfig(level=logging.INFO)

CHROME_PROFILE_PATH = "D:/Users/aizha/goszakup-profile"
CHROMEDRIVER_PATH = "D:/Users/aizha/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe"
EDS_PATH = r"D:\Users\aizha\Downloads\goszakupbot\ИП ДАНА GOST512_505941dcaade7bd7905fcb3964c8bdf5b40105b0.p12"  # путь к файлу ЭЦП
EDS_PASS = "Aa1234"  # пароль от ЭЦП

def init_driver():
    logging.info("🔧 Настройка Chrome профиля...")
    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={CHROME_PROFILE_PATH}")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # prefs = {"profile.managed_default_content_settings.images": 2}
    # chrome_options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=chrome_options)

def parse_lots(url):
    driver = init_driver()
    logging.info(f"🌐 Переход на {url}")
    driver.get(url)

    try:
        logging.info("⏳ Ожидание загрузки таблицы с лотами...")
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH, '//table[contains(@class,"table")]/tbody/tr'))
        )
        logging.info("✅ Таблица найдена.")
    except Exception:
        driver.quit()
        raise Exception("❌ Таблица с лотами не найдена. Возможно, вы не авторизованы.")
    

    lots = []
    rows = driver.find_elements(By.XPATH, '//table[contains(@class,"table")]/tbody/tr')
    for row in rows:
        try:
            tds = row.find_elements(By.TAG_NAME, 'td')
            public_id = tds[1].find_element(By.CLASS_NAME, "btn-select-lot").get_attribute("data-lot-id").strip()
            internal_id = tds[1].find_element(By.CLASS_NAME, "btn-select-history").get_attribute("data-lot-id").strip()
            number = tds[1].text.strip().split()[0]
            name = tds[3].text.strip()
            details = tds[4].text.strip()
            quantity = tds[6].text.strip()
            unit = tds[7].text.strip()
            price = tds[5].text.strip()
            text = f"{number} — {name} ({details}) — {quantity} {unit} — {price} ₸"

            lots.append({
                "id": internal_id,     # ВАЖНО: сохраняем именно internal ID для формы подачи
                "text": text,
                "public_id": public_id
            })
        except Exception as e:
            logging.warning(f"⚠️ Ошибка при парсинге строки: {e}")
            continue

    logging.info(f"📦 Спарсено {len(lots)} лотов.")
    return driver,lots


def fast_jump_to_application(tender_url, saved_lot_ids, driver):
    match = re.search(r'/announce/index/(\d+)', tender_url)
    if not match:
        driver.quit()
        raise ValueError("❌ Невозможно извлечь app_id из ссылки.")

    app_id = match.group(1)
    create_url = f"https://v3bl.goszakup.gov.kz/ru/application/create/{app_id}"
    logging.info(f"🚀 Быстрый переход на {create_url}")
    
    driver.get(create_url)

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//form[contains(@action, "/application/create/")]'))
        )
        logging.info("✅ Форма заявки найдена, продолжаем заполнение.")
        fill_application_form(driver, saved_lot_ids)
        return True

    except Exception as e:
        logging.warning(f"❌ Ошибка при переходе: {e}")
        driver.quit()
        logging.warning(f"❌ Заявка недоступна: форма не найдена. Ошибка: {e}")
        return None

def fill_application_form(driver, saved_lot_ids):
    try:
        subject_select = Select(driver.find_element(By.NAME, "subject_address"))
        for option in subject_select.options:
            if option.get_attribute("value") != "0":
                subject_select.select_by_value(option.get_attribute("value"))
                break

        iik_select = Select(driver.find_element(By.NAME, "iik"))
        for option in iik_select.options:
            if option.get_attribute("value") != "0":
                iik_select.select_by_value(option.get_attribute("value"))
                break

        phone_input = driver.find_element(By.NAME, "contact_phone")
        phone_input.clear()
        phone_input.send_keys("87476083836")

        next_button = driver.find_element(By.ID, "next-without-captcha")
        next_button.click()

        time.sleep(3)
        select_and_add_lots(driver, saved_lot_ids)
        logging.info("✅ Форма успешно заполнена и отправлена.")
    except Exception as e:
        logging.error(f"❌ Ошибка при заполнении формы: {e}")
    finally:
        logging.info("🔚 Браузер закрыт.")

def select_and_add_lots(driver, saved_lot_ids):
    try:
        saved_lot_ids = [str(lid).strip() for lid in saved_lot_ids]
        logging.info(f"📌 Сохр. лоты (строки): {saved_lot_ids}")

        WebDriverWait(driver, 2).until(
            EC.presence_of_all_elements_located((By.XPATH, '//input[@type="checkbox" and @name="selectLots[]"]'))
        )
        checkboxes = driver.find_elements(By.XPATH, '//input[@type="checkbox" and @name="selectLots[]"]')
        logging.info(f"🔍 Найдено чекбоксов: {len(checkboxes)}")
    
        selected_count = 0
        for checkbox in checkboxes:
            lot_id = checkbox.get_attribute("value").strip()
            if lot_id in saved_lot_ids:
                checkbox.click()
                selected_count += 1
                # time.sleep(0.2)

        driver.find_element(By.ID, "add_lots").click()

        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.ID, "selected_lots"))
        )
        logging.info("🟢 Перешли во вкладку 'Просмотр выбранных лотов'.")

        next_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "next"))
        )
        next_button.click()
        logging.info("➡️ Нажата кнопка 'Далее'")

        WebDriverWait(driver, 1).until(
        EC.presence_of_element_located((By.XPATH, '//table[contains(@class, "table")]'))
)

        open_required_documents(driver)

    except Exception as e:
            logging.error(f"❌ Ошибка при выборе лотов: {e}")
            #driver.quit()


def open_required_documents(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//table[contains(@class, "table")]//a'))
        )

        # Берём первую ссылку с "Приложение 5"
        link = driver.find_element(By.XPATH, '//a[contains(text(), "Приложение 5")]')
        href = link.get_attribute("href")

        if href.startswith("/"):
            href = "https://v3bl.goszakup.gov.kz" + href

        logging.info(f"🔗 Переходим в ту же вкладку: {href}")
        driver.get(href)

        # После загрузки страницы нажимаем "Подписать"
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-add-signature"))
        )
        sign_button = driver.find_element(By.CLASS_NAME, "btn-add-signature")

        driver.execute_script("arguments[0].scrollIntoView(true);", sign_button)
        time.sleep(1)
        sign_button.click()
        logging.info("🖋 Нажата кнопка 'Подписать'")
        handle_ncalayer_popup(EDS_PATH, EDS_PASS)
    except Exception as e:
        logging.error(f"❌ Ошибка при переходе и попытке подписания: {e}")

def handle_ncalayer_popup(eds_path, eds_pass):
        logging.info("🕵️ Запускаем EdsManager для подписи")
        try:
            eds = EdsManager(eds_path, eds_pass)
            eds.execute_sign_by_eds()
            logging.info("✅ Подпись выполнена.")
        except Exception as e:
            logging.error(f"❌ Подпись не удалась: {e}")

# def open_required_documents(driver):
#     try:
#         WebDriverWait(driver, 10).until(
#             EC.presence_of_all_elements_located((By.XPATH, '//table[contains(@class, "table")]//a'))
#         )

#         links = driver.find_elements(By.XPATH, '//table[contains(@class, "table")]//a')

#         for link in links:
#             try:
#                 text = link.text.strip()
#                 href = link.get_attribute("href")
#                 if not href:
#                     continue

#                 if href.startswith("/"):
#                     href = "https://v3bl.goszakup.gov.kz" + href

#                 logging.info(f"🌐 Открываю документ: {text} — {href}")
#                 old_tabs = driver.window_handles

#                 driver.execute_script("window.open(arguments[0]);", href)
#                 WebDriverWait(driver, 5).until(lambda d: len(d.window_handles) > len(old_tabs))

#                 new_tab = [t for t in driver.window_handles if t not in old_tabs][0]
#                 driver.switch_to.window(new_tab)

#                 logging.info(f"🆕 Перешли во вкладку: {driver.current_url}")
#                 time.sleep(2)

#                 handle_document_page(driver, text)

#                 driver.close()
#                 driver.switch_to.window(old_tabs[0])

#             except Exception as e:
#                 logging.warning(f"⚠️ Ошибка при обработке ссылки '{text}': {e}")

#         logging.info("✅ Все нужные документы обработаны.")
#     except Exception as e:
#         logging.error(f"❌ Ошибка при открытии документов: {e}")


# def handle_document_page(driver, doc_name):
#     try:
#         if "Приложение 5" in doc_name:
#             WebDriverWait(driver, 10).until(
#                 EC.presence_of_element_located((By.CLASS_NAME, "btn-add-signature"))
#             )
#             sign_button = driver.find_element(By.CLASS_NAME, "btn-add-signature")

#             driver.execute_script("arguments[0].scrollIntoView(true);", sign_button)
#             time.sleep(1)

#             sign_button.click()
#             logging.info("🖋 Нажата кнопка 'Подписать'")

#             WebDriverWait(driver, 10).until(
#                 EC.presence_of_element_located((By.ID, "addSign"))
#             )
#             logging.info("📤 Подпись инициирована, форма 'addSign' найдена.")
#             time.sleep(3)

#         elif "Приложение 2" in doc_name:
#             logging.info("📄 Приложение 2: просмотр без действий.")

#         else:
#             logging.info(f"📎 Для '{doc_name}' действий не задано.")

#     except Exception as e:
#         logging.error(f"❌ Ошибка при обработке '{doc_name}': {e}")
