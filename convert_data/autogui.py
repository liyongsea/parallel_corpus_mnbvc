import keyboard
import pyautogui
import time


while True:
    keyboard.wait('`')
    print('start')
    # while 1:
    #     pyautogui.press('down')
    #     time.sleep(0.1)
    #     pyautogui.press('enter')
    #     time.sleep(5)
            
    pyautogui.press('enter')
    time.sleep(0.05)
    pyautogui.press('f12')
    time.sleep(0.5)
    pyautogui.press('tab')
    time.sleep(0.1)
    pyautogui.press('down')

    time.sleep(0.02)
    pyautogui.press('up')
    time.sleep(0.02)
    pyautogui.press('up')
    time.sleep(0.02)

    pyautogui.press('enter')
    time.sleep(0.1)
    pyautogui.press('enter')

    time.sleep(0.8)
    pyautogui.keyDown('alt')
    pyautogui.press('f4')
    pyautogui.keyUp('alt')

    time.sleep(0.6)

    pyautogui.press('delete')
    time.sleep(0.6)



    # keyboard.read_key()