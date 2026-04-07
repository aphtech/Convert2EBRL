# Convert2EBRL

A set of tools for converting documents to eBraille. This repository contains a number of subpprojects:

* gui: A graphical tool for converting BRF documents into eBraille.
* brf2ebrl: The parser library for converting documents.
* plugins: Subprojects within this directory are parser plugins for specific Braille codes.

## Development status

This project is currently being actively developed. Only git tags starting with `release/` are deemed to be end user ready. All other forms of the code are deemed to be development code and so is not recommended for any use other than testing.

## Developer information

### Building

To build and run this project you will need to install UV. The UV web site is https://docs.astral.sh/uv/ and contains details of the various install methods. See the README files within the subprojects for build/useage details for that specific subproject.

### IDE configuration

To get code completions and avoid warnings for PySide6 features of snake_case and true_property you may need to regenerate the stub files. Run the following command:
```commandline
pyside6-genpyi all --feature snake_case true_property
```

## Contributing

If you would like to contribute code to the project, please create an issue on GitHub first explaining what you would like to change and why. This will give an opportunity for your idea to be discussed, for us to get a feeling of how much demand there is for what you propose and to be able to give feedback on how it may be done. Having these discussions prior to pull requests being submitted is likely to increase the chance your contribution will be accepted.