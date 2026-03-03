from rapidocr_onnxruntime import RapidOCR
import os
import sys

def get_model_path():
    """
    获取打包后/未打包时的模型路径（适配EXE运行和本地运行）
    """
    # 判断是否是打包后的EXE环境
    if getattr(sys, 'frozen', False):
        # EXE运行时，根目录是EXE所在目录
        base_path = sys._MEIPASS  # PyInstaller打包后的临时解压目录
    else:
        # 本地Python运行时，根目录是脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # 拼接模型路径
    det_model = os.path.join(base_path, "models", "ch_PP-OCRv5_mobile_det.onnx")
    rec_model = os.path.join(base_path, "models", "ch_PP-OCRv5_rec_mobile_infer.onnx")
    return det_model, rec_model

def rapid_ocr_recognize(img_path):
    if not os.path.exists(img_path):
        print(f"❌ 未找到文件：{img_path}")
        return

    # 1. 获取本地模型路径
    det_model, rec_model = get_model_path()
    # 2. 初始化RapidOCR，指定本地模型（禁用自动下载）
    ocr = RapidOCR(
        det_model_path=det_model,  # 检测模型本地路径
        rec_model_path=rec_model,  # 识别模型本地路径
        use_angle_cls=False       # 关闭角度检测，提速
    )

    # 3. 识别图片
    result, elapse = ocr(img_path)

    # 4. 输出结果
    if result:
        for line in result:
            if isinstance(line, list) and len(line) == 3:
                box, text, score = line
                if len(box) >= 2:
                    x1, y1 = box[0]
                    x2, y2 = box[2]
                    try:
                        score = float(score)
                        print(f"{text}|{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}|{score:.2f}")
                    except ValueError:
                        print(f"{text}|{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}|{score}")

if __name__ == "__main__":
    rapid_ocr_recognize("wechat_screenshot.png")