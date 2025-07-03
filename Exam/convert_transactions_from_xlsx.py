import pathlib
import re
import pandas as pd

def find_and_process_case_files():
    """
    Search recursively in ../testing_case_5 for xlsx files containing 'suspect' or 'victim'
    where the immediate parent folder starts with 'Case #'
    """
    search_dir = pathlib.Path('../testing_case_5')
    suspect_victim_pattern = re.compile(r'(suspect|victim)', re.IGNORECASE)
    case_pattern = re.compile(r'^case\s+([a-zA-Z]+)', re.IGNORECASE)
    number_pattern = re.compile(r'(suspect|victim)\s+(\d+)', re.IGNORECASE)
    matching_files = []

    if not search_dir.exists():
        print(f"Directory not found: {search_dir.resolve()}")
        return

    print(f"Searching recursively in: {search_dir.resolve()}")
    print("=" * 80)

    for xlsx_file in search_dir.rglob('*.xlsx'):
        if not suspect_victim_pattern.search(xlsx_file.name):
            continue
        parent_folder = xlsx_file.parent.name
        case_match = case_pattern.match(parent_folder)
        if case_match:
            case_num = case_match.group(1)
            matching_files.append((xlsx_file, case_num))

    if not matching_files:
        print("No matching files found!")
        return

    output_dir = pathlib.Path('Raw Transaction Records')
    output_dir.mkdir(exist_ok=True)

    print("Processing files:")
    print("=" * 80)
    processed_count = 0

    for xlsx_file, case_num in matching_files:
        try:
            filename_lower = xlsx_file.name.lower()
            if 'suspect' in filename_lower:
                type_str = 'Suspect'
            elif 'victim' in filename_lower:
                type_str = 'Victim'
            else:
                continue
            number_match = number_pattern.search(filename_lower)
            if number_match:
                suspect_victim_num = int(number_match.group(2))
            else:
                suspect_victim_num = 1
            output_filename = f"Case_{case_num}_{type_str}_{suspect_victim_num}_transaction_record.csv"
            output_path = output_dir / output_filename
            df = pd.read_excel(xlsx_file, sheet_name=0)
            df.to_csv(output_path, index=False)
            print(f"{xlsx_file.resolve()} → {output_filename}")
            processed_count += 1
        except Exception as e:
            print(f"{xlsx_file.resolve()} → Failed: {str(e)}")

    print("=" * 80)
    print(f"Files saved to: {output_dir.resolve()}")
    print(f"\nTotal files processed: {processed_count}")

if __name__ == "__main__":
    find_and_process_case_files()
