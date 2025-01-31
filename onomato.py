import sys
from collections import defaultdict

KANA_ORDER = [
    'あ', 'い', 'う', 'え', 'お',
    'か', 'き', 'く', 'け', 'こ',
    'さ', 'し', 'す', 'せ', 'そ',
    'た', 'ち', 'つ', 'て', 'と',
    'な', 'に', 'ぬ', 'ね', 'の',
    'は', 'ひ', 'ふ', 'へ', 'ほ',
    'ま', 'み', 'む', 'め', 'も',
    'や', 'ゆ', 'よ',
    'ら', 'り', 'る', 'れ', 'ろ',
    'わ', 'を', 'ん',
    'ア', 'イ', 'ウ', 'エ', 'オ',
    'カ', 'キ', 'ク', 'ケ', 'コ',
    'サ', 'シ', 'ス', 'セ', 'ソ',
    'タ', 'チ', 'ツ', 'テ', 'ト',
    'ナ', 'ニ', 'ヌ', 'ネ', 'ノ',
    'ハ', 'ヒ', 'フ', 'ヘ', 'ホ',
    'マ', 'ミ', 'ム', 'メ', 'モ',
    'ヤ', 'ユ', 'ヨ',
    'ラ', 'リ', 'ル', 'レ', 'ロ',
    'ワ', 'ヲ', 'ン'
]
KANA_ORDER_DICT = {char: idx for idx, char in enumerate(KANA_ORDER)}

def get_sort_key(char):
    return KANA_ORDER_DICT.get(char, len(KANA_ORDER))

def parse_input(text):
    groups = defaultdict(list)
    seen_chars = set()
    
    for word in (line.strip() for line in text.split('\n') if line.strip()):
        if not word:
            continue
        first_char = word[0]
        if first_char not in seen_chars:
            seen_chars.add(first_char)
        groups[first_char].append(word)
    
    for key in groups:
        unique_words = sorted(set(groups[key]), key=lambda x: (len(x), x))
        groups[key] = unique_words
    
    return groups

def merge_onomatopoeia(original_text, add_text):
    original_groups = parse_input(original_text)
    add_groups = parse_input(add_text)
    
    merged_groups = defaultdict(list)
    
    # 合并原始数据
    for char in original_groups:
        merged_groups[char] = original_groups[char].copy()
    
    # 合并新增数据
    for char in add_groups:
        if char in merged_groups:
            combined = list(set(merged_groups[char] + add_groups[char]))
            merged_groups[char] = sorted(combined, key=lambda x: (len(x), x))
        else:
            merged_groups[char] = add_groups[char].copy()
    
    # 按五十音排序所有字符
    sorted_chars = sorted(merged_groups.keys(), key=get_sort_key)
    
    # 生成结果
    output = []
    for char in sorted_chars:
        output.extend(merged_groups[char])
        output.append('\n')
    
    return '\n'.join(output)

if __name__ == "__main__":
    def read_file(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            return ''
    
    original_file = r"D:\Codes\haystack\onomato.txt"
    add_file = r"D:\Codes\haystack\new.txt"
    original_content = read_file(original_file)
    add_content = read_file(add_file)
    
    result = merge_onomatopoeia(original_content, add_content)
    with open(original_file, "w", encoding="utf-8") as f:
        f.write(result)