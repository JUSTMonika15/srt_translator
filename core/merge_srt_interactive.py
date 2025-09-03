import os
import re

def natural_key(s):
    # 提取字符串中的数字用于排序
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def list_srt_files(folder):
    files = [f for f in os.listdir(folder) if f.lower().endswith('.srt')]
    return sorted(files, key=natural_key)

def parse_srt_blocks(filepath):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    blocks = [b.strip() for b in content.strip().split('\n\n') if b.strip()]
    return [block.split('\n') for block in blocks]

def merge_srt_blocks(blocks1, blocks2):
    if len(blocks1) != len(blocks2):
        raise ValueError("两个文件的字幕条数不一致，无法合并！")
    merged = []
    for b1, b2 in zip(blocks1, blocks2):
        # 保持编号和时间轴
        idx = b1[0]
        time = b1[1]
        # 合并正文内容
        text1 = '\n'.join(b1[2:])
        text2 = '\n'.join(b2[2:])
        merged_block = f"{idx}\n{time}\n{text1}\n{text2}"
        merged.append(merged_block)
    return merged

def main():
    folder = input("请输入要合并字幕的文件夹路径：").strip('"')
    files = list_srt_files(folder)
    if len(files) < 2:
        print("该文件夹下没有足够的SRT文件。")
        return
    print("可选的SRT文件：")
    for i, f in enumerate(files):
        print(f"{i+1}: {f}")
    idx1 = int(input("请选择第一个文件编号（在上）：")) - 1
    idx2 = int(input("请选择第二个文件编号（在下）：")) - 1
    file1 = os.path.join(folder, files[idx1])
    file2 = os.path.join(folder, files[idx2])
    blocks1 = parse_srt_blocks(file1)
    blocks2 = parse_srt_blocks(file2)
    merged = merge_srt_blocks(blocks1, blocks2)
    out_dir = input("请输入输出目录（留空则为当前目录）：").strip('"')
    if not out_dir:
        out_dir = folder
    out_name = f"【合并】{files[idx1]}"
    out_path = os.path.join(out_dir, out_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(merged))
    print(f"合并完成，输出文件：{out_path}")

if __name__ == '__main__':
    main()