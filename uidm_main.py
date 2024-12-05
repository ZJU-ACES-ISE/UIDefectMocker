import json
import os
import random
from dataclasses import asdict

from config import load_config
from uidm import utils
from uidm.ui_defects import UIDefectInjection, strategies

configs = load_config()


def ui_defect_mocker(screenshot_path, ui_positions, ui_texts, selected=None):
    uidi = UIDefectInjection(screenshot_path, ui_positions, ui_texts)
    if selected:
        uidi.selected = selected
    selected_strategy = random.choice(configs["STRATEGY"])
    if "CONTENT" in selected_strategy:
        non_empty_text_indices = [idx for idx, text in enumerate(uidi.ui_texts) if text.strip()]
        if non_empty_text_indices:
            uidi.selected = random.choice(non_empty_text_indices)
        else:
            selected_strategy = random.choice(configs["STRATEGY"][2:])
            uidi.selected = random.choice(range(len(uidi.ui_positions)))
    else:
        uidi.selected = random.choice(range(len(uidi.ui_positions)))
    strategies[selected_strategy](uidi)

    uidi.injected_defect = f'{selected_strategy}|{uidi.selected}|{uidi.ui_positions[uidi.selected]}'
    if configs["OUTPUT_WITH_LABELED"]:
        uidi.labeled_path = os.path.join(configs['SAVED_DIR'], f"labeled_{os.path.basename(uidi.image_path)}")
        labeled = utils.screenshot_labeled(uidi)
        labeled.save(uidi.labeled_path)
    if not configs['JSON_RECORD']:
        return uidi
    uidi_dict = asdict(uidi)
    saved_dir = configs['SAVED_DIR']
    json_path = os.path.join(saved_dir, f'{os.path.basename(saved_dir)}.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
        data.append(uidi_dict)
    else:
        data = [uidi_dict]
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    return uidi


if __name__ == '__main__':
    input_dir = configs["INPUT_DIR"]
    saved_dir = configs["SAVED_DIR"]
    xml_dir = configs["XML_DIR"]
    if input_dir != saved_dir:
        utils.copy_walk_dir(input_dir, saved_dir)
    screenshots = [f for f in os.listdir(input_dir) if f.endswith('.png')]
    for screenshot in screenshots:
        xml_path = os.path.join(xml_dir, f'{os.path.basename(screenshot).replace(".png", ".xml")}')
        el_list = utils.extract_xml(xml_path)
        ui_defect_mocker(screenshot, [el.bbox for el in el_list], [el.text for el in el_list])
