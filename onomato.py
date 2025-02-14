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
        str: merged onomatopoeia text
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
    # invisible characters, \uFE0F 
    text = re.sub(r'[\p{M}\p{Cf}]', '', text)
    # content in parenthesis
    text = re.sub(r'【[^】]*】|（[^）]*）|〈[^〉]*〉|（[^）]*）', '', text)
    text = re.sub(r'\n+', '\n', text)

    return text

def postprocess_text(text):
    '''
    reduce multiple fullwidth space to single fullwidth space, filter out fullwidth space if at the end or begin, after that, reduce multiple \n to \n
    '''
    text = re.sub('[♡♪]+', r'\u3000', text)
    text = re.sub(r'\u3000+', r'\u3000', text)
    text = re.sub(r'^\u3000+|\u3000+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*\n', '\n', text)
    return text

def merge_input_to_onomato_list(text=None):
    """
    merge input to onomatopoeia list
    first input from user, filter out all non-kana characters, then merge to text
    Args:
        text (str): onomatopoeia list
    Returns:
        str: merged onomatopoeia text
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
    merged_texts = merge_add_to_original(text, "\n".join(new_words))
    return merged_texts

class OnomatopoeiaPatternMatcher:
    def __init__(self, candidate_file):
        # You can extend this list based on your needs
        with open(candidate_file, 'r', encoding='utf-8') as f:
            self.candidate_words = [line.strip() for line in f.readlines() if line.strip()]
        # Special suffix words (送り仮名など)
        self.special_words = [ "あ","ぁ", "へ", "ぉ", "お", "れろ", "ん", "う", "ぅ", "い", "ー", "る", "～", "っ","ッ", "゛", "ル", "ォォ"]
        
        # Build the regex pattern
        self._build_pattern()
    
    def _build_pattern(self):
        # Escape special characters in candidate words
        escaped_candidates = [re.escape(word) for word in self.candidate_words]
        # Join candidates with OR operator
        candidates_pattern = '|'.join(escaped_candidates)
        
        # Escape special characters in special words
        escaped_specials = [re.escape(word) for word in self.special_words]
        # Join special words with OR operator and allow repetition of each special word
        specials_pattern = '|'.join(f'(?:{word})+' for word in escaped_specials)
        
        # Complete pattern:
        # - (?:{candidates}) : One candidate word
        # - (?:(?:{specials}))* : Zero or more groups of repeated special words
        # - (?: ... )+ : One or more of the above combination
        self.pattern = re.compile(
            f'(?:(?:{specials_pattern})+|(?:(?:{specials_pattern})*(?:{candidates_pattern})(?:{specials_pattern})*)+)',
            re.V1
        )
    
    def find_matches(self, text):
        """Find all onomatopoeia matches in the given text."""
        return self.pattern.finditer(text)
    
    def is_match(self, text):
        """Check if the entire text is a valid onomatopoeia."""
        return bool(self.pattern.fullmatch(text))

def filter_onomatopoeia(words):
    """
    filter out onomatopoeia patterns from words

    Args:
        words (list): words to filter
    Returns:
        list: filtered onomatopoeia
    """
    # Memoize the validation function to optimize repeated checks
    matcher = OnomatopoeiaPatternMatcher('onomato.txt')
    @lru_cache(maxsize=None)
    def is_onomato(subword):
        return matcher.is_match(subword)

    result = []
    japanese_characters = r"\p{Hiragana}\p{IsKatakana}\p{IsHan}ー゛゜々ゝヽヾ\uFF5E\u301C"
    full_width_alpnums = r'A-Za-z0-9\uFF21-\uFF3A\uFF41-\uFF5A\uFF10-\uFF19'
    for i,word in enumerate(words):
        clean_word = re.sub(f"[^{japanese_characters}{full_width_alpnums}]", "", word)
        if is_onomato(clean_word):
            result.append('\u3000')
        else:
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
    brackets = r'「[^」]*」|『[^』]*』|（[^）]*）|〈[^〉]*〉|［[^］]*］|【[^】]*】|｛[^｝]*｝|《[^》]*》'
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
