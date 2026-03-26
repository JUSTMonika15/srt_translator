"""
SRT 字幕断句修复工具
专门用于修复中文字幕中被切断的词语，特别是专有名词（人名、地名等）
"""

import jieba
import pysrt
import re
import os
import glob
from typing import List, Tuple, Optional

# 添加自然排序函数
def natural_sort_key(text: str):
    """
    自然排序：让 1-500 排在 501-1001 前面，1002-1503 排在最后
    """
    return [int(c) if c.isdigit() else c.lower() 
            for c in re.split(r'(\d+)', text)]

class SubtitleBreakFixer:
    def __init__(self, custom_vocab: Optional[List[str]] = None, vocab_file: Optional[str] = None):
        """
        初始化断句修复器
        
        Args:
            custom_vocab: 自定义词汇列表
            vocab_file: 术语列表文件路径（如果为None，自动查找"术语列表.txt"）
        """
        self.custom_vocab = custom_vocab or []
        
        # 加载术语词典
        if not self.custom_vocab:
            if vocab_file is None:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                vocab_file = os.path.join(script_dir, "术语列表.txt")
            
            if os.path.exists(vocab_file):
                self.custom_vocab = self.load_vocab_from_file(vocab_file)
                print(f"✓ 从 {os.path.basename(vocab_file)} 加载了 {len(self.custom_vocab)} 个术语")
            else:
                print(f"⚠ 未找到术语文件: {vocab_file}")
                print("  提示：可以创建 术语列表.txt 文件来添加自定义词汇")
        
        # 把自定义词汇加入 jieba 词典（设置超高频，确保不被切开）
        for word in self.custom_vocab:
            jieba.add_word(word, freq=999999)
    
    def load_vocab_from_file(self, file_path: str) -> List[str]:
        """
        从术语列表文件加载词汇
        支持格式：中文 English 或单独的词
        """
        vocab = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                
                # 提取所有词汇（中英文都要）
                for word in line.split():
                    if word and len(word) > 1:
                        vocab.append(word)
        
        # 去重并按长度排序（长词优先匹配）
        vocab = list(set(vocab))
        vocab.sort(key=len, reverse=True)
        return vocab
    
    def find_broken_word(self, text1: str, text2: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        检查断点是否切断了词语（增强版）
        
        检测方法：
        1. 专有名词匹配（最优先）
        2. jieba 分词检测
        
        Returns:
            (是否有问题, 被切断的完整词, text1中属于该词的部分)
        """
        # 方法1：专有名词匹配（针对自定义词汇表）
        # 检查 text1 的结尾 + text2 的开头是否匹配某个专有名词
        for vocab_word in self.custom_vocab:
            if len(vocab_word) < 2:
                continue
            
            # 尝试不同的切分位置
            for i in range(1, len(vocab_word)):
                part1 = vocab_word[:i]
                part2 = vocab_word[i:]
                
                # 检查是否匹配
                if text1.endswith(part1) and text2.startswith(part2):
                    # 确保不是更长词的一部分
                    prefix_ok = (len(text1) < len(part1) or 
                               text1[-(len(part1)+1)] in '，。！？；：""''、\n ')
                    suffix_ok = (len(text2) == len(part2) or 
                               text2[len(part2)] in '，。！？；：""''、\n ')
                    
                    if prefix_ok or suffix_ok:
                        return True, vocab_word, part1
        
        # 方法2：jieba 分词检测（扩大窗口）
        window_size = 30
        boundary = text1[-window_size:] + text2[:window_size]
        split_pos = len(text1[-window_size:])
        
        # 分词
        tokens = list(jieba.cut(boundary))
        
        # 找到跨越断点的词
        char_pos = 0
        for token in tokens:
            token_start = char_pos
            token_end = char_pos + len(token)
            
            # 如果断点在词中间（词长度至少2，且不是纯标点）
            if (token_start < split_pos < token_end and 
                len(token) >= 2 and 
                not all(c in '，。！？；：""''、·…—（）[]{}' for c in token)):
                
                part_in_text1 = token[:(split_pos - token_start)]
                part_in_text2 = token[(split_pos - token_start):]
                
                # 验证这确实是被切断的词
                if text1.endswith(part_in_text1) and text2.startswith(part_in_text2):
                    return True, token, part_in_text1
            
            char_pos += len(token)
        
        return False, None, None
    
    def fix_subtitle_file(self, input_srt: str, output_srt: Optional[str] = None) -> str:
        """
        修复整个字幕文件的断句
        
        Args:
            input_srt: 输入文件路径
            output_srt: 输出文件路径（默认为 _fixed.srt）
        
        Returns:
            输出文件路径
        """
        if output_srt is None:
            output_srt = input_srt.replace('.srt', '_fixed.srt')
        
        # 加载字幕
        subs = pysrt.open(input_srt, encoding='utf-8')
        fixes = []
        
        print(f"\n{'='*60}")
        print(f"开始优化字幕断句")
        print(f"{'='*60}")
        print(f"输入: {os.path.basename(input_srt)}")
        print(f"字幕数: {len(subs)} 条")
        print(f"词汇表: {len(self.custom_vocab)} 个术语")
        print(f"检测中...")
        
        # 滑动窗口遍历，显示进度
        total = len(subs) - 1
        for i in range(total):
            # 显示进度（每100条）
            if i % 100 == 0 and i > 0:
                print(f"  进度: {i}/{total} ({i*100//total}%)")
            
            current = subs[i]
            next_sub = subs[i + 1]
            
            # 跳过空字幕
            if not current.text.strip() or not next_sub.text.strip():
                continue
            
            # 只检查中文部分（跳过英文原文）
            current_lines = current.text.split('\n')
            next_lines = next_sub.text.split('\n')
            
            # 取第一行（通常是中文）
            current_text = current_lines[0] if current_lines else current.text
            next_text = next_lines[0] if next_lines else next_sub.text
            
            # 检查断句
            is_bad, broken_word, part_in_current = self.find_broken_word(
                current_text, 
                next_text
            )
            
            if is_bad and broken_word:
                # 修复：把整个词推给第二句
                new_current = current_text[:-len(part_in_current)].rstrip()
                new_next = broken_word + next_text[len(broken_word) - len(part_in_current):]
                
                # 保存修复信息
                fixes.append({
                    'index': i + 1,
                    'word': broken_word,
                    'before': f"{current_text[-30:]} | {next_text[:30]}",
                    'after': f"{new_current[-30:]} | {new_next[:30]}"
                })
                
                # 更新字幕文本（只修改第一行，保留英文）
                if len(current_lines) > 1:
                    current.text = new_current + '\n' + '\n'.join(current_lines[1:])
                else:
                    current.text = new_current
                
                if len(next_lines) > 1:
                    next_sub.text = new_next + '\n' + '\n'.join(next_lines[1:])
                else:
                    next_sub.text = new_next
        
        # 保存文件
        subs.save(output_srt, encoding='utf-8')
        
        # 输出报告
        print(f"\n{'='*60}")
        print(f"✓ 完成！共修复 {len(fixes)} 处断句问题")
        print(f"{'='*60}\n")
        
        if fixes:
            print(f"修复详情（显示前 15 个）：\n")
            for idx, fix in enumerate(fixes[:15], 1):
                print(f"{idx}. #{fix['index']}: '{fix['word']}'")
                print(f"   前: ...{fix['before']}...")
                print(f"   后: ...{fix['after']}...")
                print()
            
            if len(fixes) > 15:
                print(f"... 还有 {len(fixes) - 15} 处修复未显示")
        else:
            print("✓ 未发现需要修复的断句（翻译质量很好！）")
        
        print(f"\n输出: {os.path.basename(output_srt)}")
        return output_srt

def select_directory() -> str:
    """选择要处理的文件夹"""
    print("\n" + "="*60)
    print("SRT 字幕断句修复工具")
    print("="*60 + "\n")
    
    current_dir = os.getcwd()
    print(f"当前目录: {current_dir}\n")
    
    # 扫描包含 SRT 文件的文件夹
    folders = []
    for root, dirs, files in os.walk(current_dir):
        srt_count = len([f for f in files 
                        if f.endswith('.srt') and not f.endswith('_fixed.srt')])
        if srt_count > 0:
            rel_path = os.path.relpath(root, current_dir)
            if rel_path == '.':
                rel_path = '当前目录'
            folders.append((root, rel_path, srt_count))
    
    # 自然排序
    folders.sort(key=lambda x: natural_sort_key(x[1]))
    
    if not folders:
        print("⚠ 未找到包含 SRT 文件的文件夹")
        folder_path = input("\n请输入文件夹路径: ").strip().strip('"')
        return folder_path
    
    print(f"找到 {len(folders)} 个文件夹：\n")
    for i, (path, rel_path, count) in enumerate(folders, 1):
        print(f"  [{i}] {rel_path} ({count} 个文件)")
    
    print(f"\n  [0] 手动输入路径")
    print(f"  [Q] 退出\n")
    
    while True:
        choice = input("选择文件夹编号: ").strip().upper()
        
        if choice == 'Q':
            exit(0)
        if choice == '0':
            return input("\n请输入文件夹路径: ").strip().strip('"')
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(folders):
                return folders[index][0]
            print(f"⚠ 请输入 1-{len(folders)} 之间的数字")
        except ValueError:
            print("⚠ 请输入有效的数字")

def list_srt_files(directory: str) -> List[str]:
    """列出目录下的所有 SRT 文件（自然排序）"""
    srt_files = [f for f in glob.glob(os.path.join(directory, "*.srt"))
                 if not f.endswith("_fixed.srt")]
    srt_files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
    return srt_files

def select_srt_file(directory: str):
    """交互式选择 SRT 文件"""
    print(f"\n{'='*60}")
    print(f"文件夹: {directory}")
    print(f"{'='*60}\n")
    
    srt_files = list_srt_files(directory)
    
    if not srt_files:
        print("⚠ 该文件夹下没有 .srt 文件")
        return None
    
    print(f"找到 {len(srt_files)} 个 SRT 文件：\n")
    
    for i, file in enumerate(srt_files, 1):
        file_name = os.path.basename(file)
        file_size = os.path.getsize(file) / 1024
        print(f"  [{i}] {file_name} ({file_size:.1f} KB)")
    
    print(f"\n  [A] 全部处理")
    print(f"  [B] 返回上级")
    print(f"  [Q] 退出\n")
    
    while True:
        choice = input("选择文件编号: ").strip().upper()
        
        if choice == 'Q':
            exit(0)
        if choice == 'B':
            return 'BACK'
        if choice == 'A':
            return srt_files
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(srt_files):
                return [srt_files[index]]
            print(f"⚠ 请输入 1-{len(srt_files)} 之间的数字")
        except ValueError:
            print("⚠ 请输入有效的数字、A、B 或 Q")

def main():
    """主程序"""
    import sys
    
    # 命令行模式
    if len(sys.argv) > 1:
        input_files = [sys.argv[1]]
    else:
        # 交互式模式
        while True:
            directory = select_directory()
            
            if not os.path.exists(directory):
                print(f"⚠ 文件夹不存在: {directory}")
                continue
            
            result = select_srt_file(directory)
            
            if result == 'BACK':
                continue
            elif result is None:
                continue
            else:
                input_files = result
                break
    
    # 创建修复器
    print("\n初始化分词引擎...")
    fixer = SubtitleBreakFixer()
    
    # 批量处理
    success_count = 0
    for idx, input_file in enumerate(input_files, 1):
        if not os.path.exists(input_file):
            print(f"⚠ 文件不存在: {input_file}")
            continue
        
        if len(input_files) > 1:
            print(f"\n{'='*60}")
            print(f"处理文件 {idx}/{len(input_files)}")
            print(f"{'='*60}")
        
        input_dir = os.path.dirname(input_file)
        input_name = os.path.basename(input_file)
        output_file = os.path.join(input_dir, "[修复分句]" + input_name)
        
        try:
            fixer.fix_subtitle_file(input_file, output_file)
            success_count += 1
        except Exception as e:
            print(f"⚠ 处理出错: {e}")
            import traceback
            traceback.print_exc()
    
    # 总结
    print(f"\n{'='*60}")
    print(f"所有文件处理完成！({success_count}/{len(input_files)} 成功)")
    print(f"{'='*60}")
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()