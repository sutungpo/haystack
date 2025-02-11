import sys
import difflib
import regex as re
from pathlib import Path
from functools import lru_cache
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
        unique_words = sorted(set(groups[key]), key=lambda x: (len(x), x),reverse=True)
        groups[key] = unique_words
    
    return groups

def merge_add_to_original(original_text, add_text):
    """
    merge added text into original text, the text will be sorted by kana order group, each group will be sorted by length
    Args:
        original_text (str): original onomatopoeia list
        add_text (str): added onomatopoeia list
    Returns:
        str: merged onomatopoeia list
    """
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
            merged_groups[char] = sorted(combined, key=lambda x: (len(x), x), reverse=True)
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

def preprocess_text(text):
    '''
    reduce multiple newline to single newline, filter out invisible characters, content in parenthesis.
    '''
    # invisible characters
    text = re.sub(r'[\p{M}\p{Cf}]', '', text)
    # content in parenthesis
    text = re.sub(r'【[^】]*】|（[^）]*）|〈[^〉]*〉|（[^）]*）', '', text)
    text = re.sub(r'\n+', '\n', text)

    return text

def merge_input_to_onomato_list(text=None):
    """
    merge input to onomatopoeia list
    first input from user, filter out all non-kana characters, then merge to text
    Args:
        text (str): onomatopoeia list
    Returns:
        str: merged onomatopoeia list
    """
    lines = []
    while True:
        line = input("input onomatopoeias:").strip()
        if line == "":
            break
        lines.append(line)

    new_words = []
    for line in lines:
        words_in_line = re.findall(r'[\u3040-\u309F\u30A0-\u30FFー]+', line)
        new_words.extend(words_in_line)
    if text is None:
        text = ""
    merged_lines = merge_add_to_original(text, "\n".join(new_words))
    return merged_lines

def filter_onomatopoeia(words, candidates):
    """
    filter out onomatopoeia patterns from words

    Args:
        words (list): words to filter
        candidates (list): onomatopoeia words, candidates has to be well ordered, each group has same initial character
                            each word in the same group is ordered from longest to shortest length
    Returns:
        list: filtered onomatopoeia
    """
    # Prepare the suffix regex pattern using escaped special words
    special_words = ["ぁ","へ", "お", "れろ", "ん", "う", "ぅ", "い", "ー", "る"]
    segments = []
    for candidate in candidates:
        # Pattern for segments starting with this candidate
        segment_pattern = rf"{candidate}([{''.join(special_words)}]*っ?)"
        segments.append(segment_pattern)
    # The word should match one or more of these segments in sequence
    onomato_pattern = rf"({'|'.join(segments)})+"
    # Memoize the validation function to optimize repeated checks
    @lru_cache(maxsize=None)
    def is_onomato(subword):
        return bool(re.fullmatch(onomato_pattern, subword))

    # result = [word for word in words if not is_onomato(word)]
    result = []
    for i,word in enumerate(words):
        if not is_onomato(word):
            result.append(word)
    return result

def segment_to_words(text):
    '''
    text is Japanese text, segment it into sentences by punctuations.
    # full-width numbers and alphabets
    pattern = r'[\uFF21-\uFF3A\uFF41-\uFF5A\uFF10-\uFF19]+'
    # Japanese characters
    pattern = r"\p{Hiragana}\p{IsKatakana}\p{IsHan}ー゛゜々ゝヽヾ\uFF5E\u301C"
    # Japanese punctuations
    pattern = r"。、？！「」『』（）・…〜※＝；：《》〈〉［］【】｛｝　"
    '''
    # # From Grok
    # Define the delimiters
    weak_delimiters = r'…♪♡♥　\p{Emoji_Presentation}'
    strong_delimiters = r'。、？！'
    # "～" (U+FF5E)	(e.g., "3～5" for "3 to 5"). "〜" (U+301C)	Used in natural Japanese text, (e.g., "あ〜", "ん〜")
    japanese_characters = r"\p{Hiragana}\p{IsKatakana}\p{IsHan}ー゛゜々ゝヽヾ\uFF5E\u301C"
    full_width_alpnums = r'A-Za-z0-9\uFF21-\uFF3A\uFF41-\uFF5A\uFF10-\uFF19'
    brackets = r'「[^」]*」|『[^』]*』|（[^）]*）|〈[^〉]*〉|［[^］]*］|【[^】]*】|｛[^｝]*｝'
    # Regex pattern:
    # - Japanese characters followed by zero or more weak delimiters, then a strong delimiter or newline
    # - Or, sequences of weak delimiters alone
    pattern = rf'''
        (?P<bracket>{brackets})
        |(?P<group>[{weak_delimiters}]*
        (?:[{japanese_characters}{full_width_alpnums}]+)
        (?:[{weak_delimiters}]*[{strong_delimiters}]*[{weak_delimiters}]*)?)
        |(?P<delimiters>[{weak_delimiters}]+)
        |(?P<newline>\n+)
    '''
    # Use split to ensure all contexts are included
    segments = []
    start = 0
    for match in re.finditer(pattern, text, re.VERBOSE):
        if match.start() > start:
            segments.append(text[start:match.start()])  # Add any text before the match
        if match.group('bracket'):
            segments.append(match.group('bracket'))
        elif match.group('group'):
            segments.append(match.group('group'))
        elif match.group('delimiters'):
            segments.append(match.group('delimiters'))
        elif match.group('newline'):
            segments.append(match.group('newline'))
        start = match.end()
    
    # Add any remaining text after the last match
    if start < len(text):
        segments.append(text[start:])
    return segments

def compare_texts_char_level_with_positions(original, processed):
    '''
    print("Inserted characters (position, char):", inserted)
    print("Deleted characters (position, char):", deleted)
    '''
    # Convert text into lists of characters
    original_chars = list(original)
    processed_chars = list(processed)

    # Use difflib to get the differences
    diff = list(difflib.ndiff(original_chars, processed_chars))

    inserted = []
    deleted = []

    original_index = 0  # Tracks position in the original text
    processed_index = 0  # Tracks position in the processed text

    for item in diff:
        if item.startswith(' '):  # No change
            original_index += 1
            processed_index += 1
        elif item.startswith('-'):  # Deleted character
            deleted.append((original_index, item[2:]))  # Store (position, character)
            original_index += 1
        elif item.startswith('+'):  # Inserted character
            inserted.append((processed_index, item[2:]))  # Store (position, character)
            processed_index += 1

    return inserted, deleted
