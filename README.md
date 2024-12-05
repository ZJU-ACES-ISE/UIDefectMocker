# 🎨UI Defect Mocker

## 📍Overview
UIDefectMocker is designed to inject various UI **display** defects into mobile screenshot to simulate real-world UI issues.

![sample.png](resources/sample.png)

## 🧩Defect Injection Strategies
- **CONTENT_ERROR**: Repeats content within an element.
- **CONTENT_REPEAT**: Replaces content within an element.
- **EL_OVERLAPPING**: Overlaps one element with another.
- **EL_SCALING**: Scales an element up or down.
- **EL_MISSING_BLANK**: Replaces an element with a blank space.
- **EL_MISSING_BROKEN_IMG**: Replaces an element with a broken image.
- **EL_MISALIGNED**: Misaligns elements on the page.
- **UNEVEN_SPACE**: Covers a row of elements with a blank space in the center.

## 🛠Installation
1. Clone the repository:
    ```sh
    git clone https://github.com/sesuii/uidefectmocker.git
    ```
2. Navigate to the project directory:
    ```sh
    cd UIDefectMocker
    ```
3. Initialize Poetry in the project:
    ```sh
    poetry init
    ```
4. Install the required dependencies:
    ```sh
    poetry install
    ```

## 🚀Usage
1. Configure the `config.yaml` file with your desired settings.
2. Place your screenshots in the directory specified by `INPUT_DIR` in the `config.yaml` file.
3. Run the main script to inject defects:
    ```sh
    poetry run python uidm_main.py
    ```

## ⚙️Configuration

Here is an example configuration `config.yaml`:

```yaml
INPUT_DIR: "/screenshots"
SAVED_DIR: "/saved"
ANDROID_XML_DIR: "/xml"
STRATEGY: ["CONTENT_ERROR", "CONTENT_REPEAT", "EL_OVERLAPPING", "EL_SCALING", "EL_MISSING_BLANK", "EL_MISSING_BROKEN_IMG", "EL_MISALIGNED", "UNEVEN_SPACE"]
OUTPUT_WITH_LABELED: True
PATTERN: "SCREENSHOT_WITH_XML"
RESOURCE_DIR: "/resources"
FONT_PATH: "/resources/Roboto-Regular.ttf"
GARBLED_CONTENT: ['����', 'nullnull']
DARK_MODE: false
MIN_DIST: 30
```

## 📝TODO
- [ ] According to the screenshot size, automatically adjust the `screen_labeled` related parameters (`font_size`, `thickness`).
- [ ] Strategy: `UNEVEN_SPACE` use a rectangle(screenshot_width, screenshot / 10) scan the screen?