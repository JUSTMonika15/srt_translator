from faster_whisper import WhisperModel
import requests, json, os
import sys

def format_timestamp(seconds):
    """将秒数转换为SRT时间格式 HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_srt(segments, output_file):
    """生成SRT字幕文件"""
    with open(output_file, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n")
            f.write(f"{segment.text.strip()}\n\n")

def transcribe_audio(audio_file, model_size="medium", use_gpu=True, generate_subtitle=True):
    """
    使用 faster-whisper 转录音频
    不需要 PyTorch，支持 CUDA/CPU
    """
    print(f"加载 faster-whisper {model_size} 模型...")
    
    # 尝试GPU,失败则自动切换CPU
    model = None
    force_cpu = False
    
    if use_gpu:
        try:
            print("尝试使用GPU...")
            model = WhisperModel(model_size, device="cuda", compute_type="float16")
            print("✅ GPU模式")
        except Exception as e:
            print(f"⚠️  GPU加载失败: {e}")
            print("切换到CPU模式...")
            model = None
            force_cpu = True
    
    if model is None or force_cpu:
        if not force_cpu:
            print("使用CPU模式...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("✅ CPU模式")
    
    print(f"正在转录: {audio_file}")
    
    # 尝试转录
    try:
        segments, info = model.transcribe(audio_file, vad_filter=True)
        segments_list = list(segments)  # 转换为列表以便多次使用
        text = "".join([seg.text for seg in segments_list])
        
        # 生成SRT字幕文件
        if generate_subtitle:
            srt_file = os.path.splitext(audio_file)[0] + ".srt"
            generate_srt(segments_list, srt_file)
            print(f"📺 字幕已保存到: {srt_file}")
        
        return {"text": text, "language": info.language, "segments": segments_list}
        
    except Exception as e:
        error_msg = str(e)
        # 如果GPU转录失败（包括cuDNN错误），重试CPU
        if use_gpu and not force_cpu:
            print(f"\n⚠️  转录失败: {error_msg[:200]}")
            print("检测到GPU错误，重新尝试CPU模式...")
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            print("✅ 已切换到CPU模式")
            
            segments, info = model.transcribe(audio_file, vad_filter=True)
            segments_list = list(segments)
            text = "".join([seg.text for seg in segments_list])
            
            if generate_subtitle:
                srt_file = os.path.splitext(audio_file)[0] + ".srt"
                generate_srt(segments_list, srt_file)
                print(f"📺 字幕已保存到: {srt_file}")
            
            return {"text": text, "language": info.language, "segments": segments_list}
        else:
            print(f"\n❌ 转录失败: {error_msg}")
            raise

def translate_with_ollama(text, model="qwen3:8b"):
    url = "http://localhost:11434/api/generate"
    prompt = f"请将以下文本翻译成中文,只输出翻译结果,不要解释:\n\n{text}"
    payload = {"model": model, "prompt": prompt, "stream": False}
    print(f"使用 {model} 翻译中...")
    response = requests.post(url, json=payload)
    result = response.json()
    return result["response"].strip()

def translate_segments_with_ollama(segments, model="qwen3:8b"):
    """逐段翻译字幕"""
    url = "http://localhost:11434/api/generate"
    translated_segments = []
    
    print(f"正在翻译 {len(segments)} 个字幕片段...")
    for i, segment in enumerate(segments, 1):
        prompt = f"请将以下英文翻译成中文,只输出翻译结果,不要解释:\n\n{segment.text.strip()}"
        payload = {"model": model, "prompt": prompt, "stream": False}
        
        try:
            response = requests.post(url, json=payload)
            result = response.json()
            translated_text = result["response"].strip()
            translated_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": translated_text
            })
            print(f"  进度: {i}/{len(segments)}", end="\r")
        except Exception as e:
            print(f"\n⚠️  翻译片段 {i} 失败: {e}")
            translated_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text  # 保留原文
            })
    
    print()  # 换行
    return translated_segments

def generate_translated_srt(translated_segments, output_file):
    """生成翻译后的SRT字幕文件"""
    with open(output_file, "w", encoding="utf-8") as f:
        for i, segment in enumerate(translated_segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(segment['start'])} --> {format_timestamp(segment['end'])}\n")
            f.write(f"{segment['text']}\n\n")

def process_audio(audio_file, whisper_model="medium", ollama_model="qwen3:8b", use_gpu=True, translate=True, translate_srt=True):
    try:
        result = transcribe_audio(audio_file, whisper_model, use_gpu, generate_subtitle=True)
        original_text = result["text"]
        detected_language = result["language"]
        segments = result["segments"]
        
        print(f"\n✅ 检测到的语言: {detected_language}")
        print(f"\n📝 原文:\n{original_text[:500]}...\n")  # 只显示前500字符

        if translate:
            print("🔄 正在翻译全文...")
            translated_text = translate_with_ollama(original_text, ollama_model)
            print(f"\n🇨🇳 中文翻译:\n{translated_text[:500]}...\n")

            output_file = os.path.splitext(audio_file)[0] + "_转录.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"原文 ({detected_language}):\n{original_text}\n\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"中文翻译:\n{translated_text}\n")
            print(f"💾 结果已保存到: {output_file}")
            
            # 生成翻译字幕
            if translate_srt:
                print("\n🔄 正在生成中文字幕...")
                translated_segments = translate_segments_with_ollama(segments, ollama_model)
                translated_srt_file = os.path.splitext(audio_file)[0] + "_中文.srt"
                generate_translated_srt(translated_segments, translated_srt_file)
                print(f"📺 中文字幕已保存到: {translated_srt_file}")
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()

def interactive_mode():
    """交互式模式"""
    print("=" * 60)
    print("🎤 音频转录+翻译+字幕工具")
    print("=" * 60)
    
    # 让用户输入文件夹路径
    folder_path = input("\n请输入音频文件所在的文件夹路径 (按q退出): ").strip()
    
    if folder_path.lower() == 'q':
        print("退出程序")
        return None
    
    # 去除可能的引号
    folder_path = folder_path.strip('"').strip("'")
    
    # 如果为空，使用当前目录
    if not folder_path:
        folder_path = '.'
    
    if not os.path.exists(folder_path):
        print(f"❌ 找不到文件夹: {folder_path}")
        return None
    
    if not os.path.isdir(folder_path):
        print(f"❌ 这不是一个文件夹: {folder_path}")
        return None
    
    # 列出文件夹中的音频文件
    audio_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4']
    audio_files = [f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in audio_extensions]
    
    if not audio_files:
        print(f"\n❌ 在 {folder_path} 中没有找到音频文件")
        return None
    
    print(f"\n在 {folder_path} 中找到 {len(audio_files)} 个音频文件:")
    for i, f in enumerate(audio_files, 1):
        file_path = os.path.join(folder_path, f)
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"  {i}. {f} ({size_mb:.1f} MB)")
    
    choice = input("\n请输入文件编号 (按q退出): ").strip()
    
    if choice.lower() == 'q':
        print("退出程序")
        return None
    
    if choice.isdigit() and 1 <= int(choice) <= len(audio_files):
        audio_file = os.path.join(folder_path, audio_files[int(choice) - 1])
    else:
        print("❌ 无效的选择")
        return None
    
    if not os.path.exists(audio_file):
        print(f"❌ 找不到文件: {audio_file}")
        return None
    
    # 选择模型大小
    print("\n" + "=" * 60)
    print("选择Whisper模型 (影响准确度和速度):")
    print("  1. tiny    - 最快,准确度最低 (~1GB显存)")
    print("  2. base    - 较快,准确度较低 (~1GB显存)")
    print("  3. small   - 平衡 (~2GB显存)")
    print("  4. medium  - 推荐,准确度高 (~5GB显存) [默认]")
    print("  5. large   - 最准确,最慢 (~10GB显存)")
    
    model_choice = input("\n请选择 [1-5, 默认4]: ").strip()
    model_map = {"1": "tiny", "2": "base", "3": "small", "4": "medium", "5": "large"}
    whisper_model = model_map.get(model_choice, "medium")
    
    # 选择GPU/CPU
    print("\n提示: 如果CUDA库有问题,建议选择CPU模式")
    gpu_choice = input("尝试使用GPU? [Y/n]: ").strip().lower()
    use_gpu = gpu_choice in ['', 'y', 'yes']
    
    # 选择是否翻译
    translate_choice = input("是否翻译成中文? [Y/n]: ").strip().lower()
    translate = translate_choice in ['', 'y', 'yes']
    
    # 选择是否生成中文字幕
    translate_srt = False
    if translate:
        srt_choice = input("是否生成中文字幕? (需要逐段翻译,较慢) [Y/n]: ").strip().lower()
        translate_srt = srt_choice in ['', 'y', 'yes']
    
    # 确认开始处理
    print("\n" + "=" * 60)
    print(f"📁 文件: {audio_file}")
    print(f"🤖 模型: {whisper_model}")
    print(f"⚡ 设备: {'GPU(自动回退CPU)' if use_gpu else 'CPU'}")
    print(f"📺 字幕: 原文SRT + {'中文SRT' if translate_srt else '无中文字幕'}")
    print(f"🌐 翻译: {'qwen3:8b' if translate else '不翻译'}")
    print("=" * 60)
    
    confirm = input("\n开始处理? [Y/n]: ").strip().lower()
    if confirm in ['', 'y', 'yes']:
        return audio_file, whisper_model, use_gpu, translate, translate_srt
    else:
        print("取消处理")
        return None

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            # 命令行模式
            audio_file = sys.argv[1]
            whisper_model = sys.argv[2] if len(sys.argv) > 2 else "medium"
            
            if os.path.exists(audio_file):
                process_audio(audio_file, whisper_model, use_gpu=False)  # 命令行默认CPU
            else:
                print(f"❌ 找不到文件: {audio_file}")
        else:
            # 交互式模式
            result = interactive_mode()
            if result:
                audio_file, whisper_model, use_gpu, translate, translate_srt = result
                print("\n开始处理...\n")
                process_audio(audio_file, whisper_model, use_gpu=use_gpu, translate=translate, translate_srt=translate_srt)
                
                # 询问是否继续处理其他文件
                while True:
                    again = input("\n是否继续处理其他文件? [Y/n]: ").strip().lower()
                    if again in ['', 'y', 'yes']:
                        result = interactive_mode()
                        if result:
                            audio_file, whisper_model, use_gpu, translate, translate_srt = result
                            print("\n开始处理...\n")
                            process_audio(audio_file, whisper_model, use_gpu=use_gpu, translate=translate, translate_srt=translate_srt)
                        else:
                            break
                    else:
                        print("感谢使用!")
                        break
    except KeyboardInterrupt:
        print("\n\n👋 感谢使用!")
        sys.exit(0)
