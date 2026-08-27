import argparse
import sys
import io
import json
import csv
from typing import Any


def getArgs() -> argparse.Namespace:
    """
    Parses the command‑line arguments.
    Returns: argparse.Namespace: Command-line arguments inputs as an argparse.Namespace object.
    """
    parser = argparse.ArgumentParser(prog='jsonToCsv', description='Convert jsPsych and OSweb data to CSV format')
    parser.add_argument('file', help='the input file')
    parser.add_argument('output', nargs='?', default='output.csv', help='the output file')
    parser.add_argument('variables', nargs='*', help='one or more variables to extract from the input file')
    parser.add_argument('-a', '--all', action='store_true', help='extract all variables from the data')
    parser.add_argument('-p', '--print', action='store_true', help='print all variables from the input file')
    parser.add_argument('-f', '--force', action='store_true', help='force overwrite')
    args = parser.parse_args()
    
    if args.file == args.output and not args.force:
        sys.exit(f"Error: input and output refer to the same file ({args.file}). "
                  "Use --force to allow overwriting.")
    return args

def readFile(file: str) -> list[dict | list]:
    """
    Read input file.
    Args: file (str): Path to a file that contains one participant per row.
    PRE: `file` must comform to either Opensesame or jsPsych data structure.
    Returns: list[dict | list]: Raw text with one participant per row
    """
    try:
        with io.open(file, "r", encoding="UTF-8") as f:
            text = f.readlines()
    except OSError as err:
        print("OS error:", err)
        sys.exit(1)
    except Exception as err:
        print(f"Unexpected error: {err=}, {type(err)=}")
        raise

    return text

def parseJson(text: list) -> list[dict]:
    """
    Parse the JSON data
    Input: text (list): Raw text with one participant on each row.
    PRE: `text` need to follow either Opensesame or jsPsych data structure.
    Returns: list[dict]: A list of dictionaries, each containing the parsed data for one participant.
    """
    acc = []
    for line in text:
        try:
            parsed = json.loads(line)
        
        except json.JSONDecodeError as err:
            # Print the context around the error
            print(f"JSON decode error: {err.msg} at line {err.lineno} column {err.colno} (char {err.pos})")
            try:
                fixedContent = repairJsonData(line)
                parsed = json.loads(fixedContent)
                print(f"Error was fixed for participant")
            except:
                print(f"Could not fix corrupt data: {err}")

        except Exception as err:
            print(f"Unexpected error during JSON parsing: {err=}, {type(err)=}")
            raise

        acc.append(parsed)

    return acc

def repairJsonData(incompleteJson: str) -> str:
    """
    Fix corrupt JSON data by adding missing brackets and data wrapper.
    Args: incompleteJson (str): JSON string missing closing brackets and data wrapper
    PRE: `incompleteJson` must be an OpenSesame‑style JSON fragment that
          ends abruptly (typically missing the final `]` and the outer
          `{"data": …, "context": …}` wrapper).
    Returns: str: Properly structured JSON string with data wrapper.
    """
    incompleteJson = incompleteJson[:-2] + "]"
    fixedJson = '{"data":' + incompleteJson + ',"context":{"browser":{}}}'

    return fixedJson

def getAllKeys(data: list[dict | list], args: argparse.Namespace) -> dict[str, Any]:
    """
    Extract all keys from the input file or the user-provided list of variables.
    Args: data (list[dict | list]): A list with a participants on each row, either as a dict or as a list. 
          args (argparse.Namespace): User terminal inputs
    PRE: `data` need to follow either Opensesame or jsPsych data structure.
    Return: dict[str, Any]: Dictornary with variables as keys and an empty value.
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

def writeToCsv(data: list[dict | list], outputFile: str, keys: dict[str, Any]) -> None:
    """
    Writ all the keys to the first row of a CSV file and then add the corresponding values 
    for each participant's trials on subsequent row.
    Args: data (list[dict | list]): A list with a participants on each row, either as a dict or as a list. 
          outputFile (str): Path to the CSV file that will be created/overwritten.
          keys (dict[str, Any]): Dictornary with variables as keys and an empty value.
    PRE: `data` need to follow either Opensesame or jsPsych data structure.
         The directory containing `outputFile` must be writable.
    Returns: None
    """
    try:
        with open(outputFile, "w", newline="", encoding="UTF-8") as csvfile:

            writer = csv.writer(csvfile)
            writer.writerow(list(keys.keys()))

            # Opensesame structure
            # Need to retrieve all context variables from every participant.
            # Otherwise, if the first participant lacks the context,
            # none of the subsequent participants will receive any context variables.
            if isinstance(data[0], dict):
                contextKeys = {} 
                for participant in data:
                    contextKeys.update({k:"" for k in keys if k in participant["context"]})
                dataKeys = {k:"" for k in keys if k not in contextKeys}

            for participant in data:
                # Opensesame structure
                if isinstance(participant, dict):
                    contextValues = [participant['context'].get(k, None) for k in contextKeys]
                    for trial in participant['data']:
                        row = contextValues + [trial.get(k, None) for k in dataKeys]
                        writer.writerow(row)
                
                # jsPsych structure
                if isinstance(participant, list):
                    for trial in participant:
                        row = [trial.get(k, None) for k in keys]
                        writer.writerow(row)

    except OSError as err:
        print(f"OS error while writing CSV: {err}")
        sys.exit(1)
    except Exception as err:
        print(f"Unexpected error while writing CSV: {err=}, {type(err)=}")
        raise

def main():

    # Get command-line interface arguments
    args = getArgs()
    
    # Read the JSON file
    print(f"Opening file: {args.file}")
    text = readFile(args.file)

    # Parse JSON
    print(f"Parsing file: {args.file}")
    data = parseJson(text)

    # Keys to extract from data
    keys = getAllKeys(data, args)
    if args.print:
        print(list(keys))
    else:
        # Write keys and values to CSV file
        print(f"Saving to file: {args.output}")
        writeToCsv(data, args.output, keys)

if __name__ == "__main__":
    main()
