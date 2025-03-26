from onomato import *
from force_align import *
from pathlib import Path
choice = input("1: filter or folder onomatopoeia from text\n2: merge onomatopoeia\n3: align textgird with transcription\n")
if choice == '1':
    def remove_onomatopoia(path):        
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        final_text = filter_onomatopoeia_from_text(text)
        result = Path(path).name
        with open(result, 'w', encoding='utf-8') as f:
            f.write(final_text)
        inserted, deleted = compare_texts_char_level_with_positions(text, final_text)
        print("Inserted characters:", inserted)
        print("Deleted characters:", deleted)
    path = input("1: input text file or folder\n")
    path = path.strip('"').strip("'")
    path = Path(path)
    if path.is_dir():
        for file in path.glob('*.txt'):
            remove_onomatopoia(file)
    else:
        remove_onomatopoia(path)
elif choice == '2':
    with open('onomato.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    txt = merge_input_to_onomato_list(text)
    with open('onomato.txt', 'w', encoding='utf-8') as f:
        f.write(txt)
elif choice == '3':
    # align textgrid with transcript
    response = input("Enter the path to the textgrid file: \n")
    textgrid_path = Path(response.strip('"'))
    if not textgrid_path.exists() or textgrid_path.suffix != '.TextGrid':
        print("The path you entered does not exist.")
        exit()
    aligner = JapaneseTextAligner()
    aligner.align_text(textgrid_path)
    response = input("Enter YES to continue: \n")
    if response.lower().strip() != 'y':
        print("Exiting...")
        exit()
    aligned_text = textgrid_path.with_suffix('.aligned.txt')
    if not aligned_text.exists():
        print("The aligned text file does not exist.")
        exit()
    aligner._format_check(aligned_text)
