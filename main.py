#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StandUp - 久坐提醒桌面应用
为Mac设计的定时提醒应用，帮助用户避免久坐
使用tkinter实现，无需额外依赖
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import os
from datetime import datetime, timedelta
import subprocess
import sys


class StandUpApp:
    """主应用程序类"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.reminder_thread = None
        self.is_running = False
        self.settings_file = "settings.json"
        self.next_reminder_time = None
        self.countdown_timer = None
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化用户界面"""
        self.root.title("🐕 StandUp - 久坐提醒")
        self.root.geometry("500x600")
        self.root.minsize(400, 500)
        
        # 设置窗口图标
        try:
            icon_path = "/Users/xl/Desktop/projects/StandUp/src/icon/柴犬.png"
            if os.path.exists(icon_path):
                self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
        except Exception as e:
            print(f"设置图标失败: {e}")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="StandUp - 久坐提醒", 
                               font=("Arial", 18, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 设置组
        settings_frame = ttk.LabelFrame(main_frame, text="提醒设置", padding="10")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        settings_frame.columnconfigure(1, weight=1)
        
        # 提醒间隔设置
        ttk.Label(settings_frame, text="提醒间隔:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.interval_var = tk.IntVar(value=30)
        
        # 创建滑块和显示标签的框架
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        interval_frame.columnconfigure(0, weight=1)
        
        # 水平滑块
        self.interval_scale = ttk.Scale(interval_frame, from_=1, to=60, 
                                       variable=self.interval_var, orient=tk.HORIZONTAL,
                                       command=self.on_interval_change)
        self.interval_scale.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # 显示当前值的标签
        self.interval_label = ttk.Label(interval_frame, text="30 分钟", 
                                       font=("Arial", 10, "bold"), foreground="#2196F3")
        self.interval_label.grid(row=0, column=1)
        
        # 自动启动设置
        self.auto_start_var = tk.BooleanVar()
        self.auto_start_checkbox = ttk.Checkbutton(settings_frame, 
                                                  text="开机自动启动",
                                                  variable=self.auto_start_var)
        self.auto_start_checkbox.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 最小化到托盘设置
        self.minimize_to_tray_var = tk.BooleanVar(value=True)
        self.minimize_to_tray_checkbox = ttk.Checkbutton(settings_frame, 
                                                        text="最小化到系统托盘",
                                                        variable=self.minimize_to_tray_var)
        self.minimize_to_tray_checkbox.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(0, 20))
        
        self.start_button = ttk.Button(button_frame, text="开始提醒", 
                                      command=self.start_reminder,
                                      style="Start.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="停止提醒", 
                                     command=self.stop_reminder,
                                     style="Stop.TButton",
                                     state="disabled")
        self.stop_button.pack(side=tk.LEFT)
        
        # 状态显示
        self.status_var = tk.StringVar(value="状态: 未启动")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                                     font=("Arial", 10))
        self.status_label.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        # 倒计时显示
        countdown_frame = ttk.LabelFrame(main_frame, text="下次提醒倒计时", padding="10")
        countdown_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        countdown_frame.columnconfigure(0, weight=1)
        
        self.countdown_var = tk.StringVar(value="未启动")
        self.countdown_label = ttk.Label(countdown_frame, textvariable=self.countdown_var, 
                                        font=("Arial", 16, "bold"), foreground="#2E7D32")
        self.countdown_label.grid(row=0, column=0, pady=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(countdown_frame, variable=self.progress_var, 
                                           maximum=100, length=300)
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="活动日志", padding="10")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=50,
                                                 font=("Monaco", 10))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置按钮样式
        style = ttk.Style()
        style.configure("Start.TButton", foreground="white", background="#2196F3")
        style.configure("Stop.TButton", foreground="white", background="#2196F3")
        
        # 添加日志
        self.add_log("应用已启动")
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_interval_change(self, value):
        """滑块值变化时的回调函数"""
        interval = int(float(value))
        self.interval_label.config(text=f"{interval} 分钟")
        
    def start_reminder(self):
        """开始提醒"""
        if self.is_running:
            return
            
        interval = self.interval_var.get()
        self.is_running = True
        
        # 设置下次提醒时间
        self.next_reminder_time = datetime.now() + timedelta(minutes=interval)
        
        # 启动提醒线程
        self.reminder_thread = threading.Thread(target=self.reminder_loop, 
                                               args=(interval,), daemon=True)
        self.reminder_thread.start()
        
        # 启动倒计时更新
        self.start_countdown()
        
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set(f"状态: 运行中 (每{interval}分钟提醒)")
        self.add_log(f"开始提醒，间隔: {interval}分钟")
        
    def stop_reminder(self):
        """停止提醒"""
        self.is_running = False
        if self.reminder_thread:
            self.reminder_thread.join(timeout=1)
            
        # 停止倒计时
        self.stop_countdown()
        
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("状态: 已停止")
        self.countdown_var.set("未启动")
        self.progress_var.set(0)
        self.add_log("提醒已停止")
        
    def reminder_loop(self, interval_minutes):
        """提醒循环"""
        while self.is_running:
            time.sleep(interval_minutes * 60)  # 转换为秒
            if self.is_running:
                # 在主线程中显示提醒
                self.root.after(0, self.show_reminder)
                # 更新下次提醒时间
                self.next_reminder_time = datetime.now() + timedelta(minutes=interval_minutes)
                
    def show_reminder(self):
        """显示提醒对话框"""
        # 创建提醒窗口
        reminder_window = tk.Toplevel(self.root)
        reminder_window.title("久坐提醒")
        reminder_window.geometry("400x300")
        reminder_window.resizable(False, False)
        
        # 设置窗口置顶
        reminder_window.attributes('-topmost', True)
        reminder_window.grab_set()  # 模态窗口
        
        # 居中显示
        reminder_window.transient(self.root)
        reminder_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))
        
        # 主框架
        main_frame = ttk.Frame(reminder_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="您已经坐了太久了！", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 内容
        content_text = """是时候站起来活动一下了！

建议：
• 站起来走走
• 做几个伸展运动  
• 看看窗外
• 喝点水

请选择休息时间："""
        
        content_label = ttk.Label(main_frame, text=content_text, 
                                 font=("Arial", 11), justify=tk.LEFT)
        content_label.pack(pady=(0, 20))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(0, 10))
        
        # 休息按钮
        def rest_for_minutes(minutes):
            self.add_log(f"用户选择休息{minutes}分钟")
            reminder_window.destroy()
            
        ttk.Button(button_frame, text="休息5分钟", 
                  command=lambda: rest_for_minutes(5)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="休息10分钟", 
                  command=lambda: rest_for_minutes(10)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="休息15分钟", 
                  command=lambda: rest_for_minutes(15)).pack(side=tk.LEFT, padx=5)
        
        # 忽略按钮
        def ignore_reminder():
            self.add_log("用户忽略提醒")
            reminder_window.destroy()
            
        ttk.Button(main_frame, text="忽略", 
                  command=ignore_reminder).pack(pady=(10, 0))
        
        # 自动关闭定时器（30秒后自动关闭）
        def auto_close():
            if reminder_window.winfo_exists():
                self.add_log("提醒自动关闭")
                reminder_window.destroy()
                
        reminder_window.after(30000, auto_close)
        
    def start_countdown(self):
        """启动倒计时更新"""
        self.update_countdown()
        
    def stop_countdown(self):
        """停止倒计时更新"""
        if self.countdown_timer:
            self.root.after_cancel(self.countdown_timer)
            self.countdown_timer = None
            
    def update_countdown(self):
        """更新倒计时显示"""
        if not self.is_running or not self.next_reminder_time:
            return
            
        now = datetime.now()
        if now >= self.next_reminder_time:
            # 时间到了，重置倒计时
            interval = self.interval_var.get()
            self.next_reminder_time = now + timedelta(minutes=interval)
            self.countdown_var.set("提醒中...")
            self.progress_var.set(100)
        else:
            # 计算剩余时间
            remaining = self.next_reminder_time - now
            total_seconds = remaining.total_seconds()
            
            # 格式化显示
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            
            if hours > 0:
                countdown_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                countdown_text = f"{minutes:02d}:{seconds:02d}"
                
            self.countdown_var.set(countdown_text)
            
            # 更新进度条
            interval_minutes = self.interval_var.get()
            total_interval_seconds = interval_minutes * 60
            progress = ((total_interval_seconds - total_seconds) / total_interval_seconds) * 100
            self.progress_var.set(progress)
            
            # 根据剩余时间改变颜色
            if total_seconds < 300:  # 最后5分钟
                self.countdown_label.config(foreground="#D32F2F")  # 红色
            elif total_seconds < 600:  # 最后10分钟
                self.countdown_label.config(foreground="#F57C00")  # 橙色
            else:
                self.countdown_label.config(foreground="#2E7D32")  # 绿色
        
        # 设置下次更新（每秒更新一次）
        self.countdown_timer = self.root.after(1000, self.update_countdown)
        
    def add_log(self, message):
        """添加日志"""
        current_time = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{current_time}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)  # 自动滚动到底部
        
    def load_settings(self):
        """加载设置"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.interval_var.set(settings.get('interval', 30))
                    self.auto_start_var.set(settings.get('auto_start', False))
                    self.minimize_to_tray_var.set(settings.get('minimize_to_tray', True))
        except Exception as e:
            self.add_log(f"加载设置失败: {e}")
            
    def save_settings(self):
        """保存设置"""
        try:
            settings = {
                'interval': self.interval_var.get(),
                'auto_start': self.auto_start_var.get(),
                'minimize_to_tray': self.minimize_to_tray_var.get()
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.add_log(f"保存设置失败: {e}")
            
    def on_closing(self):
        """窗口关闭事件"""
        if self.minimize_to_tray_var.get():
            # 最小化到托盘（在macOS上实际是隐藏窗口）
            self.root.withdraw()
            self.add_log("应用已最小化")
        else:
            self.quit_app()
            
    def quit_app(self):
        """退出应用"""
        self.save_settings()
        self.stop_reminder()
        self.root.quit()
        self.root.destroy()
        
    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    """主函数"""
    app = StandUpApp()
    app.run()


if __name__ == "__main__":
    main()