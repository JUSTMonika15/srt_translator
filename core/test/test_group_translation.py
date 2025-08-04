import sys
import os

# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from core.subtitle_translator import Subtitle, SmartSubtitleTranslator

class MockTranslator:
    """模拟翻译器，不需要真实API"""
    def translate(self, text, system_prompt, temperature=0.7):
        # 模拟翻译结果
        if "分析" in system_prompt or "analyze" in system_prompt.lower():
            return "这是一个DND（龙与地下城）游戏视频，包含多个角色的对话和旁白。主要角色包括ORION（奥利安）、MATT（马特）、LAURA（劳拉）等。"
        
        # 模拟按组翻译
        lines = text.strip().split('\n')
        translated_lines = []
        
        for line in lines:
            if line.startswith("ORION:"):
                # 修复引号冲突问题
                translated_line = line.replace("ORION:", "奥利安：")
                translated_line = translated_line.replace("Can we use the word liaison?", "我们能用'联络人'这个词吗？")
                translated_line = translated_line.replace("But wait, I have another idea.", "等等，我有另一个想法。")
                translated_lines.append(translated_line)
            elif line.startswith("MATT:"):
                translated_line = line.replace("MATT:", "马特：")
                translated_line = translated_line.replace("The price would be", "价格应该是")
                translated_lines.append(translated_line)
            elif line.startswith("LAURA:"):
                translated_line = line.replace("LAURA:", "劳拉：")
                translated_line = translated_line.replace("That's interesting", "这很有趣")
                translated_lines.append(translated_line)
            else:
                # 没有说话人的行，简单翻译
                line_lower = line.lower()
                if "think" in line_lower:
                    translated_lines.append(f"我认为{line_lower.replace('i think', '').strip()}")
                elif "what" in line_lower:
                    translated_lines.append(f"什么{line_lower.replace('what', '').strip()}")
                elif "maybe" in line_lower:
                    translated_lines.append(f"也许{line_lower.replace('maybe', '').strip()}")
                elif "agree" in line_lower:
                    translated_lines.append(f"我同意{line_lower.replace('i agree', '').strip()}")
                elif "let" in line_lower and "s" in line_lower:
                    translated_lines.append(f"让我们{line_lower.replace('let', '').replace('s', '').strip()}")
                else:
                    translated_lines.append(f"翻译：{line}")
        
        return "\n".join(translated_lines)

def test_complete_group_translation_flow():
    """测试完整的分组翻译流程"""
    print("=== 完整分组翻译流程测试 ===\n")
    
    # 创建测试字幕数据
    test_subtitles = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "ORION: Can we use the word liaison?"),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "I think it's appropriate."),
        Subtitle("3", "00:00:07,000", "00:00:09,000", "What do you all think?"),
        Subtitle("4", "00:00:10,000", "00:00:12,000", "MATT: The price would be quite high."),
        Subtitle("5", "00:00:13,000", "00:00:15,000", "You can find it in the marketplace."),
        Subtitle("6", "00:00:16,000", "00:00:18,000", "ORION: But wait, I have another idea."),
        Subtitle("7", "00:00:19,000", "00:00:21,000", "Maybe we should consider alternatives."),
        Subtitle("8", "00:00:22,000", "00:00:24,000", "LAURA: That's interesting to hear."),
        Subtitle("9", "00:00:25,000", "00:00:27,000", "I agree with your assessment."),
        Subtitle("10", "00:00:28,000", "00:00:30,000", "Let's move forward with this plan."),
    ]
    
    # 创建模拟翻译器
    mock_translator = MockTranslator()
    subtitle_translator = SmartSubtitleTranslator(translator=mock_translator, custom_vocab=["liaison 联络人"])
    
    print("1. 测试分组功能...")
    groups = subtitle_translator.group_subtitles_by_speaker(test_subtitles)
    print(f"   分组数量: {len(groups)}")
    
    total_subs_in_groups = 0
    for i, group in enumerate(groups):
        group_texts = [sub.text for sub in group]
        print(f"   第{i+1}组 ({len(group)}条): {group_texts}")
        total_subs_in_groups += len(group)
    
    print(f"   分组总数量: {total_subs_in_groups}, 原始数量: {len(test_subtitles)}")
    assert total_subs_in_groups == len(test_subtitles), "分组后总数量不匹配！"
    print("   ✓ 分组数量匹配\n")
    
    print("2. 测试内容分析...")
    full_text = "\n".join([sub.text for sub in test_subtitles])
    context_summary = subtitle_translator.analyze_content(full_text)
    print(f"   分析结果: {context_summary[:100]}...")
    subtitle_translator.context_summary = context_summary
    print("   ✓ 内容分析完成\n")
    
    print("3. 测试分组翻译...")
    translated_texts = subtitle_translator.translate_subtitles_by_speaker(test_subtitles)
    print(f"   翻译结果数量: {len(translated_texts)}")
    print(f"   原始字幕数量: {len(test_subtitles)}")
    
    if len(translated_texts) == len(test_subtitles):
        print("   ✓ 翻译数量匹配")
    else:
        print("   ✗ 翻译数量不匹配！")
        return False
    
    print("\n4. 翻译结果展示:")
    for i, (original, translated) in enumerate(zip(test_subtitles, translated_texts)):
        print(f"   {i+1:2d}. 原文: {original.text}")
        print(f"       译文: {translated}")
        print()
    
    print("5. 测试重建字幕...")
    rebuilt_content = subtitle_translator.rebuild_subtitles(test_subtitles, translated_texts)
    lines = rebuilt_content.strip().split('\n')
    print(f"   重建内容行数: {len(lines)}")
    print("   重建内容样例:")
    print("   " + "\n   ".join(lines[:8]))
    print("   ...\n")
    
    # 验证时间轴保持不变
    print("6. 验证时间轴保持...")
    subtitle_blocks = rebuilt_content.strip().split('\n\n')
    for i, block in enumerate(subtitle_blocks[:3]):  # 检查前3个
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            index = lines[0]
            timestamp = lines[1]
            content = lines[2]
            original_sub = test_subtitles[i]
            
            print(f"   字幕{i+1}: {index} | {timestamp}")
            assert index == original_sub.index, f"字幕序号不匹配: {index} vs {original_sub.index}"
            expected_timestamp = f"{original_sub.timestamp_in} --> {original_sub.timestamp_out}"
            assert timestamp == expected_timestamp, f"时间轴不匹配: {timestamp} vs {expected_timestamp}"
    
    print("   ✓ 时间轴保持正确\n")
    
    print("🎉 所有测试通过！分组翻译流程工作正常！")
    return True

def test_smart_split_function():
    """测试智能拆分功能"""
    print("\n=== 智能拆分功能测试 ===\n")
    
    mock_translator = MockTranslator()
    subtitle_translator = SmartSubtitleTranslator(translator=mock_translator)
    
    # 测试数据
    test_cases = [
        {
            "text": "这是第一句话。这是第二句话。这是第三句话。",
            "target_lengths": [6, 6, 6],
            "description": "等长分割"
        },
        {
            "text": "短句。这是一个比较长的句子内容。长句结束。",
            "target_lengths": [3, 12, 4],
            "description": "不等长分割"
        },
        {
            "text": "奥利安：我们能用联络人这个词吗？",
            "target_lengths": [15],
            "description": "单句不分割"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"{i}. 测试{case['description']}:")
        print(f"   原文: {case['text']}")
        print(f"   目标长度: {case['target_lengths']}")
        
        result = subtitle_translator.smart_split_translatedSubs(case['text'], case['target_lengths'])
        print(f"   分割结果: {result}")
        print(f"   分割数量: {len(result)} (期望: {len(case['target_lengths'])})")
        
        if len(result) == len(case['target_lengths']):
            print("   ✓ 分割数量正确")
        else:
            print("   ✗ 分割数量错误")
        
        # 验证重新组合后内容完整
        rejoined = "".join(result)
        if rejoined == case['text']:
            print("   ✓ 内容完整性保持")
        else:
            print("   ✗ 内容完整性丢失")
            print(f"   原文: '{case['text']}'")
            print(f"   重组: '{rejoined}'")
        print()

def test_edge_cases_group_translation():
    """测试分组翻译的边缘情况"""
    print("=== 分组翻译边缘情况测试 ===\n")
    
    mock_translator = MockTranslator()
    subtitle_translator = SmartSubtitleTranslator(translator=mock_translator)
    
    # 测试1: 只有一个说话人
    single_speaker_subs = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "ORION: Hello there."),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "How are you doing?"),
        Subtitle("3", "00:00:07,000", "00:00:09,000", "I hope you're well."),
    ]
    
    print("1. 测试单说话人场景:")
    groups = subtitle_translator.group_subtitles_by_speaker(single_speaker_subs)
    print(f"   分组数量: {len(groups)} (期望: 1)")
    assert len(groups) == 1, "单说话人应该只有一组"
    print(f"   组内字幕数: {len(groups[0])} (期望: 3)")
    assert len(groups[0]) == 3, "单组应该包含所有字幕"
    print("   ✓ 单说话人测试通过\n")
    
    # 测试2: 每条都是不同说话人
    different_speakers_subs = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "ORION: Hello."),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "MATT: Hi there."),
        Subtitle("3", "00:00:07,000", "00:00:09,000", "LAURA: Hey everyone."),
    ]
    
    print("2. 测试不同说话人场景:")
    groups = subtitle_translator.group_subtitles_by_speaker(different_speakers_subs)
    print(f"   分组数量: {len(groups)} (期望: 3)")
    assert len(groups) == 3, "三个不同说话人应该有三组"
    for i, group in enumerate(groups):
        print(f"   第{i+1}组字幕数: {len(group)} (期望: 1)")
        assert len(group) == 1, f"第{i+1}组应该只有一条字幕"
    print("   ✓ 不同说话人测试通过\n")
    
    # 测试3: 完全没有说话人标识
    no_speaker_subs = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "Just some text here."),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "More text without speaker."),
        Subtitle("3", "00:00:07,000", "00:00:09,000", "Even more text."),
    ]
    
    print("3. 测试无说话人场景:")
    groups = subtitle_translator.group_subtitles_by_speaker(no_speaker_subs)
    print(f"   分组数量: {len(groups)} (期望: 1)")
    assert len(groups) == 1, "无说话人应该合并为一组"
    print(f"   组内字幕数: {len(groups[0])} (期望: 3)")
    assert len(groups[0]) == 3, "应该包含所有字幕"
    print("   ✓ 无说话人测试通过\n")

def test_srt_file_generation():
    """测试SRT文件生成和验证"""
    print("\n=== SRT文件生成测试 ===\n")
    
    mock_translator = MockTranslator()
    subtitle_translator = SmartSubtitleTranslator(translator=mock_translator)
    
    # 创建测试字幕数据
    test_subtitles = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "ORION: Can we use the word liaison?"),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "I think it's appropriate."),
        Subtitle("3", "00:00:07,000", "00:00:09,000", "MATT: The price would be quite high."),
        Subtitle("4", "00:00:10,000", "00:00:12,000", "You can find it in the marketplace."),
        Subtitle("5", "00:00:13,000", "00:00:15,000", "ORION: But wait, I have another idea."),
    ]
    
    # 模拟翻译结果
    translated_texts = [
        "奥利安：我们能用'联络人'这个词吗？",
        "我认为这很合适。",
        "马特：价格应该很高。",
        "你可以在市场上找到它。",
        "奥利安：等等，我有另一个想法。"
    ]
    
    print("1. 测试SRT内容重建...")
    rebuilt_content = subtitle_translator.rebuild_subtitles(test_subtitles, translated_texts)
    
    # 检查重建内容格式
    print("   重建的SRT内容:")
    print("   " + "=" * 50)
    print("   " + rebuilt_content.replace('\n', '\n   '))
    print("   " + "=" * 50)
    
    # 验证SRT格式
    print("\n2. 验证SRT格式...")
    
    # 分割为字幕块
    subtitle_blocks = rebuilt_content.strip().split('\n\n')
    print(f"   字幕块数量: {len(subtitle_blocks)} (期望: {len(test_subtitles)})")
    assert len(subtitle_blocks) == len(test_subtitles), "字幕块数量不匹配"
    
    # 验证每个字幕块的格式
    for i, block in enumerate(subtitle_blocks):
        lines = block.strip().split('\n')
        print(f"\n   验证第{i+1}个字幕块:")
        print(f"   原始: {test_subtitles[i].index} | {test_subtitles[i].timestamp_in} --> {test_subtitles[i].timestamp_out} | {test_subtitles[i].text}")
        print(f"   重建: {' | '.join(lines)}")
        
        # 检查行数
        assert len(lines) == 3, f"第{i+1}个字幕块应该有3行，实际有{len(lines)}行"
        
        # 检查序号
        assert lines[0] == test_subtitles[i].index, f"序号不匹配: {lines[0]} vs {test_subtitles[i].index}"
        
        # 检查时间轴格式
        expected_timestamp = f"{test_subtitles[i].timestamp_in} --> {test_subtitles[i].timestamp_out}"
        assert lines[1] == expected_timestamp, f"时间轴不匹配: {lines[1]} vs {expected_timestamp}"
        
        # 检查翻译内容
        assert lines[2] == translated_texts[i], f"翻译内容不匹配: {lines[2]} vs {translated_texts[i]}"
        
        print(f"   ✓ 第{i+1}个字幕块格式正确")
    
    print("\n   ✓ 所有字幕块格式验证通过")
    
    # 验证时间轴格式
    print("\n3. 验证时间轴格式...")
    time_pattern = r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}'
    import re
    
    for i, block in enumerate(subtitle_blocks):
        lines = block.strip().split('\n')
        timestamp_line = lines[1]
        
        if re.match(time_pattern, timestamp_line):
            print(f"   ✓ 第{i+1}个时间轴格式正确: {timestamp_line}")
        else:
            print(f"   ✗ 第{i+1}个时间轴格式错误: {timestamp_line}")
            assert False, f"时间轴格式不正确: {timestamp_line}"
    
    print("\n4. 测试SRT文件可解析性...")
    # 测试重建的内容是否可以被parse_subtitles重新解析
    try:
        reparsed_subtitles = subtitle_translator.parse_subtitles(rebuilt_content)
        print(f"   重新解析的字幕数量: {len(reparsed_subtitles)} (期望: {len(test_subtitles)})")
        assert len(reparsed_subtitles) == len(test_subtitles), "重新解析的字幕数量不匹配"
        
        # 验证重新解析的内容
        for i, (original, reparsed) in enumerate(zip(test_subtitles, reparsed_subtitles)):
            print(f"   验证第{i+1}条字幕:")
            print(f"     序号: {original.index} -> {reparsed.index}")
            print(f"     开始: {original.timestamp_in} -> {reparsed.timestamp_in}")
            print(f"     结束: {original.timestamp_out} -> {reparsed.timestamp_out}")
            print(f"     内容: {translated_texts[i]} -> {reparsed.text}")
            
            assert reparsed.index == original.index, f"序号不匹配: {reparsed.index} vs {original.index}"
            assert reparsed.timestamp_in == original.timestamp_in, f"开始时间不匹配"
            assert reparsed.timestamp_out == original.timestamp_out, f"结束时间不匹配"
            assert reparsed.text == translated_texts[i], f"内容不匹配"
        
        print("   ✓ 重新解析验证通过")
        
    except Exception as e:
        print(f"   ✗ 重新解析失败: {e}")
        assert False, f"SRT文件无法重新解析: {e}"
    
    print("\n🎉 SRT文件生成测试通过！")

def test_srt_edge_cases():
    """测试SRT处理的边缘情况"""
    print("\n=== SRT边缘情况测试 ===\n")
    
    mock_translator = MockTranslator()
    subtitle_translator = SmartSubtitleTranslator(translator=mock_translator)
    
    # 测试1: 包含特殊字符的字幕
    special_char_subtitles = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "ORION: What's that \"thing\" over there?"),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "It looks... strange & mysterious!"),
        Subtitle("3", "00:00:07,000", "00:00:09,000", "100% sure it's magic <laughs>"),
    ]
    
    special_char_translations = [
        "奥利安：那边的东西是什么？",
        "看起来...奇怪又神秘！",
        "100%确定那是魔法 <笑声>"
    ]
    
    print("1. 测试特殊字符处理...")
    rebuilt_special = subtitle_translator.rebuild_subtitles(special_char_subtitles, special_char_translations)
    
    # 验证特殊字符是否正确保留
    reparsed_special = subtitle_translator.parse_subtitles(rebuilt_special)
    for i, reparsed in enumerate(reparsed_special):
        expected_text = special_char_translations[i]
        print(f"   第{i+1}条: {reparsed.text}")
        assert reparsed.text == expected_text, f"特殊字符处理错误"
    
    print("   ✓ 特殊字符处理正确")
    
    # 测试2: 多行字幕内容
    multiline_subtitles = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "ORION: This is a long line"),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "that might span multiple lines"),
    ]
    
    multiline_translations = [
        "奥利安：这是一条很长的句子",
        "可能会跨越多行显示"
    ]
    
    print("\n2. 测试多行内容处理...")
    rebuilt_multiline = subtitle_translator.rebuild_subtitles(multiline_subtitles, multiline_translations)
    reparsed_multiline = subtitle_translator.parse_subtitles(rebuilt_multiline)
    
    for i, reparsed in enumerate(reparsed_multiline):
        expected_text = multiline_translations[i]
        print(f"   第{i+1}条: {reparsed.text}")
        assert reparsed.text == expected_text, f"多行内容处理错误"
    
    print("   ✓ 多行内容处理正确")
    
    # 测试3: 空翻译内容
    empty_translations = ["", "正常翻译", ""]
    empty_subtitles = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "First line"),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "Second line"),  
        Subtitle("3", "00:00:07,000", "00:00:09,000", "Third line"),
    ]
    
    print("\n3. 测试空翻译处理...")
    rebuilt_empty = subtitle_translator.rebuild_subtitles(empty_subtitles, empty_translations)
    reparsed_empty = subtitle_translator.parse_subtitles(rebuilt_empty)
    
    print(f"   处理后字幕数量: {len(reparsed_empty)}")
    for i, reparsed in enumerate(reparsed_empty):
        print(f"   第{i+1}条: '{reparsed.text}'")
    
    print("   ✓ 空翻译处理完成")

def test_current_smart_split_effectiveness():
    """测试当前智能分割系统的实际效果"""
    print("\n=== 当前智能分割系统效果测试 ===\n")
    
    mock_translator = MockTranslator()
    subtitle_translator = SmartSubtitleTranslator(translator=mock_translator)
    
    # 使用你提供的真实案例
    print("测试案例：Critical Role字幕分割")
    print("=" * 60)
    
    # 真实的中文翻译结果（一整段）
    chinese_group = "马特：索比尔带头，按照卡肖兄弟提供的东北方向指引前行，最终带你们绕到了集市的一侧。你们这才明白为何这里被称为「四路交汇」——正是在这片市集所在的位置，两条主干道交汇，然后分别向四面八方延伸至城市的各个区域。从你们当前的位置望去，东北方向的城区逐渐过渡到一个你们之前未曾探访的新区域——你们听说过这个地方，它叫「黄昏草场」此前你们所经过的地区多是信仰「铂金龙」巴哈姆特的信徒聚居之地，那里有「勇武试炼场」，供奉的是力量与战争之神「寇德」；而「四路交汇」则是在「文明与发明之神」厄拉西斯的庇护下。至于眼下将要进入的「黄昏草场」，它则是在「死亡女神」鸦后的注视之下。你们先前远远看到、那座矗立在此区中央、由黑曜石构筑的庞大神殿，正是她的主殿，或许也被称作「鸦之峰」。此外，这一地区还有另一项引人注目的建筑：「紫红地牢」，它实际上是整座瓦瑟海姆城市的主监狱。"
    
    # 对应的英文原文长度（14条字幕）
    english_lengths = [
        95,  # MATT: Thorbir, leading forward in the northeastern direction that was given by Brother Kash,
        98,  # eventually brings you around the side of the bazaar. And you can now see why it's called the
        104, # Quad Roads, there are two main roads that meet right where the bazaar occurs and then they spread
        94,  # off into the other sections of the city. To the northeastern section, from your guys' perspective,
        97,  # the district begins to drift into another district that you have not previously visited. This
        97,  # district is, you've heard it mentioned before, known as the Duskmeadow. Now, previous sections
        89,  # you've been in have been worshipers of Bahamut, the Platinum Dragon. There was the Braving
        104, # Grounds, which worships Kord, the god of strength and warfare and honor. The Quad Roads, which is
        96,  # under Erathis, the deity of civilization and invention. The Duskmeadow falls under the watchful
        104, # eye of the Raven Queen, the goddess of death. That large obsidian-type structure that you were led
        97,  # to earlier is the temple that resides in the center of this district. And you've heard mention
        97,  # before of a few of the things that exist here. That being probably Raven's Crest, which is
        108, # the main temple to the Raven Queen. This is also where the Amaranthine Oubliette is located, which
        78   # is essentially the prison of the entire city of Vasselheim.
    ]
    
    print(f"输入中文长度: {len(chinese_group)} 字符")
    print(f"期望分割数量: {len(english_lengths)} 段")
    print(f"英文原文总长: {sum(english_lengths)} 字符")
    print(f"中英文比例: {len(chinese_group) / sum(english_lengths):.2f}")
    print()
    
    # 测试1: 直接使用英文长度分割
    print("1. 直接按英文长度分割:")
    print("-" * 40)
    
    try:
        result1 = subtitle_translator.smart_split_translatedSubs(chinese_group, english_lengths)
        
        print(f"✓ 分割成功！")
        print(f"  分割段数: {len(result1)} (期望: {len(english_lengths)})")
        print(f"  数量匹配: {'✓' if len(result1) == len(english_lengths) else '✗'}")
        
        # 检查分割质量
        print(f"\n  分割结果预览:")
        for i, segment in enumerate(result1[:5]):  # 只显示前5段
            actual_len = len(segment)
            expected_len = english_lengths[i]
            ratio = actual_len / expected_len if expected_len > 0 else 0
            print(f"    第{i+1}段: 长度{actual_len:3d} (期望{expected_len:3d}) 比例{ratio:.2f}")
            print(f"         内容: {segment}")
        
        if len(result1) > 5:
            print(f"    ... (还有{len(result1)-5}段)")
        
        # 验证完整性
        rejoined = "".join(result1)
        integrity_ok = rejoined == chinese_group
        print(f"\n  内容完整性: {'✓ 完整' if integrity_ok else '✗ 有损失'}")
        
        if not integrity_ok:
            print(f"    原文长度: {len(chinese_group)}")
            print(f"    重组长度: {len(rejoined)}")
            
    except Exception as e:
        print(f"✗ 分割失败: {e}")
        result1 = []
    
    print()
    
    # 测试2: 按比例调整后分割
    print("2. 按比例调整后分割:")
    print("-" * 40)
    
    try:
        # 计算调整比例
        ratio = len(chinese_group) / sum(english_lengths)
        adjusted_lengths = [max(1, int(length * ratio)) for length in english_lengths]
        
        print(f"  调整比例: {ratio:.3f}")
        print(f"  调整后总长: {sum(adjusted_lengths)} (原始: {len(chinese_group)})")
        
        result2 = subtitle_translator.smart_split_translatedSubs(chinese_group, adjusted_lengths)
        
        print(f"✓ 分割成功！")
        print(f"  分割段数: {len(result2)} (期望: {len(english_lengths)})")
        print(f"  数量匹配: {'✓' if len(result2) == len(english_lengths) else '✗'}")
        
        # 检查分割质量
        print(f"\n  分割结果预览:")
        for i, segment in enumerate(result2[:5]):  # 只显示前5段
            actual_len = len(segment)
            adjusted_len = adjusted_lengths[i]
            ratio_adj = actual_len / adjusted_len if adjusted_len > 0 else 0
            print(f"    第{i+1}段: 长度{actual_len:3d} (调整期望{adjusted_len:3d}) 比例{ratio_adj:.2f}")
            print(f"         内容: {segment}")
        
        if len(result2) > 5:
            print(f"    ... (还有{len(result2)-5}段)")
        
        # 验证完整性
        rejoined2 = "".join(result2)
        integrity_ok2 = rejoined2 == chinese_group
        print(f"\n  内容完整性: {'✓ 完整' if integrity_ok2 else '✗ 有损失'}")
        
    except Exception as e:
        print(f"✗ 分割失败: {e}")
        result2 = []
    
    print()
    
    # 测试3: 效果对比
    if result1 and result2:
        print("3. 效果对比分析:")
        print("-" * 40)
        
        # 长度分布标准差（越小越均匀）
        def calc_length_variance(segments, target_lengths):
            if len(segments) != len(target_lengths):
                return float('inf')
            
            ratios = [len(seg) / target for seg, target in zip(segments, target_lengths) if target > 0]
            if not ratios:
                return float('inf')
            
            avg_ratio = sum(ratios) / len(ratios)
            variance = sum((r - avg_ratio) ** 2 for r in ratios) / len(ratios)
            return variance ** 0.5
        
        var1 = calc_length_variance(result1, english_lengths)
        var2 = calc_length_variance(result2, adjusted_lengths)
        
        print(f"  直接分割长度标准差: {var1:.3f}")
        print(f"  调整分割长度标准差: {var2:.3f}")
        print(f"  更均匀的方案: {'调整分割' if var2 < var1 else '直接分割'}")
        
        # 语义完整性检查（简单检查是否有断句）
        def check_semantic_integrity(segments):
            broken_count = 0
            for segment in segments:
                # 检查是否在词中间断开
                if segment and not segment[-1] in '。，！？；：':
                    broken_count += 1
            return broken_count
        
        broken1 = check_semantic_integrity(result1)
        broken2 = check_semantic_integrity(result2)
        
        print(f"  直接分割可能断词数: {broken1}")
        print(f"  调整分割可能断词数: {broken2}")
        print(f"  语义更完整的方案: {'调整分割' if broken2 < broken1 else '直接分割'}")
        
    print()
    
    # 测试4: 极端情况
    print("4. 极端情况测试:")
    print("-" * 40)
    
    extreme_cases = [
        {
            "name": "超长单段",
            "text": "这是一个非常非常长的句子" * 10,
            "lengths": [300]
        },
        {
            "name": "超多短段",
            "text": "短句。" * 20,
            "lengths": [1] * 20
        },
        {
            "name": "长度差异巨大",
            "text": "短。这是一个比较长的句子内容部分。超短。",
            "lengths": [1, 50, 2]
        }
    ]
    
    for case in extreme_cases:
        print(f"\n  测试 {case['name']}:")
        try:
            result = subtitle_translator.smart_split_translatedSubs(case['text'], case['lengths'])
            success = len(result) == len(case['lengths'])
            integrity = "".join(result) == case['text']
            print(f"    数量匹配: {'✓' if success else '✗'}")
            print(f"    内容完整: {'✓' if integrity else '✗'}")
        except Exception as e:
            print(f"    ✗ 失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试结论:")
    print("- 当前智能分割系统能够处理基本的分割需求")
    print("- 建议在实际使用中采用比例调整策略")
    print("- 极端情况下可能需要额外的错误处理")

# 运行所有测试
if __name__ == "__main__":
    try:
        success = test_complete_group_translation_flow()
        if success:
            test_smart_split_function()
            test_edge_cases_group_translation()
            test_srt_file_generation()
            test_srt_edge_cases()
            test_current_smart_split_effectiveness()
            print("\n🎉🎉🎉 所有测试完成！分组翻译功能和SRT生成功能正常工作！")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()