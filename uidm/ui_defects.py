import os
import random
import uuid
from dataclasses import dataclass
from typing import Tuple, List
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

import config

configs = config.load_config()


def identify_el_size(img_size, bbox):
    """
    Identify the size of the element based on the image size and bounding box.
    if the element is smaller than 40% of the screen width or 10% of the screen height, it is considered small.
    if the element is larger than 90% of the screen width or 25% of the screen height, it is considered large.
    Otherwise, it is considered medium.
    :param img_size:
    :param bbox:
    :return:
    """
    x1, y1, x2, y2 = bbox
    w, h = img_size
    el_width, el_height = x2 - x1, y2 - y1
    if el_width < int(w * 0.4) or el_height < int(h * 0.1):
        return "SMALL"
    elif el_width > int(w * 0.9) or el_height > int(h * 0.25):
        return "LARGE"
    return "MEDIUM"


def get_dominant_color(cropped_img):
    """
    Get the dominant color of the cropped image.
    :param cropped_img:
    :return:
    """
    if cropped_img.mode != 'RGB':
        cropped_img = cropped_img.convert('RGB')

    pixels = list(cropped_img.getdata())
    color_counts = Counter(pixels)

    dominant_color = color_counts.most_common(1)[0][0]
    return dominant_color


def identify_aligned_groups(ui_positions: List[Tuple[float, float, float, float]], tolerance: float = 5):
    """
    Optimized identification of aligned groups (horizontal, vertical, and center alignment).
    :param ui_positions: List of bounding boxes [(x1, y1, x2, y2)]
    :param tolerance: Alignment tolerance (default: 5 pixels)
    :return: A dictionary with aligned groups and mapping to original indices
    """
    indexed_positions = [(i, pos) for i, pos in enumerate(ui_positions)]
    sorted_positions_with_index = sorted(indexed_positions, key=lambda x: (x[1][0], x[1][1]))
    sorted_positions = [pos for _, pos in sorted_positions_with_index]
    original_indices = [i for i, _ in sorted_positions_with_index]

    centers = [(i, ((x1 + x2) // 2, (y1 + y2) // 2)) for i, (x1, y1, x2, y2) in enumerate(sorted_positions)]

    def detect_alignment(criteria_func, positions):
        """Generalized alignment detection based on a criteria function."""
        groups = []
        visited = set()
        for i, pos1 in enumerate(positions):
            if i in visited:
                continue
            group = [i]
            for j, pos2 in enumerate(positions[i + 1:], start=i + 1):
                if j not in visited and criteria_func(pos1, pos2):
                    group.append(j)
            if len(group) > 1:
                groups.append(group)
                visited.update(group)
        return groups

    # Define criteria for different alignments
    def horizontal_criteria(pos1, pos2):
        return abs(pos1[1] - pos2[1]) <= tolerance

    def vertical_criteria(pos1, pos2):
        return abs(pos1[0] - pos2[0]) <= tolerance

    def center_criteria(center1, center2):
        return abs(center1[0] - center2[0]) <= tolerance

    horizontal_groups = detect_alignment(horizontal_criteria, sorted_positions)
    vertical_groups = detect_alignment(vertical_criteria, sorted_positions)
    center_groups = detect_alignment(center_criteria, [c[1] for c in centers])

    horizontal_groups_original = [[original_indices[i] for i in group] for group in horizontal_groups]
    vertical_groups_original = [[original_indices[i] for i in group] for group in vertical_groups]
    center_groups_original = [[original_indices[centers[i][0]] for i in group] for group in center_groups]

    return {
        "horizontal": horizontal_groups_original,
        "vertical": vertical_groups_original,
        "center_aligned": center_groups_original,
    }


@dataclass
class UIDefectInjection:
    image_path: str
    ui_positions: List[Tuple[float, float, float, float]]
    ui_texts: List[str]
    alignment_el: dict = None
    injected_defect: str = ""
    labeled_path: str = ""
    selected: int = 0

    def __post_init__(self):
        self.alignment_el = identify_aligned_groups(self.ui_positions)

    def __str__(self):
        return f"UIDefectInjection(image_path={self.image_path}, ui_positions={self.ui_positions}, " \
               f"ui_texts={self.ui_texts}, alignment_el={self.alignment_el}, injected_defect={self.injected_defect}, " \
               f"labeled_path={self.labeled_path}, selected={self.selected})"


def el_repeat_content(uidi: UIDefectInjection):
    """
    Repeat the selected element's text in the center of the element.
    :param uidi: UIDefectInjection
    :return:
    """
    screenshot = Image.open(uidi.image_path)
    x1, y1, x2, y2 = uidi.ui_positions[uidi.selected]
    center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
    x_offset, y_offset = (x2 - x1) // 6, (y2 - y1) // 6
    x_add = center_x + x_offset
    y_add = center_y + y_offset
    draw = ImageDraw.Draw(screenshot)
    font = ImageFont.truetype(configs["FONT_PATH"], int(y2 - y1))
    draw.text((x_add, y_add), uidi.ui_texts[uidi.selected], fill=(57, 57, 57), font=font)
    screenshot.save(uidi.image_path)


def el_replace_content(uidi: UIDefectInjection):
    """
    Replace the selected element with a random string from ['����', 'nullnull'].
    :param uidi: UIDefectInjection
    :return:
    """
    text = random.choice(configs["GARBLED_CONTENT"])
    screenshot = Image.open(uidi.image_path)
    x1, y1, x2, y2 = uidi.ui_positions[uidi.selected]
    el_width, el_height = x2 - x1, y2 - y1
    cropped = screenshot.crop((x1, y1, x2, y2))
    font = ImageFont.truetype(configs["FONT_PATH"], int(el_height))
    draw = ImageDraw.Draw(cropped)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_x = (el_width - (text_bbox[2] - text_bbox[0])) // 2
    text_y = (el_height - (text_bbox[3] - text_bbox[1])) // 2

    draw.rectangle((0, 0, el_width, el_height), fill=get_dominant_color(cropped))
    draw.text((text_x, text_y), text, fill=(57, 57, 57), font=font)
    screenshot.paste(cropped, (x1, y1))
    screenshot.save(uidi.image_path)


def el_missing_blank(uidi: UIDefectInjection):
    """
    Replace the selected element with a blank rectangle.
    :param uidi: UIDefectInjection
    :return:
    """
    screenshot = Image.open(uidi.image_path)
    x1, y1, x2, y2 = uidi.ui_positions[uidi.selected]
    cropped = screenshot.crop((x1, y1, x2, y2))
    tmp_dir = './tmp'
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    cropped.save(f"{tmp_dir}/{uuid.uuid4()}.png")
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((x1, y1, x2, y2), fill=get_dominant_color(cropped))
    screenshot.save(uidi.image_path)


def el_missing_broken_img(uidi: UIDefectInjection):
    """
    Randomly select a broken image and paste it on the selected element.
    :param uidi: UIDefectInjection
    :return:
    """
    el_missing_blank(uidi)
    broken_img_dir = os.path.join(configs["RESOURCE_DIR"], "broken_images")
    broken_imgs = [f for f in os.listdir(broken_img_dir) if f.endswith(('png', 'jpg', 'jpeg'))]
    if not broken_imgs:
        print(f"No broken images found in {configs['RESOURCE_DIR']}.")
        return
    broken_img_path = os.path.join(broken_img_dir, random.choice(broken_imgs))
    x1, y1, x2, y2 = uidi.ui_positions[uidi.selected]
    el_width, el_height = x2 - x1, y2 - y1
    broken_img = Image.open(broken_img_path)
    broken_img_w, broken_img_h = broken_img.size
    # Resize the broken image if it is larger than the element
    aspect_ratio = broken_img_w / broken_img_h
    if broken_img_w > el_width or broken_img_h > el_height:
        if broken_img_w / el_width > broken_img_h / el_height:
            new_width = el_width
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = el_height
            new_width = int(new_height * aspect_ratio)
        broken_img = broken_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        broken_img_w, broken_img_h = broken_img.size

    center_x, center_y = x1 + el_width // 2, y1 + el_height // 2
    new_x1 = max(0, center_x - broken_img_w // 2)
    new_y1 = max(0, center_y - broken_img_h // 2)
    uidi.ui_positions[uidi.selected] = (0, 0, 0, 0)
    screenshot = Image.open(uidi.image_path)
    screenshot.paste(broken_img, (new_x1, new_y1))
    screenshot.save(uidi.image_path)


def el_overlapping(uidi: UIDefectInjection):
    """
    Randomly select an element and overlap it with the selected element.
    The offset is set to a quarter of the element's width and height.
    :param uidi: UIDefectInjection
    :return:
    """
    x1, y1, x2, y2 = uidi.ui_positions[uidi.selected]
    screenshot = Image.open(uidi.image_path)
    draw = ImageDraw.Draw(screenshot)
    cropped = screenshot.crop((x1, y1, x2, y2))
    draw.rectangle((x1, y1, x2, y2), fill=get_dominant_color(cropped))
    el_size = identify_el_size(screenshot.size, (x1, y1, x2, y2))
    if el_size == "SMALL":
        x_add, y_add = (x2 - x1) * 1.5, (y2 - y1) * 1.5
    elif el_size == "MEDIUM":
        x_add, y_add = (x2 - x1) // 2, (y2 - y1) // 2
    else:
        x_add, y_add = (x2 - x1) // 4, (y2 - y1) // 4
    uidi.ui_positions[uidi.selected] = (x1 + x_add, y1 + y_add, x2 + x_add, y2 + y_add)
    screenshot.paste(cropped, (int(x1 + x_add), int(y1 + y_add)))
    screenshot.save(uidi.image_path)


def el_scaling(uidi: UIDefectInjection):
    """
    Randomly scale up or down the element.
    If the element is larger than half of the screen width or a quarter of the screen height, scale down.
    Otherwise, scale up.
    :param uidi: UIDefectInjection
    :return:
    """
    screenshot = Image.open(uidi.image_path)
    w, h = screenshot.size
    x1, y1, x2, y2 = uidi.ui_positions[uidi.selected]
    el_width, el_height = x2 - x1, y2 - y1
    scale_down = random.uniform(0.65, 0.85)
    scale_up_medium = random.uniform(1.15, 1.35)
    scale_up = random.uniform(1.35, 1.5)
    el_size = identify_el_size(screenshot.size, (x1, y1, x2, y2))
    if el_size == "LARGE":
        new_width, new_height = max(0, int(el_width * scale_down)), max(0, int(el_height * scale_down))
    elif el_size == "MEDIUM":
        new_width, new_height = int(el_width * scale_up_medium), int(el_height * scale_up_medium)
    else:
        new_width, new_height = int(el_width * scale_up), int(el_height * scale_up)
    cropped = screenshot.crop((x1, y1, x2, y2))
    resized = cropped.resize((new_width, new_height))
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((x1, y1, x2, y2), fill=get_dominant_color(cropped))
    center_x, center_y = x1 + el_width // 2, y1 + el_height // 2
    new_x1 = max(0, center_x - new_width // 2)
    new_y1 = max(0, center_y - new_height // 2)
    new_x2 = min(w, new_x1 + new_width)
    new_y2 = min(h, new_y1 + new_height)
    uidi.ui_positions[uidi.selected] = (new_x1, new_y1, new_x2, new_y2)
    resized_w, resized_h = new_x2 - new_x1, new_y2 - new_y1
    if resized_w != new_width or resized_h != new_height:
        resized = resized.resize((resized_w, resized_h))
    screenshot.paste(resized, (new_x1, new_y1))
    screenshot.save(uidi.image_path)


def el_misaligned(uidi: UIDefectInjection):
    """
    Check if there are continuously aligned elements on the page.
    If there are, randomly select one of them for misalignment.
    :param uidi: UIDefectInjection
    :return:
    """

    def calculate_average_size(group):
        """Calculate the average size of elements in a group."""
        total_area = sum((x2 - x1) * (y2 - y1) for idx in group for x1, y1, x2, y2 in [uidi.ui_positions[idx]])
        return total_area / len(group) if group else 0

    all_groups = [
                     ("horizontal", group) for group in uidi.alignment_el.get("horizontal", [])
                 ] + [
                     ("vertical", group) for group in uidi.alignment_el.get("vertical", [])
                 ] + [
                     ("center_aligned", group) for group in uidi.alignment_el.get("center_aligned", [])
                 ]
    if not all_groups:
        return
    longest_group_type, longest_group = max(all_groups, key=lambda x: (len(x[1]), calculate_average_size(x[1])))

    uidi.selected = random.choice(longest_group)
    x1, y1, x2, y2 = uidi.ui_positions[uidi.selected]
    screenshot = Image.open(uidi.image_path)
    w, h = screenshot.size
    cropped_img = screenshot.crop((x1, y1, x2, y2))
    cropped_img.save(f'./tmp/{uuid.uuid4()}.png')
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((x1, y1, x2, y2), fill=get_dominant_color(cropped_img))
    if longest_group_type == "horizontal":
        y_offset = random.randint(-10, -5)
        uidi.ui_positions[uidi.selected] = (x1, y1 + y_offset, x2, y2 + y_offset)
    else:
        x_offset = abs(int(w - x1 - x2)) if longest_group_type == "vertical" else x1 / 4
        uidi.ui_positions[uidi.selected] = (x1 + x_offset, y1, x2 + x_offset, y2)
    x1, y1, x2, y2 = uidi.ui_positions[uidi.selected]
    # FIXME
    screenshot.paste(cropped_img, (int(x1), int(y1)))
    screenshot.save(uidi.image_path)


def uneven_space(uidi: UIDefectInjection):
    """
    Cover the entire row of elements at the center of the screen with a blank rectangle.
    The rectangle spans the full screen width and has the height of the tallest element in the row.
    FIXME - use a rectangle(screenshot_width, screenshot / 10) scan the screen?
    :param uidi: UIDefectInjection
    :return:
    """
    vertical_groups = uidi.alignment_el.get("vertical", [])
    if not vertical_groups:
        return
    group_heights = [
        (group, max((uidi.ui_positions[idx][3] - uidi.ui_positions[idx][1]) for idx in group))
        for group in vertical_groups
    ]
    tallest_group, _ = max(group_heights, key=lambda x: x[1])
    screenshot = Image.open(uidi.image_path)
    w, h = screenshot.size
    max_height = 0
    row_els = []
    for idx in tallest_group:
        x1, y1, x2, y2 = uidi.ui_positions[idx]
        max_height = max(max_height, y2 - y1)
        uidi.ui_positions[idx] = (0, 0, 0, 0)
        row_els.append(idx)
    y1 = min(uidi.ui_positions[idx][1] for idx in row_els)
    uidi.ui_positions[row_els[0]] = (0, y1, w, y1 + max_height)
    uidi.selected = row_els[0]
    el_missing_blank(uidi)


strategies = {
    "CONTENT_ERROR": el_replace_content,
    "CONTENT_REPEAT": el_repeat_content,
    "EL_OVERLAPPING": el_overlapping,
    "EL_SCALING": el_scaling,
    "EL_MISSING_BLANK": el_missing_blank,
    "EL_MISSING_BROKEN_IMG": el_missing_broken_img,
    "EL_MISALIGNED": el_misaligned,
    "UNEVEN_SPACE": uneven_space
}
