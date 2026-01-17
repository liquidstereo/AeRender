# AeRender

A simple python cli for automating **Adobe After Effects** rendering process with multicore acceleration.

> 💡 Especially effective for older versions of After Effects that do not support native multiprocessing.

> ⚠️ **Important:** Always save your `.aep` file before running the script.

---

## Update (v2.0)

- **Multi-Composition Rendering**: Render multiple compositions in a single command
- **Auto Worker Detection**: Automatically calculates optimal worker count based on system resources
- **Preview Results**: Preview rendered results even in multi-composition rendering (`-p` flag)
  - `SPACE` pause | `←/→` prev/next | `↑/↓` first/last | `+/-` zoom | `PgUp/PgDn` switch comp | `ESC` exit

---

## Requirements

- [Python 3.10+](https://www.python.org/downloads/)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- Adobe After Effects (aerender.exe in PATH)

> ⚠️ This script currently supports only **image sequence rendering** on **Windows**.

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

### Running the Script

```bash
python AeRender.py -f <project.aep> -c <CompName> -s <start> -e <end>
```

**Example:**
```bash
# Single Composition
python AeRender.py -f "project.aep" -c "MainComp" -s 0 -e 100

# Multiple Compositions (Comp1: 0-100, Comp2: 10-110, Comp3: 20-120)
python AeRender.py -f "project.aep" -c "Comp1,Comp2,Comp3" -s 0 10 20 -e 100 110 120

# With Preview
python AeRender.py -f "project.aep" -c "MainComp" -s 0 -e 100 -p

# With Logging
python AeRender.py -f "project.aep" -c "MainComp" -s 0 -e 100 -l

# Specify Workers
python AeRender.py -f "project.aep" -c "MainComp" -s 0 -e 100 -w 4

# Full Options (use your own Output Module template name)
python AeRender.py -f "project.aep" -c "MainComp" -s 0 -e 100 -omt "Your_Template_Name" -x png -w 4 -p -l
```

> 📌 For multiple compositions, provide comma-separated comp names and space-separated frame ranges.

For more information on automated rendering, see the [Adobe After Effects User Guide](https://helpx.adobe.com/after-effects/using/automated-rendering-network-rendering.html).

### Command-Line Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `-f` | After Effects project file (.aep) | Yes | - |
| `-c` | Composition name (single or comma/space-separated) | Yes | - |
| `-s` | Start frame (single or space-separated list) | Yes | - |
| `-e` | End frame (single or space-separated list) | Yes | - |
| `-o` | Output directory | No | results/COMP_NAME |
| `-omt` | Output module template | No | YOUR_TEMPLATE |
| `-rst` | Render settings template | No | Best Settings |
| `-x` | Output file extension | No | png |
| `-w` | Number of workers (0 = auto) | No | 0 |
| `-t` | Frames per task (0 = auto) | No | 0 |
| `-v` | After Effects verbose flag | No | ERRORS_AND_PROGRESS |
| `-p` | Enable preview mode | No | False |
| `-l` | Enable logging | No | False |
| `-json` | Save render config as JSON | No | False |

> 📌 Preview feature supports: **PNG, JPG, JPEG, BMP, TIFF**

> ⚠️ **Important:** You must set `-omt` to your own Output Module template name from After Effects.
> Check your templates in After Effects: `Edit > Templates > Output Module`

### Default Configuration

You can customize default values directly in **`configs/defaults.py`** to avoid typing arguments repeatedly.

```python
# configs/defaults.py
DEFAULT_RS_TEMPLATE = 'Best Settings'
DEFAULT_OM_TEMPLATE = 'YOUR_TEMPLATE'  # Set your After Effects Output Module template name
DEFAULT_FILE_EXTENSION = 'png'
DEFAULT_SYSTEM_USAGE = 0.70
# ... and more
```

> ⚠️ **Recommended:** For stable rendering, keep `DEFAULT_SYSTEM_USAGE = 0.70` (70% of system resources).

---

## License

This project is licensed under the MIT License.
