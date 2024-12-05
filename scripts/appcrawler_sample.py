import glob
import json
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from lxml import etree

from config import load_config
from uidm.utils import extract_xml

configs = load_config()


def find_action_bbox(xml_file, xpath):
    if xml_file == '':
        return ""
    try:
        node = etree.parse(xml_file).xpath(xpath)
        if node:
            bounds = node[0].get('bounds')[1:-1].split("][")
            x1, y1 = map(int, bounds[0].split(","))
            x2, y2 = map(int, bounds[1].split(","))
            return [x1, y1, x2, y2]
    except etree.XPathEvalError as e:
        print(f"UNUSABLE: {xpath}")
    except Exception as e:
        print(f"XPATH ERROR: {e}")
    return ""


def get_subdirectories(directory):
    subdirectories = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
    return subdirectories


def fileter_appinfo(json_path, package_name, saved_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    selected_app = [app for app in data if app['app_id'] == package_name]
    if not os.path.exists(saved_path):
        os.makedirs(saved_path)
    with open(f'{saved_path}/{package_name}.json', 'w') as f:
        json.dump(selected_app, f, indent=4, ensure_ascii=False)


def extract_testcases_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    cnt = 0
    json_data = []
    for testcase in root.findall('testcase'):
        cnt += 1
        name = testcase.get('name')
        name_split = name.split(' ')
        clickedIndex, action, xpath = name_split[0], name_split[1], " ".join(name_split[2:])
        data = {
            'classname': testcase.get('classname'),
            'clickedIndex': clickedIndex.split('=')[-1],
            'action': action.split('=')[-1].replace("CLICKED", "CLICK"),
            'xpath': xpath.replace('xpath=', '')
        }
        json_data.append(data)
    if cnt > 1:
        return json_data
    return None


def pre_processing(input_dir, package_name):
    testcases_match = f'TEST-{package_name}'
    xml_files = glob.glob(f'{input_dir}/*.xml', recursive=True)
    filtered_xml = [xml for xml in xml_files if testcases_match in xml]
    fileter_appinfo('./Google_Play_Top_200.json', package_name, f"{configs['SAVED_DIR']}/{package_name}")
    for xml_file in filtered_xml:
        testcases = extract_testcases_xml(xml_file)
        if testcases is None:
            continue
        classname = testcases[0]['classname']
        saved_dir = f"{configs['SAVED_DIR']}/{classname.split('.')[-1]}"
        if not os.path.exists(saved_dir):
            os.makedirs(saved_dir)
        imgs = glob.glob(f'{input_dir}/*.png', recursive=True)
        for testcase in testcases:
            testcase['imgs_path'] = []
            clickedIndex = int(testcase['clickedIndex'])
            f_imgs = [img for img in imgs if os.path.basename(img).split('_')[0] == str(clickedIndex)]
            if len(f_imgs) < 2:
                continue
            fir_img, sec_img = f_imgs[0], f_imgs[1]
            if 'clicked' in fir_img:
                fir_img, sec_img = sec_img, fir_img
            shutil.copy(fir_img, f'{saved_dir}/{clickedIndex}_0.png')
            testcase['imgs_path'].append(f'{saved_dir}/{clickedIndex}_0.png')
            shutil.copy(sec_img, f'{saved_dir}/{clickedIndex}_1.png')
            testcase['imgs_path'].append(f'{saved_dir}/{clickedIndex}_1.png')
            sec_xml = [xml for xml in xml_files if os.path.basename(xml).split('_')[0] == str(clickedIndex)][0]
            fir_xml = ''
            if clickedIndex - 1 >= 0 and clickedIndex - 1 != 1:
                fir_xml = [xml for xml in xml_files if os.path.basename(xml).split('_')[0] == str(clickedIndex - 1)]
                if fir_xml:
                    fir_xml = fir_xml[0]
                    shutil.copy(fir_xml, f'{saved_dir}/{clickedIndex}_0.xml')
            shutil.copy(sec_xml, f'{saved_dir}/{clickedIndex}_1.xml')
            testcase['action_bbox'] = str(find_action_bbox(fir_xml, testcase['xpath']))
            el_list_before = extract_xml(fir_xml)
            el_list_after = extract_xml(sec_xml)
            testcase['ui_positions'] = [str([el.bbox for el in el_list_before]), str([el.bbox for el in el_list_after])]
            testcase['ui_text'] = [str([el.text for el in el_list_before]), str([el.text for el in el_list_after])]

        with open(f'{saved_dir}/{classname}.json', 'w') as f:
            json.dump(testcases, f, indent=4, ensure_ascii=False)


def extract_appcrawler_data(input_dir, package_name):
    """
    TODO - Extract AppCrawler Data
    :param input_dir:
    :param package_name:
    :return:
    """
    pass


if __name__ == '__main__':
    root_dir = sys.argv[1]
    subdirectories = get_subdirectories(root_dir)
    for subdir in subdirectories:
        package_name = '_'.join(subdir.split('_')[1:])
        configs['INPUT_DIR'] = f'../{root_dir}/{subdir}'
        configs['SAVED_DIR'] = f'../original_cs_data/{package_name}'
        input_dir = configs['INPUT_DIR']
        pre_processing(input_dir, package_name)
        print("Pre Processing Successfully for ", subdir)
        extract_appcrawler_data(input_dir, package_name)
        print("Extract AppCrawler Data Successfully for ", subdir)
