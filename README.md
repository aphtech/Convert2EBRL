# Convert2EBRL

A GUI application for converting files to EBRL.

## Status of EBRL support

As there is no published version of the EBRL standard, currently this tool is unable to produce files which are guaranteed to comply with the final EBRL specification. Once a EBRL specification is published this tool will then recieve updates to produce files to comply with that specification.

## Developer information

### Building

This package is managed with the pdm tool.

### IDE configuration

To get code completions and avoid warnings for PySide6 features of snake_case and true_property you may need to regenerate the stub files. Run the following command:
```commandline
pyside6-genpyi all --feature snake_case true_property
```