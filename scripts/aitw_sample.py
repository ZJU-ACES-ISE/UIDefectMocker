import json
import os
import random
import sys
from typing import List, Tuple

from PIL import Image

from config import load_config
from uidm import utils
from uidm.ui_defects import UIDefectInjection
from uidm.utils import copy_walk_dir
from uidm_main import ui_defect_mocker

configs = load_config()


def extract_ui_positions(img_size, bboxes: List[Tuple[float, float, float, float]]):
    ex_bboxes = []
    w, h = img_size
    for idx, bbox in enumerate(bboxes):
        y1, x1, height, width = bbox[:4]
        x2, y2 = x1 + width, y1 + height
        x1 = min(max(0, x1), w) - 5
        x2 = min(max(x1, x2), w) + 5
        y1 = min(max(0, y1), h) - 3
        y2 = min(max(y1, y2), h) + 3
        ex_bboxes.append((x1, y1, x2, y2))
    return ex_bboxes


def check_inside(x, y, bbox_array):
    for idx, bbox in enumerate(bbox_array):
        x_min, y_min, x_max, y_max = bbox
        if (x_min <= x <= x_max) and (y_min <= y <= y_max):
            return idx, bbox

    return None, None


def extract_aitz_data():
    input_dir = configs['INPUT_DIR']
    saved_dir = configs['SAVED_DIR']
    copy_walk_dir(input_dir, saved_dir)
    json_path = os.path.join(saved_dir, f'{os.path.basename(saved_dir)}.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    json_data = [{**item, "injected_defect": ""} for item in json_data]
    item_len = len(json_data)
    if item_len < 3:
        return
    if item_len > 8:
        count = 3
    else:
        count = 2 if item_len > 5 else 1
    selected = [random.randint(0, item_len - 2)]
    flag = True
    while count > 0:
        tmp = random.choice([x for x in range(0, item_len - 1) if x not in selected])
        selected.append(tmp)
        count -= 1
    for idx, item in enumerate(json_data):
        img_name = os.path.basename(item['image_path'])
        img_path = os.path.join(saved_dir, img_name)
        img_size = Image.open(img_path).size
        ui_positions = extract_ui_positions(img_size, json.loads(item['ui_positions']))
        ui_texts = json.loads(item['ui_text'])
        if idx in selected:
            if flag:
                y, x = json.loads(item['result_touch_yx'])
                tmp_idx, selected_coords = check_inside(x, y, ui_positions)
                if tmp_idx is None:
                    tmp_idx = random.randint(0, len(ui_positions) - 1)
                else:
                    flag = False
            else:
                tmp_idx = random.randint(0, len(ui_positions) - 1)
            uidi = ui_defect_mocker(img_path, ui_positions, ui_texts, tmp_idx)
            item['injected_defect'] = uidi.injected_defect
        else:
            uidi = UIDefectInjection(img_path, ui_positions, ui_texts)
        item['ui_positions'] = str(uidi.ui_positions)
        if configs["OUTPUT_WITH_LABELED"]:
            uidi.labeled_path = os.path.join(configs['SAVED_DIR'], f"labeled_{os.path.basename(uidi.image_path)}")
            labeled = utils.screenshot_labeled(uidi)
            labeled.save(uidi.labeled_path)
            item['labeled_path'] = uidi.labeled_path
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)


if __name__ == '__main__':
    extract_aitz_data()
