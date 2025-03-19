import json
import os
import random
from dataclasses import asdict

from config import load_config
from uidm import utils
from uidm.ui_defects import UIDefectInjection, strategies

configs = load_config()

difficulties = {
    'simple': 1,
    'medium': 2,
    'hard': 5
}


def ui_defect_mocker(screenshot_path, ui_positions, ui_texts, difficulty=None, selected=None):
    injected_defect = {
        "idx": selected,
        "strategy": "",
        "selected": [],
    }
    uidi = UIDefectInjection(screenshot_path, ui_positions, ui_texts)
    if difficulty:
        uidi.difficulty = difficulty
    selected_strategy = random.choice(configs["STRATEGY"])
    if len(uidi.ui_positions) == 0:
        return uidi
    defect_cnt = difficulties[uidi.difficulty]
    if "CONTENT" in selected_strategy:
        non_empty_text_indices = [idx for idx, text in enumerate(uidi.ui_texts) if text.strip()]
        if non_empty_text_indices:
            while defect_cnt > 0 and non_empty_text_indices:
                uidi.selected = random.choice(non_empty_text_indices)
                non_empty_text_indices.remove(uidi.selected)
                strategies[selected_strategy](uidi)
                defect_cnt -= 1
                injected_defect["selected"].append(f"{uidi.selected}|{ui_positions[uidi.selected]}")
        else:
            selected_strategy = random.choice(configs["STRATEGY"][2:])
            while defect_cnt > 0:
                uidi.selected = random.choice(range(len(uidi.ui_positions)))
                strategies[selected_strategy](uidi)
                defect_cnt -= 1
                injected_defect["selected"].append(f"{uidi.selected}|{ui_positions[uidi.selected]}")
    else:
        while defect_cnt > 0:
            uidi.selected = random.choice(range(len(uidi.ui_positions)))
            strategies[selected_strategy](uidi)
            defect_cnt -= 1
            injected_defect["selected"].append(f"{uidi.selected}|{ui_positions[uidi.selected]}")

        # uidi.selected = random.choice(range(len(uidi.ui_positions)))
    # strategies[selected_strategy](uidi)
    injected_defect['selected'] = list(dict.fromkeys(injected_defect['selected']))
    injected_defect['strategy'] = selected_strategy
    uidi.injected_defect = injected_defect
    # uidi.injected_defect = f'{selected_strategy}|{uidi.selected}|{uidi.ui_positions[uidi.selected]}'
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
