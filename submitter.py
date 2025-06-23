# submitter.py

import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from parser import fast_jump_to_application

def submit_tender(key_path, lot_ids, tender_url):
    driver = fast_jump_to_application(tender_url)
    if not driver:
        raise Exception("Не удалось открыть форму подачи заявки.")

    try:
        for lot_id in lot_ids:
            checkbox = driver.find_element(By.XPATH, f'//input[@type="checkbox" and @value="{lot_id}"]')
            checkbox.click()
            logging.info(f"✅ Лот {lot_id} выбран")

        time.sleep(1)

        # Нажать на кнопку "Подписать и подать"
        submit_button = driver.find_element(By.XPATH, '//button[contains(text(),"Подписать и подать")]')
        submit_button.click()
        logging.info("🖊️ Клик по кнопке Подписать")

        # ⏳ Ждём загрузки NCALayer
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "signDialog"))
        )

        # Вызываем NCALayer через JavaScript
        driver.execute_script(f"signXml('{key_path}', 'password')")  # ⚠️ здесь 'password' — замени при необходимости

        # ⏳ Ждём завершения подписи
        time.sleep(5)
        logging.info("✅ Заявка подана")

    finally:
        driver.quit()
