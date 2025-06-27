import uiautomation as auto

dlg = auto.WindowControl(searchDepth=1, Name="Формирование ЭЦП")
dlg.SetActive()

target = dlg.find_first_descendant(lambda c: "IIN" in c.Name)
if target:
    print("✔️ Найден элемент:", target.Name)
    target.Click()
else:
    print("❌ Элемент с IIN не найден")
