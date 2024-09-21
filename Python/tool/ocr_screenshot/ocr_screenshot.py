import tkinter as tk
from tkinter import messagebox
import pyautogui
from PIL import Image
import io
import base64
import requests
import hashlib
import json
import random
import pyperclip
import threading
import keyboard  # 用于监听全局快捷键
import pystray
from pystray import MenuItem as item
from PIL import Image as PILImage
import time
import logging
import queue
import sys
import os

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ocr_screenshot.log"),
        logging.StreamHandler()
    ]
)

def resource_path(relative_path):
    """ 获取打包后资源文件的绝对路径 """
    try:
        # PyInstaller创建临时文件夹并存储路径到 _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class OCR:
    @staticmethod
    def make_body_and_sign(image_base64: str):
        body_obj = {
            "images": [
                {
                    "data": image_base64,
                    "dataId": "1",
                    "type": 2
                }
            ],
            "nonce": random.randint(0, int(1e5)),
            "secretId": "Inner_40731a6efece4c2e992c0d670222e6da",
            "timestamp": int(time.time() * 1000)
        }
        body = json.dumps(body_obj)
        text = body + '43e7a66431b14c8f856a8e889070c19b'  # 请替换为您自己的密钥
        sign = hashlib.md5(text.encode('utf-8')).hexdigest()
        return body, sign

    @staticmethod
    def get_result(image_data: bytes):
        encoded_string = base64.b64encode(image_data).decode('utf-8')
        body, sign = OCR.make_body_and_sign(encoded_string)
        headers = {
            'CX-Signature': sign,
            'Content-Type': 'application/json;charset=utf-8'
        }
        try:
            res = requests.post('http://ai.chaoxing.com/api/v1/ocr/common/sync', data=body, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            logging.info("OCR API响应: %s", data)
            texts = data.get('data', [])
            if not texts:
                return "未识别到文字。"
            first_data = texts[0]
            if isinstance(first_data, list):
                # texts[0] 是列表
                result = '\n'.join(item.get('text', '') for item in first_data if isinstance(item, dict))
            elif isinstance(first_data, dict):
                # texts[0] 是字典
                result = first_data.get('text', '')
            else:
                result = ""
            return result if result.strip() else "未识别到文字。"
        except requests.RequestException as e:
            logging.error("网络错误: %s", e)
            return f"网络错误: {e}"
        except (KeyError, TypeError) as e:
            logging.error("解析错误: %s", e)
            return f"解析错误: {e}"
        except Exception as e:
            logging.error("未知错误: %s", e)
            return f"未知错误: {e}"


class ScreenshotOverlay(tk.Toplevel):
    def __init__(self, master, task_queue):
        super().__init__(master)
        self.task_queue = task_queue
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.setup_overlay()
        self.create_canvas()
        self.bind_events()

    def setup_overlay(self):
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.3)  # 设置透明度
        self.attributes("-topmost", True)  # 保持窗口最前
        self.config(cursor="cross")  # 设置鼠标为十字形
        self.overrideredirect(True)  # 移除窗口边框和标题栏

    def create_canvas(self):
        self.canvas = tk.Canvas(self, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def on_button_press(self, event):
        self.start_x = self.winfo_pointerx() - self.winfo_rootx()
        self.start_y = self.winfo_pointery() - self.winfo_rooty()
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2
        )

    def on_mouse_drag(self, event):
        cur_x = self.winfo_pointerx() - self.winfo_rootx()
        cur_y = self.winfo_pointery() - self.winfo_rooty()
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x = self.winfo_pointerx() - self.winfo_rootx()
        end_y = self.winfo_pointery() - self.winfo_rooty()
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        # 最小截图区域限制
        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            self.destroy()
            return

        region = (self.winfo_rootx() + x1, self.winfo_rooty() + y1, x2 - x1, y2 - y1)
        self.destroy()
        threading.Thread(target=self.process_screenshot, args=(region,), daemon=True).start()

    def process_screenshot(self, region):
        try:
            logging.info("开始截图区域: %s", region)
            screenshot = pyautogui.screenshot(region=region)
            output = io.BytesIO()
            screenshot.save(output, format="PNG")
            screenshot_bytes = output.getvalue()

            result = OCR.get_result(screenshot_bytes)
            if result and not result.startswith(("网络错误", "解析错误", "未知错误")):
                pyperclip.copy(result)
                logging.info("识别的文字已复制到剪贴板。")
            else:
                logging.warning("OCR结果: %s", result or "未识别到文字。")
        except Exception as e:
            logging.error("处理截图时出错: %s", e)
        finally:
            # 将退出任务放入队列，由主线程处理
            self.task_queue.put('screenshot_done')


class TrayIcon:
    def __init__(self, stop_event):
        self.stop_event = stop_event
        # 创建一个简单的图标，您可以使用自己的图标
        icon_path = resource_path('OCR识别.png')
        if not os.path.exists(icon_path):
            logging.error(f"图标文件未找到: {icon_path}")
            # 使用默认图标
            image = PILImage.new('RGB', (64, 64), color='blue')
        else:
            image = PILImage.open(icon_path)
        menu = (item('退出', self.exit_app),)
        self.icon = pystray.Icon("OCR_Screenshot", image, "OCR Screenshot", menu)
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def exit_app(self, icon, item):
        logging.info("通过托盘图标退出应用程序。")
        self.icon.stop()
        self.stop_event.set()


def run_tray_icon(stop_event):
    TrayIcon(stop_event)


def start_listener(task_queue, stop_event):
    def on_hotkey():
        logging.info("快捷键被按下，加入截图任务。")
        task_queue.put('screenshot')

    # 注册全局快捷键 Ctrl+Alt+A
    keyboard.add_hotkey('ctrl+alt+a', on_hotkey)
    logging.info("已注册快捷键 Ctrl+Alt+A 进行截图。")
    keyboard.wait()


def main():
    task_queue = queue.Queue()
    stop_event = threading.Event()

    # 启动托盘图标
    threading.Thread(target=run_tray_icon, args=(stop_event,), daemon=True).start()

    # 启动快捷键监听器线程
    listener_thread = threading.Thread(target=start_listener, args=(task_queue, stop_event), daemon=True)
    listener_thread.start()

    # 初始化Tkinter root窗口（隐藏）
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    # 定义定期检查任务队列的函数
    def process_tasks():
        while not task_queue.empty():
            task = task_queue.get()
            if task == 'screenshot':
                # 创建并显示截图覆盖层
                overlay = ScreenshotOverlay(root, task_queue)
        if not stop_event.is_set():
            root.after(100, process_tasks)  # 每100毫秒检查一次
        else:
            root.quit()

    # 启动任务处理
    process_tasks()

    # 启动Tkinter主循环
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass

    logging.info("应用程序已终止。")


if __name__ == "__main__":
    main()
