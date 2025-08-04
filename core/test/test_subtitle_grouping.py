import sys
import os

# 获取项目根目录（向上两级）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from core.subtitle_translator import Subtitle, SmartSubtitleTranslator

def test_group_subtitles_by_speaker():
    """测试说话人分组功能"""
    
    # 创建测试字幕数据
    test_subtitles = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "ORION: I wanted to know..."),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "And maybe also..."),
        Subtitle("3", "00:00:07,000", "00:00:09,000", "What about this?"),
        Subtitle("4", "00:00:10,000", "00:00:12,000", "MATT: The price would be..."),
        Subtitle("5", "00:00:13,000", "00:00:15,000", "You can find it in..."),
        Subtitle("6", "00:00:16,000", "00:00:18,000", "ORION: But wait..."),
        Subtitle("7", "00:00:19,000", "00:00:21,000", "I think we should..."),
        Subtitle("8", "00:00:22,000", "00:00:24,000", "LAURA: That's interesting..."),
        Subtitle("9", "00:00:25,000", "00:00:27,000", "Maybe we could try..."),
        Subtitle("10", "00:00:28,000", "00:00:30,000", "No speaker line here"),
    ]
    
    # 创建翻译器实例（不需要真实的translator）
    translator = SmartSubtitleTranslator(translator=None)
    
    # 执行分组
    groups = translator.group_subtitles_by_speaker(test_subtitles)
    
    # 打印结果
    print("=== 分组测试结果 ===")
    print(f"原字幕总数: {len(test_subtitles)}")
    print(f"分组数量: {len(groups)}")
    print()
    
    total_subs_in_groups = 0
    for i, group in enumerate(groups):
        print(f"第 {i+1} 组 (共 {len(group)} 条字幕):")
        for sub in group:
            print(f"  {sub.index}: {sub.text}")
        total_subs_in_groups += len(group)
        print()
    
    print(f"分组中字幕总数: {total_subs_in_groups}")
    print(f"数量是否匹配: {total_subs_in_groups == len(test_subtitles)}")
    
    # 验证期望的分组结果
    expected_groups = [
        ["ORION: I wanted to know...", "And maybe also...", "What about this?"],
        ["MATT: The price would be...", "You can find it in..."],
        ["ORION: But wait...", "I think we should..."],
        ["LAURA: That's interesting...", "Maybe we could try...", "No speaker line here"]
    ]
    
    print("\n=== 验证期望结果 ===")
    if len(groups) == len(expected_groups):
        print("✓ 分组数量正确")
        
        all_correct = True
        for i, (actual_group, expected_texts) in enumerate(zip(groups, expected_groups)):
            actual_texts = [sub.text for sub in actual_group]
            if actual_texts == expected_texts:
                print(f"✓ 第 {i+1} 组内容正确")
            else:
                print(f"✗ 第 {i+1} 组内容错误")
                print(f"  期望: {expected_texts}")
                print(f"  实际: {actual_texts}")
                all_correct = False
        
        if all_correct:
            print("\n🎉 所有测试通过！分组逻辑正确！")
        else:
            print("\n❌ 部分测试失败，需要检查分组逻辑")
    else:
        print(f"✗ 分组数量错误，期望: {len(expected_groups)}, 实际: {len(groups)}")

def test_edge_cases():
    """测试边缘情况"""
    print("\n=== 边缘情况测试 ===")
    
    translator = SmartSubtitleTranslator(translator=None)
    
    # 测试1: 空字幕列表
    empty_groups = translator.group_subtitles_by_speaker([])
    print(f"空列表分组结果: {len(empty_groups)} 组")
    
    # 测试2: 只有一条字幕
    single_sub = [Subtitle("1", "00:00:01,000", "00:00:03,000", "ORION: Hello")]
    single_groups = translator.group_subtitles_by_speaker(single_sub)
    print(f"单条字幕分组结果: {len(single_groups)} 组")
    
    # 测试3: 全部没有说话人标识
    no_speaker_subs = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "Just some text"),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "More text here"),
        Subtitle("3", "00:00:07,000", "00:00:09,000", "Even more text"),
    ]
    no_speaker_groups = translator.group_subtitles_by_speaker(no_speaker_subs)
    print(f"无说话人字幕分组结果: {len(no_speaker_groups)} 组，包含 {len(no_speaker_groups[0]) if no_speaker_groups else 0} 条字幕")
    
    # 测试4: 每条字幕都有不同说话人
    different_speakers = [
        Subtitle("1", "00:00:01,000", "00:00:03,000", "ORION: Hello"),
        Subtitle("2", "00:00:04,000", "00:00:06,000", "MATT: Hi"),
        Subtitle("3", "00:00:07,000", "00:00:09,000", "LAURA: Hey"),
    ]
    different_groups = translator.group_subtitles_by_speaker(different_speakers)
    print(f"不同说话人字幕分组结果: {len(different_groups)} 组")

if __name__ == "__main__":
    test_group_subtitles_by_speaker()
    test_edge_cases()