import os
import shutil
import json
from PIL import Image, ImageDraw, ImageFont

from add_description import desc_generate


def copy_walk_dir(source_folder, destination_folder):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder, exist_ok=True)
    for root, dirs, files in os.walk(source_folder):
        relative_path = os.path.relpath(root, source_folder)
        target_path = os.path.join(destination_folder, relative_path)
        os.makedirs(target_path, exist_ok=True)
        for file in files:
            if file.endswith(".xml"):
                continue
            source_file_path = os.path.join(root, file)
            destination_file_path = os.path.join(target_path, file)
            shutil.copy(source_file_path, destination_file_path)
            print(f"Copied: {source_file_path} to {destination_file_path}")


def screenshot_labeled(image_path, ui_positions, texts=None, extra=[], rgba=(0, 0, 255), thickness=3):
    screenshot = Image.open(image_path)
    if texts is None:
        texts = list(map(str, range(len(ui_positions))))
    width, height = screenshot.size
    if height < 900:
        font_size = 12
        thickness = 2
    elif height < 1500:
        font_size = 18
        thickness = 3
    else:
        font_size = 42
        thickness = 4
    font = ImageFont.truetype('./resources/Roboto-Regular.ttf', size=font_size, encoding="utf-8")
    with screenshot.convert('RGBA') as base:
        tmp = Image.new('RGBA', base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(tmp)
        for idx, ui_position in enumerate(ui_positions):
            x1, y1, x2, y2 = ui_position[:4]
            if x1 == x2 or y1 == y2:
                continue
            if [x1, y1, x2, y2] not in extra:
                draw.rectangle((x1, y1, x2, y2), outline=rgba, width=thickness)
            else:
                draw.rectangle((x1, y1, x2, y2), outline=(255, 0, 0), width=thickness)
            left, top, right, bottom = font.getbbox(texts[idx])
            coords = [
                x1, y1,
                x1 + right * 1.1, y1,
                x1 + right * 1.1, y1 - bottom * 1.1,
                x1, y1 - bottom * 1.1
            ]
            if [x1, y1, x2, y2] not in extra:
                draw.polygon(coords, fill=rgba)
            else:
                draw.polygon(coords, fill=(255, 0, 0))
            draw.text((x1, y1 - bottom * 1.05), texts[idx], fill=(255, 255, 255), font=font)
        out = Image.alpha_composite(base, tmp)
    return out


def aitw_process(dir):
    for subdir, _, files in os.walk(dir):
        for file in files:
            if not file.endswith('.json'):
                continue
            with open(os.path.join(subdir, file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    continue
                for item in data:
                    image_path = f'data/labeled_synthetic-data/{item.get("image_path", "")}'
                    item['image_path'] = image_path
                    ui_positions = []
                    if 'ui_positions' in item:
                        item['ui_positions'] = item['ui_positions'].replace('(', '[').replace(')', ']')
                        ui_positions = json.loads(item['ui_positions'])
                    if len(ui_positions) > 0:
                        labeled = screenshot_labeled(image_path, ui_positions)
                        labeled.save(image_path)
                with open(os.path.join(subdir, file), 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)


def crawler_process(dir):
    for subdir, _, files in os.walk(dir):
        for file in files:
            if not file.endswith('.json'):
                continue
            with open(os.path.join(subdir, file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    continue
                for item in data:
                    if 'imgs_path' not in item:
                        break
                    item['imgs_path'] = [
                        f'data/labeled_synthetic-data/{img_path.replace("./", "").replace("original_cs_data", "Defective_Close_Source")}'
                        for img_path in item['imgs_path']]
                    for idx, image_path in enumerate(item['imgs_path']):
                        ui_positions = []
                        item['ui_positions'][idx] = item['ui_positions'][idx].replace('(', '[').replace(')', ']')
                        ui_positions = json.loads(item['ui_positions'][idx])
                        if len(ui_positions) > 0:
                            labeled = screenshot_labeled(image_path, ui_positions)
                            labeled.save(image_path)
                with open(os.path.join(subdir, file), 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Processed {subdir}")


UI_DISPLAY = ["Content Display Error", "UI Layout Issue", "UI Element Missing", "UI Consistency Issue"]


def json_in_all(root_dir):
    with open('filtered_250326.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    counter_type = {"Content Display Error": 0, "UI Layout Issue": 0, "UI Element Missing": 0,
                    "UI Consistency Issue": 0, "No Defect": 0}
    for subdir, _, files in os.walk(root_dir):
        print(f"Processing {subdir}")
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(subdir, file)
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, dict):
                        continue
                    for item in data:
                        reason = []
                        if item.get('injected_defect', None):
                            strategy = item['injected_defect']['strategy']
                            s_idx = item['injected_defect']['idx']
                            for key in item['injected_defect']['selected']:
                                idx, bbox = key.split('|')
                                idx = int(idx)
                                bbox = json.loads(bbox)
                                if idx and bbox:
                                    ui_type = json.loads(item['ui_type'][s_idx])
                                    ui_text = json.loads(item['ui_text'][s_idx])
                                    reason.append(
                                        desc_generate(bbox, strategy, ui_type[idx], ui_text[idx]))
                            if "CONTENT" in strategy:
                                injected_defect = f'Content Display Error'
                            elif "MISSING" in strategy:
                                injected_defect = f'UI Element Missing'
                            elif strategy in ['EL_OVERLAPPING', 'EL_MISALIGNED', 'UNEVEN_SPACE']:
                                injected_defect = f'UI Layout Issue'
                            else:
                                injected_defect = f'{strategy}'
                            image_path = item.get('imgs_path', None)
                            if not injected_defect or not image_path:
                                continue
                            if injected_defect and injected_defect.strip() in UI_DISPLAY:
                                solution = injected_defect
                            else:
                                solution = 'No Defect'
                        else:
                            solution = 'No Defect'
                        counter_type[solution] += 1
                        for idx, image in enumerate(image_path):
                            image = f'/data10/zkj/datasets/GTArena-UI-Defects/{image}'
                            result = {
                                'image': image,
                                'problem': "You are tasked with analyzing an app screenshot to identify any GUI "
                                           "defects based on the following UI Display Defect types:\nDefect Types:\n- "
                                           "Content Display Error: Text is unreadable or displays as garbled "
                                           "characters (e.g., ‘□□□□’, null, or HTML entities), or appears in "
                                           "incorrect or unexpected formats.\n- UI Layout Issue: Overlapping, "
                                           "misaligned, or unevenly spaced elements clutter the page and obscure "
                                           "content. For example, an image or text element overlaps another, "
                                           "or similar elements have inconsistent spacing.\n- UI Element Missing: "
                                           "Essential UI element is absent, causing functionality issues or abnormal "
                                           "blank spaces. For example, image not loaded or displayed broken.\n- UI "
                                           "Consistency Issue: Inconsistent colors, element sizes, or states. For "
                                           "example, some navigation icons have different colors, font sizes vary, "
                                           "or a button appears active without interaction.\nTask:\nAnalyze the app "
                                           "screenshot to determine if any of the defects above are present. Based on "
                                           "your findings, output only the defect(s) exactly as listed. If no defects "
                                           "are observed, output No Defect.\nOutput Format:\n- If a defect is found, "
                                           "output the defect name exactly as specified.\n- If no defects are found, "
                                           "output: No Defect\nExamples:\nData Display Content Error\nUI Element "
                                           "Missing\nInconsistent Color\nNo Defect\nOnly output the specific defect("
                                           "s) or \"No Defect\" if none are present. Do not provide any additional "
                                           "explanations.\n",
                                'solution': solution,
                                'reason': reason
                            }
                            results.append(result)

    print(counter_type)
    with open('filtered_250326.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    """
    0. 该脚本请放在与待处理文件夹 Defective_Close_Source 同级的目录下 pip install Pillow
    1. python screenshot_label.py 将生成标记后的数据和汇总json文件
    ---
    copy_walk_dir 复制原来的文件夹到 labeled_{original_folder} 即 synthetic-data -> labeled_synthetic-data
    aitw_process crawler_process 分别处理AitW和开闭源的数据
    json_in_all 汇总所有数据到一个json文件中，非UI_DISPLAY的数据会被归类为No Defect
    """
    original_folder = 'Defective_Close_Source'
    labeled_folder = 'data/labeled_synthetic-data/Defective_Close_Source'
    copy_walk_dir(original_folder, labeled_folder)
    # 不需要处理的文件夹在下面删除即可
    # default ['AitW_with_Display', 'AitW_without_Display', 'Defective_Open_Source', 'Defective_Close_Source']
    # for sub in ['AitW_with_Display', 'AitW_without_Display', 'Defective_Open_Source', 'Defective_Close_Source']:
    #     target_folder = os.path.join(labeled_folder, sub)
    crawler_process(labeled_folder)
    print("SCREENSHOT LABELED DONE! Now processing all json files")
    json_in_all(labeled_folder)
    print("All DONE!")
