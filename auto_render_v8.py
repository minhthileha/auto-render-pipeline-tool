import sys
import os
import re
import subprocess
import datetime
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

def get_ffmpeg_path():
    """Tìm FFmpeg bị nhét vô file .exe"""
    if hasattr(sys, '_MEIPASS'):
        # Khi chạy bằng file .exe, PyInstaller sẽ giải nén ffmpeg ra thư mục tạm
        return os.path.join(sys._MEIPASS, 'ffmpeg.exe')
    return 'ffmpeg' # Khi đang test bằng file .py bình thường

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def execute_render_thread(mode, folder_path, fps, codec, hardware, list_file_path, files):
    folder_name = os.path.basename(os.path.normpath(folder_path))
    log_file_path = os.path.join(folder_path, f"{folder_name}_RenderLog.txt")
    
    cmd = []
    if mode == "image2mp4":
        output_path = os.path.join(folder_path, f"{folder_name}_{codec.upper()}.mp4")
        
        if hardware == "nvidia":
            cmd = ['ffmpeg', '-y', '-threads', '4', '-r', str(fps), '-f', 'concat', '-safe', '0', '-i', list_file_path]
            if codec == "hevc":
                cmd.extend(['-c:v', 'hevc_nvenc', '-preset', 'p6', '-tune', 'hq', '-rc', 'vbr', '-cq', '21', '-b:v', '0', '-tag:v', 'hvc1'])
            else:
                cmd.extend(['-c:v', 'h264_nvenc', '-preset', 'p6', '-tune', 'hq', '-rc', 'vbr', '-cq', '18', '-b:v', '0'])
        else:
            cmd = ['ffmpeg', '-y', '-threads', '2', '-r', str(fps), '-f', 'concat', '-safe', '0', '-i', list_file_path]
            if codec == "hevc":
                cmd.extend(['-c:v', 'libx265', '-crf', '24', '-preset', 'fast', '-tag:v', 'hvc1'])
            else:
                cmd.extend(['-c:v', 'libx264', '-crf', '18', '-preset', 'fast'])
                
        cmd.extend(['-pix_fmt', 'yuv420p', output_path])
        
    else: 
        output_path = os.path.join(folder_path, f"FULL_MERGED_{folder_name}.mp4")
        cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file_path, '-c', 'copy', output_path]
    
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            log_file.write(f"=== BẮT ĐẦU CHẠY ===\n")
            log_file.write(f"Lệnh chạy: {' '.join(cmd)}\n")
            log_file.write(f"----------------------------------------\n\n")
            subprocess.run(cmd, startupinfo=startupinfo, stdout=log_file, stderr=subprocess.STDOUT, check=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
            os.remove(list_file_path) 
            app.after(0, lambda: status_label.configure(text="Xong gòi!", text_color="#2FA572"))
            app.after(0, lambda: messagebox.showinfo("Done!", f"Xử lý thành công!\nFile lưu tại: {output_path}"))
        else:
            raise Exception("File xuất ra bị 0KB.")

    except subprocess.CalledProcessError:
        app.after(0, lambda: messagebox.showerror("Lỗi rùi", f"Vào thư mục mở file:\n{folder_name}_RenderLog.txt\nđể xem log chi tiết nha!"))
        app.after(0, lambda: status_label.configure(text="Lỗi rồi, check file log đi!", text_color="red"))
    except Exception as e:
        app.after(0, lambda: messagebox.showerror("Lỗi kĩ thuật", f"Phát hiện vấn đề:\n{e}"))
        app.after(0, lambda: status_label.configure(text="Sẵn sàng", text_color="gray"))
    finally:
        # Tắt thanh loading và bật lại nút
        app.after(0, progress_bar.stop)
        app.after(0, progress_bar.pack_forget) # Giấu thanh loading đi cho gọn
        app.after(0, lambda: btn_render.configure(state="normal", text="RUN"))

def run_render():
    mode = mode_var.get()
    folder_path = folder_var.get()
    fps = fps_var.get()
    codec = codec_var.get()
    hardware = hw_var.get()
    
    if not folder_path:
        messagebox.showwarning("Cảnh báo", "Chưa chọn folder kìa!")
        return
        
    if mode == "image2mp4":
        extensions = ('.png', '.jpg', '.jpeg', '.exr')
    else:
        extensions = ('.mp4', '.mov', '.avi', '.mkv')
        
    files = []
    try:
        for f in os.listdir(folder_path):
            full_path = os.path.join(folder_path, f)
            if os.path.isfile(full_path) and f.lower().endswith(extensions):
                files.append(f)
        files.sort(key=natural_sort_key)
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không đọc được folder: {e}")
        return
        
    if not files:
        loai_file = "ẢNH" if mode == "image2mp4" else "VIDEO"
        messagebox.showerror("Lỗi", f"Không tìm thấy {loai_file} trong folder này!")
        return
        
    list_file_path = os.path.join(folder_path, "file_list_temp.txt")
    with open(list_file_path, "w", encoding="utf-8") as f:
        for file_name in files:
            safe_name = file_name.replace("'", "'\\''")
            f.write(f"file '{safe_name}'\n")
            
    status_label.configure(text="Đang xử lý... Đợi xíu!", text_color="#3B8ED0")
    btn_render.configure(state="disabled", text="ĐANG RENDER...") 
    
    # Hiện thanh Loading và nó chạy
    progress_bar.pack(pady=(0, 10))
    progress_bar.start()
    app.update()
    
    threading.Thread(target=execute_render_thread, args=(mode, folder_path, fps, codec, hardware, list_file_path, files), daemon=True).start()

def browse_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_var.set(folder)

# ==========================================
# GIAO DIỆN v8 - CÓ THANH LOADING
# ==========================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")  

app = ctk.CTk()
app.title("Auto Render Tool v8")
app.geometry("540x460") # Kéo form dài ra xíu nữa
app.eval('tk::PlaceWindow . center')

folder_var = ctk.StringVar()
mode_var = ctk.StringVar(value="image2mp4")
fps_var = ctk.IntVar(value=30)
codec_var = ctk.StringVar(value="h264")
hw_var = ctk.StringVar(value="nvidia")

title_label = ctk.CTkLabel(app, text="AUTO RENDER TOOL v8", font=ctk.CTkFont(size=22, weight="bold"))
title_label.pack(pady=(15, 10))

frame_mode = ctk.CTkFrame(app, fg_color="transparent")
frame_mode.pack(pady=5)
ctk.CTkLabel(frame_mode, text="Chế độ:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
ctk.CTkRadioButton(frame_mode, text="Ghép nhiều ảnh", variable=mode_var, value="image2mp4", cursor="hand2").pack(side="left", padx=10)
ctk.CTkRadioButton(frame_mode, text="Ghép nhiều Video", variable=mode_var, value="merge_mp4", cursor="hand2").pack(side="left", padx=10)

frame_folder = ctk.CTkFrame(app, fg_color="transparent")
frame_folder.pack(pady=5, padx=20, fill="x")
folder_entry = ctk.CTkEntry(frame_folder, textvariable=folder_var, width=320, state="readonly", placeholder_text="Đường dẫn folder...")
folder_entry.pack(side="left", padx=(0, 10))
ctk.CTkButton(frame_folder, text="Chọn file or folder", command=browse_folder, width=90, cursor="hand2").pack(side="left")

frame_hw = ctk.CTkFrame(app, fg_color="transparent")
frame_hw.pack(pady=5)
ctk.CTkLabel(frame_hw, text="Máy tính:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
ctk.CTkRadioButton(frame_hw, text="NVIDIA", variable=hw_var, value="nvidia", cursor="hand2").pack(side="left", padx=10)
ctk.CTkRadioButton(frame_hw, text="CPU", variable=hw_var, value="cpu", cursor="hand2").pack(side="left", padx=10)

frame_codec = ctk.CTkFrame(app, fg_color="transparent")
frame_codec.pack(pady=5)
ctk.CTkLabel(frame_codec, text="Định dạng:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
ctk.CTkRadioButton(frame_codec, text="H.264 (Chuẩn)", variable=codec_var, value="h264", cursor="hand2").pack(side="left", padx=10)
ctk.CTkRadioButton(frame_codec, text="H.265 (Siêu nhẹ)", variable=codec_var, value="hevc", cursor="hand2").pack(side="left", padx=10)

frame_fps = ctk.CTkFrame(app, fg_color="transparent")
frame_fps.pack(pady=5)
ctk.CTkLabel(frame_fps, text="Tốc độ:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
ctk.CTkRadioButton(frame_fps, text="24 FPS", variable=fps_var, value=24, cursor="hand2").pack(side="left", padx=10)
ctk.CTkRadioButton(frame_fps, text="30 FPS", variable=fps_var, value=30, cursor="hand2").pack(side="left", padx=10)

btn_render = ctk.CTkButton(app, text="RUN", command=run_render, font=ctk.CTkFont(size=14, weight="bold"), height=40, width=260, fg_color="#2FA572", hover_color="#207A53", cursor="hand2")
btn_render.pack(pady=(15, 5))

# --- KHỞI TẠO THANH LOADING (Nhưng ẩn khi nào chạy mới hiện) ---
progress_bar = ctk.CTkProgressBar(app, mode="indeterminate", width=260)

status_label = ctk.CTkLabel(app, text="Sẵn sàng cày deadline", text_color="gray", font=ctk.CTkFont(size=12, slant="italic"))
status_label.pack(side="bottom", pady=5)

app.mainloop()
