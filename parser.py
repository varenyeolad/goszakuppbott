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

logging.basicConfig(level=logging.INFO)

CHROME_PROFILE_PATH = "C:/Users/aizha/goszakup-profile"
CHROMEDRIVER_PATH = "C:/Users/aizha/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe"

def init_driver():
    logging.info("🔧 Настройка Chrome профиля...")
    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={CHROME_PROFILE_PATH}")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=chrome_options)

def parse_lots(url):
    driver = init_driver()
    logging.info(f"🌐 Переход на {url}")
    driver.get(url)

    try:
        logging.info("⏳ Ожидание загрузки таблицы с лотами...")
        WebDriverWait(driver, 15).until(
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
            lot_a = tds[1].find_element(By.CLASS_NAME, "btn-select-lot")
            lot_id = lot_a.get_attribute("data-lot-id").strip()

            number = tds[1].text.strip().split()[0]
            name = tds[3].text.strip()
            details = tds[4].text.strip()
            quantity = tds[6].text.strip()
            unit = tds[7].text.strip()
            price = tds[8].text.strip()
            text = f"{number} — {name} ({details}) — {quantity} {unit} — {price} ₸"

            lots.append({
                "id": lot_id,
                "text": text
            })
        except Exception as e:
            logging.warning(f"⚠️ Ошибка при парсинге строки: {e}")
            continue

    driver.quit()
    logging.info(f"📦 Спарсено {len(lots)} лотов.")
    return lots

def fast_jump_to_application(tender_url, saved_lot_ids):
    driver = init_driver()

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
    except Exception as e:
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

        time.sleep(5)
        select_and_add_lots(driver, saved_lot_ids)
        logging.info("✅ Форма успешно заполнена и отправлена.")
    except Exception as e:
        logging.error(f"❌ Ошибка при заполнении формы: {e}")
    finally:
        driver.quit()
        logging.info("🔚 Браузер закрыт.")

def select_and_add_lots(driver, saved_lot_ids):
    try:
        logging.info("⏳ Ожидаем появления чекбоксов лотов...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//input[@type="checkbox" and @name="selectLots[]"]'))
        )
        checkboxes = driver.find_elements(By.XPATH, '//input[@type="checkbox" and @name="selectLots[]"]')

        logging.info(f"📝 Найдено {len(checkboxes)} лотов. Выбираем только сохранённые...")
        for checkbox in checkboxes:
            lot_id = checkbox.get_attribute("value")
            if lot_id in saved_lot_ids and not checkbox.is_selected():
                checkbox.click()
                time.sleep(0.2)

        logging.info("➕ Нажимаем кнопку 'Добавить выбранные'")
        add_button = driver.find_element(By.ID, "add_lots")
        add_button.click()
        time.sleep(3)

        logging.info("✅ Лоты добавлены успешно.")
    except Exception as e:
        logging.error(f"❌ Ошибка при выборе лотов: {e}")
        driver.quit()