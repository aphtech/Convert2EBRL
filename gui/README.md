# Convert2EBRL

A GUI application for converting files to eBraille.

## Status of eBraille support

As there is no published version of the eBraille standard, currently this tool is unable to produce files which are guaranteed to comply with the final eBraille specification. Once a eBraille specification is published this tool will then recieve updates to produce files to comply with that specification.

## Development status

This project is currently being actively developed. Only git tags starting with `release/` are deemed to be end user ready. All other forms of the code are deemed to be development code and so is not recommended for any use other than testing.

## Developer information

### Building

This package is managed with the pdm tool which you will need to install. The PDM web site is https://pdm.fming.dev and contains details of the various install methods.

### IDE configuration

To get code completions and avoid warnings for PySide6 features of snake_case and true_property you may need to regenerate the stub files. Run the following command:
```commandline
pyside6-genpyi all --feature snake_case true_property
```

### Building binary executable

You can build a binary distribution of Convert2EBRL with the following command:
```commandline
pdm build_exe
```
This will create a subdirectory named Convert2EBRL.dist which contains the executable distribution.

## Contributing

If you would like to contribute code to the project, please create an issue on GitHub first explaining what you would like to change and why. This will give an opportunity for your idea to be discussed, for us to get a feeling of how much demand there is for what you propose and to be able to give feedback on how it may be done. Having these discussions prior to pull requests being submitted is likely to increase the chance your contribution will be accepted.