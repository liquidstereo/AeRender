# AeRender

A Python script for multicore-accelerated rendering of Adobe After Effects projects via the command line.

> **Important:** This script currently supports only image sequence rendering on Windows.

---

## Requirements

- [Python 3.10+](https://www.python.org/downloads/)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

---

## Usage

### Installation

1.  **Add `aerender.exe` to Windows PATH**

    Ensure the path to your Adobe After Effects installation directory (e.g., `C:\Program Files\Adobe\Adobe After Effects VERSION\Support Files`) containing `aerender.exe` is added to your Windows system's PATH environment variable. This allows the script to call `aerender` from any directory.

    *You can find many tutorials online by searching for "how to add to the PATH environment variable in Windows".*

2.  **Clone the Repository**
    ```bash
    git clone https://github.com/liquidstereo/AeRender && cd AeRender
    ```

3.  **Create and Activate Conda Environment**
    ```bash
    conda create -n AeRender python=3.10 -y && conda activate AeRender
    ```

4.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

---

### Running the Script

**Basic usage:**

```bash
python AeRender.py -f "AEP_FILE_PATH" -c "COMP_NAME" \
-rst "RENDER_SETTINGS_TEMPLATE" -omt "OUTPUT_MODULE_TEMPLATE" \
-x "FILE_EXTENSION" -s START_FRAME -e END_FRAME \
-o "OUTPUT_DIR" -p [optional]
```

**Example Command:**

```bash
python AeRender.py -f "D:/your_proj/your_aep.aep" -c "your_Comp" -omt "Your_PNG_Output_Preset" -x "png" -s 0 -e 100 -o "D:/your_proj/your_Comp_result" -p
```

> **Note:** Always save your After Effects project file before running the script.

For more details on the underlying `aerender` tool, refer to the [Adobe Help Guide](https://helpx.adobe.com/uk/after-effects/using/automated-rendering-network-rendering.html).

### Command-Line Arguments

| Argument | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `--fpath` | `-f` | **(Required)** Path to the After Effects project file. | |
| `--comp_name` | `-c` | **(Required)** Name of the composition to render. | |
| `--output_dir` | `-o` | **(Required)** Path to the output directory. | |
| `--start` | `-s` | **(Required)** The first frame to render. | |
| `--end` | `-e` | **(Required)** The last frame to render. | |
| `--rs_template` | `-rst` | Render Settings template. | `"Multi-Machine Settings"` |
| `--om_template` | `-omt` | Output Module template. **(This should be the name of your specified Output Module preset in After Effects.)** | `"Multi-Machine Sequence"` |
| `--ext`| `-x` | File extension for the output sequence. **(This should match the file extension specified in your Output Module preset.)** | `"png"` |
| `--workers` | `-w` | Number of worker processes to use. | `0` (Auto-detect based on CPU/RAM) |
| `--per_task` | `-t` | Number of frames each worker renders at a time. | `0` (Auto-calculated based on workers) |
| `--verbose` | `-v` | Sets the logging level for `aerender.exe`. | `"ERRORS_AND_PROGRESS"` |
| `--preview` | `-p` | If present, enables a preview window after rendering.<br>**Note: This feature only supports `.png`, `.jpg`, `.jpeg`, `.bmp` and `.tiff` files.** | `False` |

---

## License

This project is licensed under the MIT License.