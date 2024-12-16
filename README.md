# AeRender.py

A Python script that enables multicore-accelerated rendering of Adobe After Effects projects in a command-line environment.
<br>_**This script currently only supports rendering to image sequence formats on Windows systems.**_</br>


## Requirements:

+ [Python 3.10+](https://www.python.org/downloads/)
+ [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

## Usage
### Installation
1. To run this script, you need to add the path to your Adobe After Effects installation directory<br>
*(eg. 'C:\Program Files\Adobe\Adobe After Effects VERSION\Support Files')</i>*
 or the path to ```aerender.exe``` to the Windows System environment PATH variable.
<br>To modify the Windows PATH environment variable, please refer to [this page](https://learn.microsoft.com/en-us/previous-versions/office/developer/sharepoint-2010/ee537574(v=office.14)#to-add-a-path-to-the-path-environment-variable).</br>

1. Download or clone the repository:
    ```bash
    git clone https://github.com/liquidstereo/AeRender
    cd AeRender
    ```

2. Create a new conda environment with python version.
    ```
    conda create -n AeRender python=3.10 -y
    conda activate AeRender
    ```
3. Dependencies can be installed by running the following command in your terminal:
    ```
    pip install -r requirements.txt
    ```

### Running the code
1. You can run this script simply by:

    ```
    python AeRender.py -f "AEP_FILE_PATH" -c "COMP_NAME" -rst "RENDER_SETTINGS_TEMPLATE" -omt "OUTPUT_MODULE_TEMPLATE" -x "FILE_EXTENSTION" -s START FRAME -e END FRAME -o "OUTPUT_DIR"
    ```
2.  Examples of script execution:

    ```
    python AeRender.py -f "D:/my_proj/my_aep.aep" -c "my_Comp" -rst "Multi-Machine Settings" -omt "my_PNG_Setting" -x "PNG"  -s 0 -e 100 -o "D:/my_proj/my_Comp_result"
    ```
3. Command line arguments:

    ```
    Usage: python AeRender.py [Arguments]

        -f,   --fpath             After Effects file path
        -c,   --comp_name         Comp Name
        -rst, --rs_template       Render Settings Template
        -omt, --om_template       Output Module Template
        -x,   --file_extension    Output File Extension (default: PNG)
        -v,   --verbose_flag      Verbose Flag (default: ERRORS)
        -s,   --start_frame       Start Frame Number
        -e,   --end_frame         End Frame Number
        -t,   --per_task          Number of parallel tasks (default: 10)
        -o,   --output_dir        Output directory path
        -w,   --workers           Maximum CPU core count for parallel tasks (default: MAX-2)


    ```
+ **Be sure to save your After Effects project file before running the script.**
+ For more information, please refer to [Adobe Help](https://helpx.adobe.com/uk/after-effects/using/automated-rendering-network-rendering.html)

## License
+ This project is licensed under the MIT License.