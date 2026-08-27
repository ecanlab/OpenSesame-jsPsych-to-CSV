"""Structure OpenSesame and jsPsych data into CSV format."""

import argparse
import sys
import io
import json
import csv
from typing import Any

def get_args() -> argparse.Namespace:
  """Parses the command‑line arguments.

  Returns:
    Command-line arguments inputs as an argparse.Namespace object.
  """
  parser = argparse.ArgumentParser(
    prog='jsonToCsv',
    description='Convert jsPsych and OSweb data to CSV format'
  )
  parser.add_argument('file', help='the input file')
  parser.add_argument(
    'output', nargs='?', default='output.csv', help='the output file'
  )
  parser.add_argument(
    'variables',
    nargs='*',
    help='one or more variables to extract from the input file'
  )
  parser.add_argument(
    '-a',
    '--all',
    action='store_true',
    help='extract all variables from the data'
  )
  parser.add_argument(
    '-p',
    '--print',
    action='store_true',
    help='print all variables from the input file'
  )
  parser.add_argument(
    '-f',
    '--force',
    action='store_true',
    help='force overwrite'
  )
  args = parser.parse_args()

  if args.file == args.output and not args.force:
    sys.exit(
      f"Error: input and output refer to the same file ({args.file}). "
      "Use --force to allow overwriting."
    )
  return args

def read_file(file: str) -> list[dict | list]:
  """Read input file.

  Args:
    file (str): Path to a file that contains one participant per row.

  PRE:
    `file` must comform to either Opensesame or jsPsych data structure.

  Returns:
    Raw text with one participant per row
  """
  try:
    with io.open(file, "r", encoding="UTF-8") as f:
      text = f.readlines()

  except OSError as error:
    print("OS error:", error)
    sys.exit(1)

  except Exception as error:
    print(f"Unexpected error: {error=}, {type(error)=}")
    raise

  return text

def parse_json(text: list) -> list[dict]:
  """Parse the JSON data

  Input:
    text (list): Raw text with one participant on each row.

  Pre:
    `text` need to follow either Opensesame or jsPsych data structure.

  Returns:
    A list of dictionaries, each containing the parsed data for one
    participant.
  """
  acc = []
  for line in text:
    try:
      parsed = json.loads(line)
      acc.append(parsed)

    except json.JSONDecodeError as error:
      # Print the context around the error
      print(
        f"JSON decode error: {error.msg} at line {error.lineno} column "
        "{error.colno} (char {error.pos})"
      )
      try:
        fixed_content = repair_json_data(line)
        parsed = json.loads(fixed_content)
        print("Error was fixed for participant")

      except json.JSONDecodeError as nerror:
        print(f"Could not fix corrupt data: {nerror}")

    except Exception as error:
      print(f"Unexpected error during JSON parsing: {error=}, {type(error)=}")
      raise

    return acc

def repair_json_data(incomplete_json: str) -> str:
  """Fix corrupt JSON data by adding missing brackets and data wrapper.

  Args:
    incomplete_json (str): JSON string missing closing brackets and data
    wrapper.

  Pre:
    `incomplete_json` must be an OpenSesame‑style JSON fragment that ends
    abruptly (typically missing the final `]` and the outer
    `{"data": …, "context": …}` wrapper).

  Returns:
    Properly structured JSON string with data wrapper.
  """
  incomplete_json = incomplete_json[:-2] + "]"
  return '{"data":' + incomplete_json + ',"context":{"browser":{}}}'

def get_all_keys(
      data: list[dict | list],
      args: argparse.Namespace
    ) -> dict[str, Any]:
  """Extract all keys from the input file or the user-provided list of
    variables.

  Args:
    data (list[dict | list]): A list with a participants on each row, either as
      a dict or as a list.
    args (argparse.Namespace): User terminal inputs.

  Pre:
    `data` need to follow either Opensesame or jsPsych data structure.

  Return:
    dict[str, Any]: Dictornary with variables as keys and an empty value.
      If `args.all` is true, the function gathers every unique key from the
      participants’ data; otherwise it returns only the keys specified in
      `args.variables`.
  """
  keys = {}

  if args.all | args.print:
    for participant in data:
      # Opensesame structure
      if isinstance(participant, dict):
        for key in participant['context'].keys():
          keys[key] = ''
          for trial in participant['data']:
            for key in trial.keys():
              keys[key] = ''

      # JsPsych structure
      if isinstance(participant, list):
        for trial in participant:
          for key in trial.keys():
            keys[key] = ''
  else:
    keys = {k: "" for k in args.variables}

  return keys

def write_to_csv(data: list[dict|list], output_file: str, keys: dict[str, Any]):
  """ Writ all the keys to the first row of a CSV file and then add the
    corresponding values for each participant's trials on subsequent row.

  Args:
    data (list[dict | list]): A list with a participants on each row, either as
      a dict or as a list.

    outputFile (str): Path to the CSV file that will be created/overwritten.

    keys (dict[str, Any]): Dictornary with variables as keys and an empty value.

  Pre: `data` need to follow either Opensesame or jsPsych data structure.
         The directory containing `outputFile` must be writable.

  Returns: None
  """
  try:
    with open(output_file, "w", newline="", encoding="UTF-8") as csvfile:

      writer = csv.writer(csvfile)
      writer.writerow(list(keys.keys()))

      # Opensesame structure
      # Need to retrieve all context variables from every participant.
      # Otherwise, if the first participant lacks the context, none of the
      # subsequent participants will receive any context variables.
      if isinstance(data[0], dict):
        context_keys = {}
        for participant in data:
          context_keys.update(
            {k:"" for k in keys if k in participant["context"]}
          )
          data_keys = {k:"" for k in keys if k not in context_keys}

      for participant in data:
        # Opensesame structure
        if isinstance(participant, dict):
          context_values = (
            [participant['context'].get(k, None) for k in context_keys]
          )
          for trial in participant['data']:
            row = context_values + [trial.get(k, None) for k in data_keys]
            writer.writerow(row)

        # jsPsych structure
        if isinstance(participant, list):
          for trial in participant:
            row = [trial.get(k, None) for k in keys]
            writer.writerow(row)

  except OSError as error:
    print(f"OS error while writing CSV: {error}")
    sys.exit(1)

  except Exception as error:
    print(f"Unexpected error while writing CSV: {error=}, {type(error)=}")
    raise

def main():
  """Initiate data restructuring."""
  # Get command-line interface arguments
  args = get_args()

  # Read the JSON file
  print(f"Opening file: {args.file}")
  text = read_file(args.file)

  # Parse JSON
  print(f"Parsing file: {args.file}")
  data = parse_json(text)

  # Keys to extract from data
  keys = get_all_keys(data, args)
  if args.print:
    print(list(keys))
  else:
    # Write keys and values to CSV file
    print(f"Saving to file: {args.output}")
    write_to_csv(data, args.output, keys)

if __name__ == "__main__":
  main()
