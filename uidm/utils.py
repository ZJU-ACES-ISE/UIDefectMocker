import os
import shutil
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

from config import load_config
from uidm.ui_defects import UIDefectInjection

configs = load_config()


class UIElement:
    def __init__(self, uid, bbox, attrib, text, el_type=""):
        self.uid = uid
        self.bbox = bbox
        self.attrib = attrib
        self.text = text
        self.type = el_type


def get_id_from_element(elem):
    bounds = elem.attrib["bounds"][1:-1].split("][")
    x1, y1 = map(int, bounds[0].split(","))
    x2, y2 = map(int, bounds[1].split(","))
    elem_w, elem_h = x2 - x1, y2 - y1
    if "resource-id" in elem.attrib and elem.attrib["resource-id"]:
        elem_id = elem.attrib["resource-id"].replace(":", ".").replace("/", "_")
    elif "class" in elem.attrib:
        elem_id = f"{elem.attrib['class']}_{elem_w}_{elem_h}"
    else:
        elem_id = f"Unknown_{elem_w}_{elem_h}"
    if "content-desc" in elem.attrib and elem.attrib["content-desc"] and len(elem.attrib["content-desc"]) < 20:
        content_desc = elem.attrib['content-desc'].replace("/", "_").replace(" ", "").replace(":", "_")
        elem_id += f"_{content_desc}"
    return elem_id


def traverse_tree(xml_path, elem_list, attrib, add_index=False):
    path = []
    try:
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
    except ET.ParseError as e:
        print(f"Error parsing XML file {xml_path}: {e}")


def extract_xml(xml_path):
    if not xml_path or not os.path.exists(xml_path):
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
    return el_list if el_list else []


def copy_walk_dir(source_folder, destination_folder):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder, exist_ok=True)
    for root, dirs, files in os.walk(source_folder):
        relative_path = os.path.relpath(root, source_folder)
        target_path = os.path.join(destination_folder, relative_path)
        os.makedirs(target_path, exist_ok=True)
        for file in files:
            # if file.endswith(".xml"):
            #     continue
            source_file_path = os.path.join(root, file)
            destination_file_path = os.path.join(target_path, file)
            shutil.copy(source_file_path, destination_file_path)
            print(f"Copied: {source_file_path} to {destination_file_path}")


def classify_ui_element(elem):
    """ Classifies UI elements based on XML attributes like class, text, content-desc, and resource-id. """
    class_name = elem.attrib.get("class", "").lower()
    text_content = elem.attrib.get("text", "").lower()
    content_desc = elem.attrib.get("content-desc", "").lower()
    resource_id = elem.attrib.get("resource-id", "").lower()
    bounds = elem.attrib.get("bounds", "[0,0][0,0]")

    # Extract width & height for size-based classification
    try:
        bounds = bounds[1:-1].split("][")
        x1, y1 = map(int, bounds[0].split(","))
        x2, y2 = map(int, bounds[1].split(","))
        width, height = x2 - x1, y2 - y1
    except:
        width, height = 100, 100  # Default size if parsing fails

    element_text = f"{text_content} {content_desc} {resource_id}"

    if any(w in class_name for w in ["button", "imagebutton", "radiobutton"]) or \
            any(w in element_text for w in
                ["submit", "confirm", "option", "send", "login", "register", "next", "search", "start"]):
        return "Button"

    if any(w in class_name for w in ["edittext", "textfield", "input"]) or \
            "enter" in element_text or "input" in element_text:
        return "InputField"

    if "textview" in class_name or "label" in class_name or "statictext" in class_name:
        return "Text"

    # ===== 图片（ImageView）=====
    if "imageview" in class_name:
        if any(w in element_text for w in ["banner", "photo", "picture", "background", "cover"]):
            return "Image"
        if width > 100 and height > 100:
            return "Image"

    # ===== 图标（Icon）=====
    if "imageview" in class_name or ("view" in class_name and width < 100 and height < 100):
        if any(w in element_text for w in ["icon", "logo", "symbol", "favicon", "indicator"]) or width < 100:
            return "Icon"

    # ===== 对话框（Dialog）=====
    if "dialog" in class_name or "popup" in element_text:
        return "Dialog"

    # ===== 复选框（CheckBox）=====
    if "checkbox" in class_name or "check" in element_text or "select" in element_text:
        return "CheckBox"

    # ===== 开关（Switch / Toggle）=====
    if "switch" in class_name or "toggle" in class_name or "on/off" in element_text:
        return "Switch"

    # ===== 列表（ListView / RecyclerView）=====
    if any(w in class_name for w in ["recyclerview", "listview", "scrollview", "gridview"]):
        return "List"

    # ===== 菜单项（Menu Item / Navigation）=====
    if "menu" in class_name or "navigation" in element_text:
        return "Menu"

    return ""


def screenshot_labeled(uidi: UIDefectInjection, texts=None, extra=[], rgba=(0, 0, 255), thickness=3):
    screenshot = Image.open(uidi.image_path)
    if texts is None:
        texts = list(map(str, range(len(uidi.ui_positions))))
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
    font = ImageFont.truetype(configs['FONT_PATH'], size=font_size, encoding="utf-8")
    with screenshot.convert('RGBA') as base:
        tmp = Image.new('RGBA', base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(tmp)
        for idx, ui_position in enumerate(uidi.ui_positions):
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
