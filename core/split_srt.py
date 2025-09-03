import re
import os

def parse_srt_file(file_path):
    """解析SRT文件，返回字幕条目列表"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 分割字幕块
    subtitle_blocks = re.split(r'\n\s*\n', content.strip())
    subtitles = []
    
    for block in subtitle_blocks:
        if block.strip():
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                subtitle_id = lines[0].strip()
                time_line = lines[1].strip()
                text_lines = lines[2:]
                text = '\n'.join(text_lines)
                
                subtitles.append({
                    'id': subtitle_id,
                    'time': time_line,
                    'text': text
                })
    
    return subtitles

def extract_speaker(text):
    """提取说话人姓名"""
    # 匹配格式：姓名: 内容 或 姓名：内容
    match = re.match(r'^([^:：]+)[：:]', text)
    if match:
        return match.group(1).strip()
    return None

def find_split_points(subtitles, chunk_size=400):
    """找到合适的分割点，确保不在对话中间分割"""
    split_points = [0]
    current_speaker = None
    speaker_start = 0
    
    for i, subtitle in enumerate(subtitles):
        speaker = extract_speaker(subtitle['text'])
        
        if speaker:
            # 如果发现新的说话人
            if current_speaker and speaker != current_speaker:
                # 前一个说话人结束了
                # 检查是否应该在这里分割
                if i >= split_points[-1] + chunk_size:
                    split_points.append(i)
                speaker_start = i
            elif not current_speaker:
                # 第一次遇到说话人
                speaker_start = i
            
            current_speaker = speaker
        else:
            # 没有说话人标识的字幕，可能是同一人继续说话
            # 检查是否需要强制分割（如果距离上次分割太远）
            if i >= split_points[-1] + chunk_size * 1.5:  # 允许一定的溢出
                split_points.append(i)
                current_speaker = None
    
    return split_points

def save_subtitle_chunk(subtitles, start_idx, end_idx, output_path):
    """保存字幕片段到文件，保留原始编号"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for subtitle in subtitles[start_idx:end_idx]:
            f.write(f"{subtitle['id']}\n")
            f.write(f"{subtitle['time']}\n")
            f.write(f"{subtitle['text']}\n\n")

def split_srt_file(input_file, chunk_size=400):
    """分割SRT文件"""
    # 获取脚本所在目录和文件信息
    input_dir = os.path.dirname(os.path.abspath(input_file))
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    # 创建输出目录（固定为split）
    output_folder = os.path.join(input_dir, "split")
    os.makedirs(output_folder, exist_ok=True)
    
    # 解析字幕文件
    print("正在解析字幕文件...")
    subtitles = parse_srt_file(input_file)
    print(f"总共找到 {len(subtitles)} 条字幕")
    
    # 找到分割点
    print("正在寻找合适的分割点...")
    split_points = find_split_points(subtitles, chunk_size)
    split_points.append(len(subtitles))  # 添加结束点
    
    print(f"将分割为 {len(split_points)-1} 个文件")
    
    # 分割并保存文件
    for i in range(len(split_points)-1):
        start_idx = split_points[i]
        end_idx = split_points[i+1]
        
        # 生成文件名
        if i == 0:
            filename = f"1-{end_idx}.srt"
        else:
            filename = f"{start_idx+1}-{end_idx}.srt"
        
        output_path = os.path.join(output_folder, filename)
        save_subtitle_chunk(subtitles, start_idx, end_idx, output_path)
        
        print(f"已保存: {filename} (字幕 {start_idx+1}-{end_idx}, 共 {end_idx-start_idx} 条)")
    
    print(f"\n分割完成！文件保存在: {output_folder}")

def main():
    # 让用户输入目录
    input_dir = input("请输入包含SRT文件的目录（留空则为当前脚本目录）: ").strip()
    if not input_dir:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    else:
        script_dir = os.path.abspath(input_dir)
    
    # 在同文件夹搜索SRT文件
    srt_files = [f for f in os.listdir(script_dir) if f.lower().endswith('.srt')]
    
    if not srt_files:
        print("在当前目录没有找到SRT文件！")
        return
    
    if len(srt_files) == 1:
        input_file = os.path.join(script_dir, srt_files[0])
        print(f"找到SRT文件: {srt_files[0]}")
    else:
        print("找到多个SRT文件:")
        for i, file in enumerate(srt_files, 1):
            print(f"{i}. {file}")
        
        try:
            choice = int(input("请选择要处理的文件编号: ")) - 1
            if 0 <= choice < len(srt_files):
                input_file = os.path.join(script_dir, srt_files[choice])
            else:
                print("无效的选择！")
                return
        except ValueError:
            print("请输入有效的数字！")
            return
    
    # 询问分割大小
    try:
        chunk_size = int(input("请输入每个文件的字幕数量 (默认400): ") or "400")
    except ValueError:
        chunk_size = 400
        print("使用默认值: 400")
    
    # 执行分割
    split_srt_file(input_file, chunk_size)

if __name__ == "__main__":
    main()
