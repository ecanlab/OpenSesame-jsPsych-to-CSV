# convert2csv.py

Convert JSON-formatted experimental data from OpenSesame (OSweb) or jsPsych into structured CSV format for analysis.

## Usage
```bash
python convert2csv.py <input_file> [output_file] [variables...] [options]
```

## Command-Line Arguments
|Argument |	Description|
|---|---|
|<input_file> |	Path to input data file |
|[output_file] |	Output CSV path (default: output.csv) |
|[variables...] |	Specific variables to extract (optional) |

## Options
|Flag |	Description|
|---|---|
|-a, --all | Extract all available variables |
|-p, --print | Print all variable names without writing CSV |
|-f, --force | Allow overwriting input file if it equals output |

## Examples

Extract all variables:
```bash
python convert2csv.py data.json results.csv --all
```

Extract specific variables only:
```bash
python convert2csv.py data.json results.csv trial_type rt accuracy
```

Preview available variable names:
```bash
python convert2csv.py data.json --print
```
