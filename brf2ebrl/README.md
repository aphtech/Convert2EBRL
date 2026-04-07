# brf2ebrl

Library for converting BRF to eBraille.

## Status of eBraille support

As there is no published version of the eBraille standard, currently this tool is
unable to produce files which are guaranteed to comply with the final eBraille
specification. Once a eBraille specification is published this tool will then
receive updates to produce files to comply with that specification.

## Building and running

To run test, from within the brf2ebrl directory run the following command:
```command line
uv run pytest
```
There is a basic command line script for demonstration purposes. To run the brf2ebrl script, use the following command:
```command line
uv run --all-packages brf2ebrl -o <output_file> <brf>
```
For details of using the brf2ebrl command, do the following:
```command line
uv run --all-packages brf2ebrl --help
```
