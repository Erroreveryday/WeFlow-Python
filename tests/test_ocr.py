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
    print("\n===== RapidOCR识别结果 =====")
    print(f"elapse类型：{type(elapse)}")
    print(f"elapse值：{elapse}")
    # 处理elapse，确保它是一个数字
    if isinstance(elapse, list):
        # 如果是列表，取第一个元素或总和
        if elapse:
            elapse = sum(elapse) if all(isinstance(item, (int, float)) for item in elapse) else elapse[0]
        else:
            elapse = 0
    print(f"识别耗时：{elapse:.2f}秒")
    
    # 查看result结构
    print(f"result类型：{type(result)}")
    print(f"result值：{result}")
    
    # 处理result
    if result:
        for line in result:
            print(f"line类型：{type(line)}")
            print(f"line值：{line}")
            if isinstance(line, list):
                # 根据实际结构处理
                if len(line) == 3:
                    # 实际结构是 [[[x1, y1], [x2, y2], [x3, y3], [x4, y4]], 'text', 'score']
                    box, text, score = line
                    # 取左上角和右下角坐标
                    if len(box) >= 2:
                        x1, y1 = box[0]
                        x2, y2 = box[2]  # 第三个点是右下角
                        # 将score转换为浮点数
                        try:
                            score = float(score)
                            print(f"文字：{text} | 位置：({x1:.0f},{y1:.0f})~({x2:.0f},{y2:.0f}) | 置信度：{score:.2f}")
                        except ValueError:
                            print(f"文字：{text} | 位置：({x1:.0f},{y1:.0f})~({x2:.0f},{y2:.0f}) | 置信度：{score}")
                    else:
                        print(f"未知box结构：{box}")
                elif len(line) == 6:
                    # 原始结构 [x1, y1, x2, y2, text, score]
                    x1, y1, x2, y2, text, score = line
                    print(f"文字：{text} | 位置：({x1:.0f},{y1:.0f})~({x2:.0f},{y2:.0f}) | 置信度：{score:.2f}")
                else:
                    print(f"未知结构：{line}")

if __name__ == "__main__":
    rapid_ocr_recognize("wechat_screenshot.png")
    input("按回车键退出...")