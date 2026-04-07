# Convert2EBRL

A GUI application for converting files to eBraille.

## Developer information

### Running from source code

From within the gui directory run the following command:
```commandline
uv run Convert2EBRL.pyw
```

### Building standalone executable

From within the gui directory run the following command to build a standalone executable:
```commandline
uv run python -m nuitka Convert2EBRL.pyw
```
This will create a directory Convert2EBRL.dist which contains all the binary files required for distribution.

### IDE configuration

To get code completions and avoid warnings for PySide6 features of snake_case and true_property you may need to regenerate the stub files. Run the following command:
```commandline
pyside6-genpyi all --feature snake_case true_property
```
