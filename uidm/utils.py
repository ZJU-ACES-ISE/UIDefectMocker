import os
import shutil
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

from config import load_config
from uidm.ui_defects import UIDefectInjection

configs = load_config()


class UIElement:
    def __init__(self, uid, bbox, attrib, text):
        self.uid = uid
        self.bbox = bbox
        self.attrib = attrib
        self.text = text


def get_id_from_element(elem):
    bounds = elem.attrib["bounds"][1:-1].split("][")
    x1, y1 = map(int, bounds[0].split(","))
    x2, y2 = map(int, bounds[1].split(","))
    elem_w, elem_h = x2 - x1, y2 - y1
    if "resources-id" in elem.attrib and elem.attrib["resources-id"]:
        elem_id = elem.attrib["resources-id"].replace(":", ".").replace("/", "_")
    else:
        elem_id = f"{elem.attrib['class']}_{elem_w}_{elem_h}"
    if "content-desc" in elem.attrib and elem.attrib["content-desc"] and len(elem.attrib["content-desc"]) < 20:
        content_desc = elem.attrib['content-desc'].replace("/", "_").replace(" ", "").replace(":", "_")
        elem_id += f"_{content_desc}"
    return elem_id


def traverse_tree(xml_path, elem_list, attrib, add_index=False):
    path = []
    for event, elem in ET.iterparse(xml_path, ['start', 'end']):
        if event == 'start':
            path.append(elem)
            if attrib in elem.attrib and elem.attrib[attrib] == "true":
                parent_prefix = ""
                if len(path) > 1:
                    parent_prefix = get_id_from_element(path[-2])
                bounds = elem.attrib["bounds"][1:-1].split("][")
                x1, y1 = map(int, bounds[0].split(","))
                x2, y2 = map(int, bounds[1].split(","))
                center = (x1 + x2) // 2, (y1 + y2) // 2
                elem_id = get_id_from_element(elem)
                if parent_prefix:
                    elem_id = parent_prefix + "_" + elem_id
                if add_index:
                    elem_id += f"_{elem.attrib['index']}"
                close = False
                for e in elem_list:
                    bbox = e.bbox
                    center_ = (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2
                    dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
                    if dist <= configs["MIN_DIST"]:
                        close = True
                        break
                if not close:
                    elem_list.append(UIElement(elem_id, [x1, y1, x2, y2], attrib, elem.attrib.get("text", "")))

        if event == 'end':
            path.pop()


def extract_xml(xml_path):
    if xml_path is None:
        return []
    clickable_list = []
    focusable_list = []
    traverse_tree(xml_path, clickable_list, "clickable", True)
    traverse_tree(xml_path, focusable_list, "focusable", True)
    el_list = clickable_list.copy()
    for elem in focusable_list:
        bbox = elem.bbox
        center = (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2
        close = False
        for e in clickable_list:
            bbox = e.bbox
            center_ = (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2
            dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
            if dist <= configs["MIN_DIST"]:
                close = True
                break
        if not close:
            el_list.append(elem)
    return el_list


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


def screenshot_labeled(uidi: UIDefectInjection, texts=None, extra=[], rgba=(0, 0, 255), thickness=3):
    screenshot = Image.open(uidi.image_path)
    if texts is None:
        texts = list(map(str, range(len(uidi.ui_positions))))
    font = ImageFont.truetype(configs['FONT_PATH'], size=configs['FONT_SIZE'], encoding="utf-8")
    with screenshot.convert('RGBA') as base:
        tmp = Image.new('RGBA', base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(tmp)
        for idx, ui_position in enumerate(uidi.ui_positions):
            x1, y1, x2, y2 = ui_position[:4]
            if x1 == x2 or y1 == y2:
                continue
            if [x1, y1, x2, y2] not in extra:
                draw.rectangle((x1, y1, x2, y2), outline=rgba, width=thickness)
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
