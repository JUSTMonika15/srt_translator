import os
import re
import time
import random
import traceback
import concurrent.futures  # 添加这个导入
from typing import List, Tuple, Optional

import tiktoken

class Subtitle:
    def __init__(self, index, timestamp_in, timestamp_out, text):
        self.index = index
        self.timestamp_in = timestamp_in
        self.timestamp_out = timestamp_out
        self.text = text

class SmartSubtitleTranslator:
    def __init__(self, translator, max_workers=5, max_tokens=2000, 
                 max_retries=3, retry_delay_base=30, custom_vocab=None, progress_callback=None, temperature=0.7):
        self.translator = translator
        self.max_workers = max_workers
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        self.context_summary = None
        self.target_language = None
        self.source_language = None
        self.custom_vocab = custom_vocab or []
        self.progress_callback = progress_callback  # 只添加这一行
        self.temperature = temperature

    def _update_progress(self, stage, current=0, total=0, extra_info=""):
        """内部进度更新方法"""
        if self.progress_callback:
            try:
                self.progress_callback(stage, current, total, extra_info)
            except Exception as e:
                print(f"进度回调出错: {e}")

    def count_tokens(self, text):
        try:
            tokenizer = tiktoken.get_encoding("cl100k_base")
            return len(tokenizer.encode(text))
        except ImportError:
            return len(text.split())

    def parse_subtitles(self, content):
        """解析SRT文件"""
        # 处理不同的换行符和编码问题
        content = content.replace('\r\n', '\n')
        
        pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)'
        matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        
        subtitles = []
        for match in matches:
            index, timestamp_in, timestamp_out, text = match
            subtitles.append(Subtitle(
                index=index, 
                timestamp_in=timestamp_in, 
                timestamp_out=timestamp_out, 
                text=text.strip()
            ))
        
        return subtitles

    def analyze_content(self, full_text):
        """第一阶段：分析整体内容，生成上下文摘要"""
        # 如果文本太短，直接返回None
        if len(full_text.strip()) < 50:
            print("文本内容过短，无法进行分析")
            return None
    
        # 准备专用词汇部分
        vocab_section = "\n专用词汇列表（如有）：\n" + "\n".join(self.custom_vocab) if self.custom_vocab else ""
    
        analysis_prompt = f"""
        请以专业的角度分析以下字幕文本的整体内容，并提供详细且精准的分析报告：
    
        1. 内容类型（如：电视剧、纪录片、访谈、教育视频等）
        2. 主要主题和核心情节
        3. 关键人物或角色特点，以及他们的固定翻译（同时列出英文原文和译文）
        4. 特定的地点或场景，固定翻译（同时列出英文原文和译文）
        5. 未包含在以下专用词汇列表中的新的人名，地名，专有名词
        （如果发现新的此类词语，请列出其英文原文及对应的建议译文，格式为中文 空格 英文 如：黄昏草场 Duskmeadow，中间不要加任何东西，方便复制，以便后续翻译固定，然后解释应该放在术语表的哪一个分类当中）
        6. 语言风格和语气特点
        7. 可能的目标受众
    
        {vocab_section}
    
        请用简洁、专业的语言总结这些信息，为后续翻译提供指导。
    
        文本内容（前2500字）：
        {full_text[:2500]}
        """
        
        try:
            context_summary = self.translator.translate(
                text=full_text[:2500],  # 只分析前2500字
                system_prompt=analysis_prompt,
                temperature=0.3 
            )
            
            # 检查返回内容是否为空
            if not context_summary or context_summary.strip() == '':
                print("内容分析返回为空")
                return None
            
            return context_summary
        except Exception as e:
            print(f"内容分析失败: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return None


    def translate_with_timeout(self, text, system_prompt, temperature=0.7, timeout_seconds=60):
        """带超时的翻译方法"""
        def translate_task():
            return self.translator.translate(
                text=text,
                system_prompt=system_prompt,
                temperature=temperature
            )
        
        # 使用线程池执行翻译，带超时
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(translate_task)
            try:
                return future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                raise Exception(f"翻译超时 ({timeout_seconds}秒)")
    
    def translate_with_context(self, subtitles):
        """第二阶段：基于上下文进行批量翻译"""
        if not self.context_summary:
            print("警告：未进行内容分析，将使用默认翻译")
            self.context_summary = f"这是一个需要翻译的字幕文件。请保持原文的语气和风格。"

        # 创建一个用于存储已翻译结果的共享列表
        translated_texts = [None] * len(subtitles)

        def safe_translate_subtitle(subtitle, context_summary, subtitles, translated_texts):
            """
            安全的字幕翻译方法，支持部分并发翻译
            
            :param subtitle: 当前字幕对象
            :param context_summary: 上下文摘要
            :param subtitles: 所有字幕列表
            :param translated_texts: 共享的翻译结果列表
            :return: 翻译结果或错误信息
            """
            current_index = subtitles.index(subtitle)
            
            # 获取已翻译的前文（如果有）
            prev_context = []
            for i in range(max(0, current_index-10), current_index):
                if translated_texts[i] is not None:
                    prev_context.append(translated_texts[i])
                else:
                    prev_context.append(subtitles[i].text)
            
            # 获取未翻译的后文
            next_context = subtitles[current_index+1:min(len(subtitles), current_index+11)]
            next_text = "\n".join([s.text for s in next_context])
            
            max_retries = 3
            timeout_seconds = 60  # 1分钟超时
            
            for retry in range(max_retries):
                try:
                    print(f"正在翻译字幕 {subtitle.index}，尝试 {retry+1}/{max_retries}")
                    
                    # 构建翻译提示
                    translation_prompt = f"""
                    你是一个专业的字幕翻译专家。以下是关于这个视频/内容的背景信息：

                    {context_summary}

                    专用词汇列表（请在翻译时特别注意）：
                    {"\n".join(self.custom_vocab) if self.custom_vocab else "无特殊词汇"}

                    翻译要求：
                    1. 仅翻译"待翻译文本"部分
                    2. 保持原文的语气和风格，调整为更符合中文语境和逻辑的表达。整体语言风格应略带轻松但专业，以适应DND视频观众的预期。
                    3. 确保翻译自然流畅，便于视频观众理解，同时保留DND的奇幻氛围。
                    4. 严格只返回翻译结果，不要添加任何其他内容
                    5. 我会为你在待翻译文本前后提供它的上下文，请你不要翻译它们。
                    6. 当前句子翻译需参考上下文，但不得提前翻译后续句子的具体内容。
                    7. 翻译需为后续内容留出逻辑衔接空间，避免突兀地断句。
                    8. 当句子逻辑复杂时，可根据中文习惯断句，并将部分内容转移到下一句。例子：
                    示例：
                    英文原文：
                    第一句：
                    MARISHA: I mean, we could Stone Shape it and I could like Stone Shape it and bury it somewhere in 
                    第二句：
                    our Keep.

                    理想翻译：
                    第一句：
                    玛丽莎：我的意思是，我们可以用「塑石术」把它变成石头，然后——
                    第二句：
                    埋在我们的「灰颅堡」某个地方。

                    9. 保持上下文的连贯性和整体语气一致，句间语义需自然衔接。
                    10. 禁止重复翻译上下文内容，仅使用当前句的信息完成翻译。
                    11. 程序会默认第一行为翻译结果，并自动截取第一行
                    12. 有关法术的专有名词，使用「」标注

                    已翻译上文（前10句）：
                    {"\n".join(prev_context)}

                    待翻译文本：{subtitle.text}

                    未翻译下文（后10句）：
                    {next_text}

                    请只返回待翻译文本的翻译结果。
                    """
                    
                    # 使用带超时的翻译方法 - 这里是关键修改
                    translated_text = self.translate_with_timeout(
                        text=subtitle.text,
                        system_prompt=translation_prompt,
                        temperature=0.7,
                        timeout_seconds=timeout_seconds
                    )
                    
                    # 检查翻译结果
                    if not translated_text or translated_text.strip() == '':
                        raise ValueError("翻译结果为空")
                    
                    # 移除可能的额外描述
                    translated_text = translated_text.strip().split('\n')[0].strip()
                    
                    return translated_text
                
                except Exception as e:
                    # 记录错误
                    if "翻译超时" in str(e):
                        print(f"翻译字幕 {subtitle.index} 超时（第 {retry + 1} 次尝试）: {e}")
                    else:
                        print(f"翻译字幕 {subtitle.index} 失败（第 {retry + 1} 次尝试）: {e}")
                    
                    # 最后一次重试仍失败
                    if retry == max_retries - 1:
                        # 根据错误类型选择不同的处理方式
                        if "翻译超时" in str(e):
                            return f"[超时跳过] {subtitle.text}"
                        elif isinstance(e, ValueError):
                            # 如果是值错误（如空结果），返回原文并附加错误标记
                            return f"[翻译失败] {subtitle.text}"
                        else:
                            # 对于其他类型错误，返回原文并附加详细错误信息
                            return f"[翻译错误：{str(e)}] {subtitle.text}"
                    
                    # 等待后重试
                    if "翻译超时" in str(e):
                        time.sleep(10)  # 超时后等待10秒
                    else:
                        time.sleep(60)  # 其他错误等待60秒
            
            # 理论上不会执行到这里，但保险起见
            return f"[翻译失败] {subtitle.text}"

        # 使用线程池进行并发翻译
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 准备翻译任务
            translation_futures = [
                executor.submit(
                    safe_translate_subtitle, 
                    subtitle, 
                    self.context_summary, 
                    subtitles, 
                    translated_texts
                ) for subtitle in subtitles
            ]
            
            # 收集翻译结果
            for future in concurrent.futures.as_completed(translation_futures):
                try:
                    index = translation_futures.index(future)
                    translated_text = future.result()
                    translated_texts[index] = translated_text
                except Exception as e:
                    print(f"处理字幕翻译任务时发生异常: {e}")
                    # 如果任务本身抛出异常，返回原文
                    translated_texts[index] = "[处理失败]"
            
            return translated_texts

    def process_subtitle_file(self, file_path, target_language) -> Tuple[str, str]:
        """完整的字幕处理流程，增加全面的错误处理"""
        try:
            # 读取字幕文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析字幕
            subtitles = self.parse_subtitles(content)
            
            # 检查是否有可翻译的字幕
            if not subtitles:
                raise ValueError(f"文件 {file_path} 中没有可翻译的字幕")
            
            # 提取纯文本用于分析
            full_text = "\n".join([sub.text for sub in subtitles])
            
            # 设置目标语言
            self.target_language = target_language
            
            # 第一阶段：分析内容
            print("正在分析内容...")
            context_summary = self.analyze_content(full_text)
            
            # 如果内容分析失败，使用默认提示词
            if not context_summary:
                context_summary = f"这是一个需要翻译的字幕文件。请保持原文的语气和风格。"
            
            print(f"内容分析完成: \n{context_summary}\n")
            
            # 将上下文摘要保存为实例变量
            self.context_summary = context_summary
            
            # 第二阶段：翻译字幕
            print("开始并发翻译...")
            translated_texts = self.translate_with_context(subtitles)
            
            # 检查翻译结果
            if len(translated_texts) != len(subtitles):
                print(f"警告：翻译结果数量({len(translated_texts)})与原字幕数量({len(subtitles)})不符")
            
            # 重建字幕文件
            output_content = self.rebuild_subtitles(subtitles, translated_texts)
            
            # 保存翻译结果
            output_path = self._generate_output_path(file_path, target_language)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            
            # 保存分析报告
            analysis_path = self._generate_analysis_path(file_path)
            with open(analysis_path, 'w', encoding='utf-8') as f:
                f.write(f"内容分析报告:\n{context_summary}")
            
            # 检查是否有翻译失败的字幕
            failed_subtitles = [
                text for text in translated_texts 
                if text.startswith("[翻译失败]") or text.startswith("[翻译错误")
            ]
            
            if failed_subtitles:
                print(f"警告：{len(failed_subtitles)} 个字幕翻译失败")
            
            return output_path, analysis_path
        
        except Exception as e:
            print(f"处理字幕文件 {file_path} 时发生错误: {e}")
            raise

    def rebuild_subtitles(self, original_subtitles, translated_texts):
        """重建SRT文件"""
        rebuilt_content = []
        for (subtitle, translated_text) in zip(original_subtitles, translated_texts):
            subtitle_block = f"{subtitle.index}\n{subtitle.timestamp_in} --> {subtitle.timestamp_out}\n{translated_text}\n\n"
            rebuilt_content.append(subtitle_block)
        
        return "".join(rebuilt_content)

    def _generate_output_path(self, input_path, target_language):
        """生成输出文件路径"""
        base, ext = os.path.splitext(input_path)
        return f"{base}_translated_{target_language}{ext}"

    def _generate_analysis_path(self, input_path):
        """生成分析报告文件路径"""
        base, ext = os.path.splitext(input_path)
        return f"{base}_analysis.txt"

    #从这里开始是按说话人分组翻译的相关方法
    
    #第二阶段变体：按照说话人分组翻译字幕
    def translate_subtitles_by_speaker(self, subtitles, context_window=5):
        """第二阶段-2：按说话人分组翻译字幕，自动支持并发"""
        if not self.context_summary:
            print("警告：未进行内容分析，将使用默认翻译")
            self.context_summary = f"这是一个需要翻译的字幕文件。请保持原文的语气和风格。"
        groups = self.group_subtitles_by_speaker(subtitles)
        translated_texts = [None] * len(groups)
        translated_groups = [None] * len(groups)

        def safe_translate_group(i, group):
            prev_context = "\n".join([g for g in translated_groups[max(0, i-context_window):i] if g]) if i > 0 else ""
            next_groups = groups[i+1:i+1+context_window]
            next_context = "\n".join(
                "\n".join([sub.text for sub in g]) for g in next_groups
            ) if next_groups else ""
            group_text = "\n".join([sub.text for sub in group])
            group_text = group_text.replace('\n', ' ').replace('\r', ' ')
            max_retries = 3
            for retry in range(max_retries):
                try:
                    self._update_progress(
                        "group_start", i+1, len(groups),
                        f"开始翻译第{i+1}组（重试{retry+1}/{max_retries}）"
                    )
                    prompt = f"""
                    你是一位专业的中英字幕翻译专家，正在翻译一段具有角色发言结构的视频字幕。以下是关于这个视频/内容的背景信息：
                    {self.context_summary}
                    专有词汇列表（请在翻译时特别注意）：
                    {"\n".join(self.custom_vocab) if self.custom_vocab else "无特殊词汇"}
                    翻译要求：
                    1. 仅翻译【待翻译分组文本】部分
                    2. 保持原文的语气和风格，调整为更符合中文语境和逻辑的表达。
                    3. 确保翻译自然流畅，便于视频观众理解，同时保留DND的奇幻氛围。
                    4. 严格只返回翻译结果，不要添加任何其他内容。
                    5. 上下文信息仅供参考，请勿翻译上下文内容。
                    6. 保持与上文衔接，并为下文留出衔接空间。
                    7. 如果有单独的数字，一般代表着掷骰的点数，不是多少分。
                    8. 请注意相似的人名翻译，例如惠顿 WIL 威尔 WILL，要有区分，名字请一定要翻译

                    
                    已翻译上文（前{context_window}组）：
                    {prev_context}
                    
                    待翻译分组文本：
                    {group_text}
                    
                    未翻译下文（后{context_window}组）：
                    {next_context}
                    
                    请只返回待翻译分组文本的翻译结果。
                    """
                    translated_group = self.translator.translate(
                        text=group_text,
                        system_prompt=prompt,
                        temperature=self.temperature
                    )
                    if not translated_group or translated_group.strip() == '':
                        raise ValueError("翻译结果为空")
                    translated_group = translated_group.strip()
                    lines = [line.strip() for line in translated_group.split('\n') if line.strip()]
                    if len(lines) == len(group):
                        zh_splits = lines
                    else:
                        eng_lens = [len(sub.text) for sub in group]
                        total_eng = sum(eng_lens)
                        zh_total = len(translated_group)
                        target_lengths = [max(1, int(zh_total * l / total_eng)) for l in eng_lens]
                        zh_splits = self.smart_split_translatedSubs(translated_group, target_lengths)
                        if len(zh_splits) != len(group):
                            print(f"警告：第{i}组拆分数量不符，原组{len(group)}条，拆分后{len(zh_splits)}条")
                    translated_groups[i] = "".join(zh_splits)
                    self._update_progress(
                        "group_done", i+1, len(groups),
                        f"第{i+1}组翻译完成"
                    )
                    return zh_splits
                except Exception as e:
                    self._update_progress(
                        "group_error", i+1, len(groups),
                        f"第{i+1}组翻译失败（第{retry+1}次）：{e}"
                    )
                    print(f"翻译分组 {i} 失败（第 {retry + 1} 次尝试）: {e}")
                    if retry == max_retries - 1:
                        if isinstance(e, ValueError):
                            return [f"[翻译失败] {sub.text}" for sub in group]
                        else:
                            return [f"[翻译错误：{str(e)}] {sub.text}" for sub in group]
                    time.sleep(10)
        # 自动并发或顺序
        if self.max_workers > 1:
            print(f"使用并发翻译模式（{self.max_workers}线程）...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(safe_translate_group, i, group) for i, group in enumerate(groups)]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        idx = futures.index(future)
                        result = future.result()
                        translated_texts[idx] = result
                    except Exception as e:
                        print(f"分组 {idx} 并发任务异常: {e}")
                        translated_texts[idx] = [f"[处理失败]"] * len(groups[idx])
            # 展平结果
            final_texts = []
            for group_result in translated_texts:
                if group_result:
                    final_texts.extend(group_result)
            return final_texts
        else:
            print("使用顺序翻译模式...")
            for i, group in enumerate(groups):
                result = safe_translate_group(i, group)
                translated_texts[i] = result
            final_texts = []
            for group_result in translated_texts:
                if group_result:
                    final_texts.extend(group_result)
            return final_texts

    #根据说话人分类字幕
    def group_subtitles_by_speaker(self, subtitles):
        """
        聚合同一说话人的字幕文本。没有说话人名的字幕归入前一个说话人组。
        """
        groups = []
        current = []
        currSpeaker = None
        # 遍历字幕列表
        for sub in subtitles:
            # 提取说话人名
            match = re.match(r'^(.+?):', sub.text)
            speaker = match.group(1) if match else None
            
            # 如果有新的说话人名，开始新组
            if speaker is not None:
                if current:
                    groups.append(current)
                current = [sub]
                currSpeaker = speaker
            else:
                # 如果没有说话人名，或者是同一说话人，继续添加到当前组
                current.append(sub)
        
        # 添加最后一组
        if current:
            groups.append(current)
        
        return groups
        
        
    def smart_split_translatedSubs(self, text, target_lengths):
        """
        智能分割翻译后的字幕文本，确保每个部分的长度接近目标长度。
        """
        if not target_lengths:
            return [text]
        
        if len(target_lengths) == 1:
            return [text]
        
        result = []
        index = 0
        
        for i, length in enumerate(target_lengths[:-1]):
            # 检查是否还有剩余文本
            if index >= len(text):
                result.append("")
                continue
                
            # 在目标长度断句
            cut = min(index + length, len(text))  # ←防止越界
            
            # 如果不是最后几个字符，尝试在标点处断开
            if cut < len(text) - 1:
                while cut < len(text) and text[cut] in "。，.！？的们么了地些；”":
                    cut += 1
        
            # 更新index和result
            result.append(text[index:cut])
            index = cut
            
            # 跳过开头的不合适标点和空白字符
            while index < len(text) and text[index] in "，、 \t\n":
                index += 1
    
        # 处理最后一段
        if index < len(text):
            result.append(text[index:])
        else:
            result.append("")
    
        return result
    
    def process_subtitle_file_grouped(self, file_path, target_language, use_concurrent=False) -> Tuple[str, str]:
       """ 处理字幕文件，按说话人分组翻译，并智能分割翻译后的字幕文本。""" 
       try:
           # 读取字幕文件
            self._update_progress("reading_file", extra_info=f"读取文件: {os.path.basename(file_path)}")
            with open(file_path, 'r', encoding = 'utf-8') as f:
               content = f.read()
               
            # 解析字幕
            self._update_progress("parsing_subtitles", extra_info="解析字幕格式")
            subtitles = self.parse_subtitles(content)
            
            # 检查是否有可翻译的字幕
            if not subtitles:
                raise ValueError(f"文件{file_path}中没有可翻译的字幕")
            
            # 提取纯文本用于分析
            full_text = "\n".join([sub.text for sub in subtitles])
            
            # 设置目标语言
            self.target_language = target_language
            
            # 第一阶段：分析内容
            self._update_progress("content_analysis", extra_info="分析内容和上下文")
            print("正在分析内容...")
            context_summary = self.analyze_content(full_text)
            
            # 如果内容分析失败，使用默认提示词
            if not context_summary:
                context_summary = "这是一个需要翻译的字幕文件。请保持原文的语气和风格。"
            
            print(f"内容分析完成：\n{context_summary}\n")
            
            # 将上下文摘要保存为实例变量
            self.context_summary = context_summary
            
            # 第二阶段：按说话人分组翻译字幕
            self._update_progress("translation_start", 0, len(subtitles), "开始按说话人分组翻译")
            print("开始按照说话人分组进行翻译...")
            
            # 选择翻译方式 - 关键修改
            if use_concurrent:
                print("使用并发翻译模式...")
                translated_texts = self.translate_subtitles_by_speaker_concurrent(subtitles)
            else:
                print("使用顺序翻译模式...")
                translated_texts = self.translate_subtitles_by_speaker(subtitles)
            
            # 检查翻译结果
            if len(translated_texts) != len(subtitles):
                print(f"警告：翻译结果数量({len(translated_texts)})与原字幕数量({len(subtitles)})不符")
                
            # 重建字幕文件
            self._update_progress("rebuilding", extra_info="重建SRT文件")
            output_content = self.rebuild_subtitles(subtitles, translated_texts)
            
            # 保存翻译结果
            output_path = self._generate_output_path(file_path, target_language)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
                
            # 保存分析报告
            analysis_path = self._generate_analysis_path(file_path)
            with open(analysis_path, 'w', encoding='utf-8') as f:
                f.write(f"内容分析报告:\n{context_summary}")
            
            # 检查是否有翻译失败的字幕
            failed_subtitles = [
                text for text in translated_texts
                if text.startswith("[翻译失败]") or text.startswith("[翻译错误")
            ]
            
            if failed_subtitles:
                print(f"警告：{len(failed_subtitles)}个字幕翻译失败")
            
            self._update_progress("completed", len(subtitles), len(subtitles), f"翻译完成: {os.path.basename(output_path)}")
            return output_path, analysis_path
       except Exception as e:
           self._update_progress("error", extra_info=f"处理文件失败: {str(e)}")
           print(f"处理字幕文件 {file_path} 时发生错误: {e}")
           raise