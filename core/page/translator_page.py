import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import traceback

import customtkinter as ctk

from config import config_manager
from core.translator import Translator
from core.subtitle_translator import SmartSubtitleTranslator

class TranslatorPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        # 设置文件路径列表和专用词汇
        self.file_paths = []
        self.custom_vocab = []

        # 创建页面布局
        self.create_file_section()
        self.create_language_section()
        self.create_api_section()
        self.create_translation_settings()
        self.create_translate_button()
        self.create_progress_section()

        # 初始化API设置
        self.init_api_settings()

    def create_file_section(self):
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(padx=10, pady=10, fill="x")

        ctk.CTkLabel(file_frame, text="选择字幕文件:").pack(side="left", padx=10)

        select_button = ctk.CTkButton(
            file_frame, 
            text="浏览文件", 
            command=self.select_files,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        select_button.pack(side="left", padx=10)

        # 文件列表
        self.file_listbox = tk.Listbox(
            self, 
            selectmode=tk.MULTIPLE, 
            height=10
        )
        self.file_listbox.pack(padx=10, pady=10, fill="both", expand=True)

    def create_language_section(self):
        lang_frame = ctk.CTkFrame(self)
        lang_frame.pack(padx=10, pady=10, fill="x")

        languages = ["English", "Chinese", "Japanese", "Korean", "Spanish", "French"]

        # 源语言
        ctk.CTkLabel(lang_frame, text="源语言:").pack(side="left", padx=5)
        self.source_lang = ctk.CTkComboBox(
            lang_frame, 
            values=languages,
            width=150
        )
        self.source_lang.pack(side="left", padx=5)
        self.source_lang.set("English")

        # 目标语言
        ctk.CTkLabel(lang_frame, text="目标语言:").pack(side="left", padx=5)
        self.target_lang = ctk.CTkComboBox(
            lang_frame, 
            values=languages,
            width=150
        )
        self.target_lang.pack(side="left", padx=5)
        self.target_lang.set("Chinese")

    def create_api_section(self):
        api_frame = ctk.CTkFrame(self)
        api_frame.pack(padx=10, pady=10, fill="x")

        # API选择
        ctk.CTkLabel(api_frame, text="API选择:").pack(side="left", padx=5)
        self.api_select = ctk.CTkComboBox(
            api_frame, 
            values=[api['name'] for api in config_manager.get_apis()],
            width=200,
            command=self.update_models
        )
        self.api_select.pack(side="left", padx=5)

        # 模型选择
        ctk.CTkLabel(api_frame, text="模型:").pack(side="left", padx=5)
        self.model_select = ctk.CTkComboBox(
            api_frame, 
            width=150
        )
        self.model_select.pack(side="left", padx=5)

        # API Key
        ctk.CTkLabel(api_frame, text="API Key:").pack(side="left", padx=5)
        self.api_key_entry = ctk.CTkEntry(
            api_frame, 
            show="*", 
            width=250
        )
        self.api_key_entry.pack(side="left", padx=5)

        # 添加API按钮
        add_api_button = ctk.CTkButton(
            api_frame, 
            text="+", 
            width=30,
            command=self.show_add_api_dialog
        )
        add_api_button.pack(side="left", padx=5)

    def create_translation_settings(self):
        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(padx=10, pady=10, fill="x")

        # 并发数设置
        ctk.CTkLabel(settings_frame, text="并发数:").pack(side="left", padx=5)
        self.concurrent_workers = ctk.CTkEntry(settings_frame, width=100)
        self.concurrent_workers.pack(side="left", padx=5)
        self.concurrent_workers.insert(0, "5")

        # 温度设置
        ctk.CTkLabel(settings_frame, text="温度:").pack(side="left", padx=5)
        self.temperature = ctk.CTkEntry(settings_frame, width=100)
        self.temperature.pack(side="left", padx=5)
        self.temperature.insert(0, "0.7")

        # 专用词汇按钮
        add_vocab_button = ctk.CTkButton(
            settings_frame, 
            text="添加专用词汇", 
            command=self.show_add_vocab_dialog,
            fg_color="#FFA500",
            hover_color="#FF8C00"
        )
        add_vocab_button.pack(side="left", padx=5)
        
        ctk.CTkLabel(settings_frame, text="翻译模式:").pack(side="left", padx=5)
        self.translate_mode = ctk.CTkComboBox(
            settings_frame,
            values=["逐条上下文翻译", "按说话人分组"],
            width=150
        )
        self.translate_mode.pack(side="left", padx=5)
        self.translate_mode.set("按说话人分组")

    def create_translate_button(self):
        self.translate_button = ctk.CTkButton(
            self, 
            text="开始翻译", 
            command=self.start_translation,
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        self.translate_button.pack(padx=10, pady=10)

    def create_progress_section(self):
        # 进度条
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(padx=10, pady=10, fill="x")
        self.progress.set(0)

        # 状态标签
        self.status_label = ctk.CTkLabel(
            self, 
            text="准备就绪", 
            text_color="green"
        )
        self.status_label.pack(padx=10, pady=10)

        # 详细信息标签
        self.detail_label = ctk.CTkLabel(
            self, 
            text="", 
            text_color="blue"
        )
        self.detail_label.pack(padx=10, pady=10)

        # 文件级别进度条
        self.file_progress = ctk.CTkProgressBar(self)
        self.file_progress.pack(padx=10, pady=10, fill="x")
        self.file_progress.set(0)

        # 状态信息标签
        self.stats_label = ctk.CTkLabel(
            self, 
            text="", 
            text_color="purple"
        )
        self.stats_label.pack(padx=10, pady=10)

        self.group_progress_labels = []
        self.group_progress_frame = ctk.CTkFrame(self)
        self.group_progress_frame.pack(padx=10, pady=5, fill="x")
        # 初始化时不创建分组标签，翻译开始时动态生成

    def init_api_settings(self):
        # 设置默认API和API Key
        last_used_api = config_manager.get_last_used_api()
        self.api_select.set(last_used_api)
        self.update_models(last_used_api)
        
        # 从配置中获取上次使用的API Key
        last_api_key = config_manager.get_api_key(last_used_api)
        self.api_key_entry.insert(0, last_api_key)

    def select_files(self):
        """选择字幕文件"""
        filetypes = [("Subtitle Files", "*.srt *.txt")]
        files = filedialog.askopenfilenames(filetypes=filetypes)
        
        # 清空之前的列表
        self.file_listbox.delete(0, tk.END)
        self.file_paths.clear()
        
        # 添加新选择的文件
        for file in files:
            self.file_listbox.insert(tk.END, os.path.basename(file))
            self.file_paths.append(file)

    def update_models(self, api_name):
        """更新模型下拉框"""
        models = config_manager.get_models(api_name)
        self.model_select.configure(values=models)
        if models:
            self.model_select.set(models[0])

    def show_add_vocab_dialog(self):
        """显示添加专用词汇对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("添加专用词汇")
        dialog.geometry("400x500")

        # 说明标签
        ctk.CTkLabel(
            dialog, 
            text="请输入专用词汇，每行一个。\n例如：\n苹果 Apple\n微软 Microsoft\n谷歌 Google",
            wraplength=350
        ).pack(pady=10)

        # 文本输入框
        vocab_text = ctk.CTkTextbox(dialog, width=350, height=300)
        vocab_text.pack(pady=10)

        def save_vocab():
            """保存专用词汇"""
            # 获取输入的词汇，并去除空行
            vocabs = [
                v.strip() for v in vocab_text.get("1.0", tk.END).split('\n') 
                if v.strip()
            ]
            
            # 更新专用词汇列表
            self.custom_vocab = vocabs
            
            # 提示保存成功
            messagebox.showinfo("提示", f"成功添加 {len(vocabs)} 个专用词汇")
            
            dialog.destroy()

        # 保存按钮
        save_button = ctk.CTkButton(
            dialog, 
            text="保存", 
            command=save_vocab,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        save_button.pack(pady=10)

    def show_add_api_dialog(self):
        """显示添加API对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("添加新API")
        dialog.geometry("400x500")

        # API名称
        ctk.CTkLabel(dialog, text="API名称:").pack(pady=5)
        name_entry = ctk.CTkEntry(dialog, width=300)
        name_entry.pack(pady=5)

        # 基础URL
        ctk.CTkLabel(dialog, text="基础URL:").pack(pady=5)
        url_entry = ctk.CTkEntry(dialog, width=300)
        url_entry.pack(pady=5)

        # API类型
        ctk.CTkLabel(dialog, text="API类型:").pack(pady=5)
        api_type_select = ctk.CTkComboBox(
            dialog, 
            values=["openai", "azure", "custom"],
            width=300
        )
        api_type_select.pack(pady=5)

        # 模型列表
        ctk.CTkLabel(dialog, text="模型(逗号分隔):").pack(pady=5)
        models_entry = ctk.CTkEntry(dialog, width=300)
        models_entry.pack(pady=5)

        def save_api():
            try:
                name = name_entry.get()
                url = url_entry.get()
                api_type = api_type_select.get()
                models = [m.strip() for m in models_entry.get().split(',')]

                config_manager.add_api(name, url, api_type, models)
                
                # 更新API选择下拉框
                apis = [api['name'] for api in config_manager.get_apis()]
                self.api_select.configure(values=apis)
                
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", str(e))

        save_button = ctk.CTkButton(dialog, text="保存", command=save_api)
        save_button.pack(pady=10)

    def start_translation(self):
        """开始翻译过程"""
        # 检查是否选择了文件
        if not self.file_paths:
            messagebox.showwarning("警告", "请先选择字幕文件")
            return

        # 检查API Key
        api_key = self.api_key_entry.get()
        api_name = self.api_select.get()
        
        if not api_key:
            messagebox.showwarning("警告", "请输入API Key")
            return

        # 保存API Key到配置文件
        config_manager.save_api_key(api_name, api_key)
        
        # 记录最后使用的API
        config_manager.set_last_used_api(api_name)

        # 多线程执行翻译
        translation_thread = threading.Thread(
            target=self.run_translation, 
            daemon=True
        )
        translation_thread.start()

    def run_translation(self):
        """翻译执行逻辑"""
        try:
            # 获取选择的API配置
            api_name = self.api_select.get()
            api_config = next(
                (api for api in config_manager.get_apis() if api['name'] == api_name), 
                None
            )
            
            if not api_config:
                raise ValueError("未找到选定的API配置")

            # 准备翻译配置
            translator_config = {
                'base_url': api_config['base_url'],
                'api_key': self.api_key_entry.get(),
                'api_type': api_config['api_type'],
                'model': self.model_select.get()
            }

            # 创建翻译器
            translator = Translator(translator_config)
            
            # 获取并发数和温度
            try:
                max_workers = int(self.concurrent_workers.get())
                temperature = float(self.temperature.get())
            except ValueError:
                messagebox.showwarning("警告", "并发数和温度必须是数字")
                return

            # 创建字幕翻译器，添加进度回调
            subtitle_translator = SmartSubtitleTranslator(
                translator=translator, 
                max_workers=max_workers,
                custom_vocab=self.custom_vocab,
                progress_callback=self.update_translation_progress,  # 只添加这一行
                temperature=temperature  # 新增
            )

            # 准备处理文件
            total_files = len(self.file_paths)
            analysis_reports = []

            # 遍历文件并翻译
            for index, file_path in enumerate(self.file_paths, 1):
                try:
                    # 更新文件级进度
                    self.update_file_progress(index, total_files, file_path)
                    
                    # 处理字幕
                    output_path, analysis_path = subtitle_translator.process_subtitle_file_grouped(
                        file_path,
                        self.target_lang.get()
                    )
                    
                    # 收集分析报告
                    with open(analysis_path, 'r', encoding='utf-8') as f:
                        analysis_reports.append({
                            'file': os.path.basename(file_path),
                            'report': f.read()
                        })

                except Exception as e:
                    print(f"处理 {file_path} 时出错: {e}")
                    self.update_status(f"处理 {os.path.basename(file_path)} 时出错", "red")
                    messagebox.showwarning("警告", f"处理 {os.path.basename(file_path)} 时出错: {e}")

            # 完成处理
            self.progress.set(1)
            self.status_label.configure(text="翻译完成", text_color="green")
            self.detail_label.configure(text="所有文件处理完成")
            
            # 显示分析报告
            self.show_analysis_reports(analysis_reports)

        except Exception as e:
            self.progress.set(0)
            self.status_label.configure(text="翻译失败", text_color="red")
            messagebox.showerror("错误", str(e))
            traceback.print_exc()

    def update_file_progress(self, current_file, total_files, file_path):
        """更新文件级别进度"""
        try:
            # 更新总体进度
            overall_progress = (current_file - 1) / total_files
            self.progress.set(overall_progress)
            
            # 更新状态信息
            self.status_label.configure(
                text=f"处理文件 {current_file}/{total_files}: {os.path.basename(file_path)}", 
                text_color="blue"
            )
            
            # 重置文件级进度条
            self.file_progress.set(0)
            
            # 更新详细信息
            self.detail_label.configure(text=f"正在处理: {os.path.basename(file_path)}")
            
            # 强制更新UI
            self.update()
            
        except Exception as e:
            print(f"更新文件进度失败: {e}")

    def update_status(self, message, color="black"):
        """更新状态信息"""
        try:
            self.status_label.configure(text=message, text_color=color)
            self.update()
        except Exception as e:
            print(f"更新状态失败: {e}")

    def update_translation_progress(self, stage, current, total, extra_info=""):
        def _update():
            if stage.startswith("group_"):
                # 动态创建分组标签（只在第一次调用时）
                if not self.group_progress_labels or len(self.group_progress_labels) != total:
                    # 清空旧标签
                    for lbl in self.group_progress_labels:
                        try:
                            if lbl.winfo_exists():
                                lbl.destroy()
                        except Exception as e:
                            print(f"分组标签销毁异常: {e}")
                    self.group_progress_labels = []
                    for i in range(total):
                        lbl = ctk.CTkLabel(self.group_progress_frame, text=f"第{i+1}组：等待中", text_color="gray")
                        lbl.pack(anchor="w")
                        self.group_progress_labels.append(lbl)
                # 更新当前分组标签
                idx = current - 1
                if 0 <= idx < len(self.group_progress_labels):
                    color = "blue"
                    if "done" in stage:
                        color = "green"
                    elif "error" in stage:
                        color = "red"
                    elif "retry" in stage:
                        color = "orange"
                    self.group_progress_labels[idx].configure(text=extra_info, text_color=color)
                self.update()
            else:
                if stage == "reading_file":
                    self.detail_label.configure(text="正在读取文件...")
                    self.stats_label.configure(text="")
                elif stage == "parsing_subtitles":
                    self.detail_label.configure(text="正在解析字幕格式...")
                elif stage == "content_analysis":
                    self.detail_label.configure(text="正在分析内容...")
                    self.stats_label.configure(text="")
                elif stage == "translation_start":
                    self.detail_label.configure(text=f"开始翻译，共{total}条字幕")
                    self.stats_label.configure(text="")
                elif stage == "translating":
                    if total > 0:
                        progress = current / total
                        self.file_progress.set(progress)
                        self.detail_label.configure(text=f"正在翻译... {current}/{total}")
                        self.stats_label.configure(text=extra_info)
                elif stage == "retry":
                    self.detail_label.configure(text=f"重试中... {current}/{total}")
                    self.stats_label.configure(text=extra_info)
                elif stage == "failed":
                    self.detail_label.configure(text=f"翻译失败... {current}/{total}")
                    self.stats_label.configure(text=extra_info)
                elif stage == "rebuilding":
                    self.detail_label.configure(text="正在重建SRT文件...")
                    self.stats_label.configure(text="")
                    self.file_progress.set(1.0)
                elif stage == "completed":
                    self.detail_label.configure(text="文件处理完成")
                    self.stats_label.configure(text=extra_info)
                    self.file_progress.set(1.0)
                elif stage == "error":
                    self.detail_label.configure(text="处理出错")
                    self.stats_label.configure(text=extra_info)

                # 强制更新UI
                self.update()

        self.after(0, _update)

    def show_analysis_reports(self, reports):
        """显示多个文件的分析报告"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("内容分析报告")
        dialog.geometry("800x600")

        # 创建笔记本（选项卡）控件
        notebook = ctk.CTkTabview(dialog)
        notebook.pack(padx=10, pady=10, fill="both", expand=True)

        # 为每个文件创建一个选项卡
        for report in reports:
            tab = notebook.add(report['file'])
            text_widget = ctk.CTkTextbox(tab, width=760, height=500)
            text_widget.pack(padx=10, pady=10)
            text_widget.insert('1.0', report['report'])
            text_widget.configure(state='disabled')

        # 关闭按钮
        close_button = ctk.CTkButton(
            dialog, 
            text="关闭", 
            command=dialog.destroy
        )
        close_button.pack(pady=10)

    def clear_group_progress(self):
        for lbl in self.group_progress_labels:
            try:
                if lbl.winfo_exists():
                    lbl.destroy()
            except Exception as e:
                print(f"分组标签销毁异常: {e}")
        self.group_progress_labels = []
