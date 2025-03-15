import sys
import difflib
import regex as re
import jaconv
from pathlib import Path
from functools import lru_cache
from collections import defaultdict
from logging import getLogger, basicConfig, DEBUG

basicConfig(level=DEBUG)
logger = getLogger(__name__)

# full-width tilde \uFF5E and wave dash \u301C
Japanese_characters = r"\p{Hiragana}\p{IsKatakana}\p{IsHan}ー゛゜々ゝヽヾ\uFF5E\u301C"
Full_width_alpnums = r'A-Za-z0-9\uFF21-\uFF3A\uFF41-\uFF5A\uFF10-\uFF19'
Japanese_punctuations = r'。、！？「」『』（）［］｛｝…ー・～〝〟'

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
    # text = jaconv.kata2hira(text)
    # invisible characters, \uFE0F 
    if '○' in text:
        logger.warning("censorship mark '○' found in text, please replace them correctly")
    text = re.sub(r'[\p{M}\p{Cf}]', '', text)
    # content in parenthesis
    text = re.sub(r'【[^】]*】|（[^）]*）|〈[^〉]*〉|（[^）]*）|^[^\S\n]*//.*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n+', '\n', text)

    return text

def postprocess_text(text):
    '''
    reduce multiple fullwidth space to single fullwidth space, filter out fullwidth space if at the end or begin, after that, reduce multiple \n to \n
    '''
    text = re.sub('[♡❤♥♪〓]+', r'\u3000', text)
    text = re.sub(r'\s*\n', '\n', text)
    text = re.sub(r'^\P{L}*\n|^[^\S]+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'[\u0020\u3000]{2,}', lambda m: m.group(0)[0], text)
    text = re.sub(r'^[\u3000+\u0020]+|[\u3000\u0020]+$', '', text, flags=re.MULTILINE)
    text = re.sub(rf'([{Japanese_punctuations}])\u3000|\u3000', lambda m: m.group(1) if m.group(1) else '、', text)
    return text

def merge_input_to_onomato_list(text=None):
    """
    merge input to onomatopoeia list
    first input from user, filter out all non-kana characters, then merge to text
    Args:
        text (str): onomatopoeia list, assume each line is a onomatopoeia word
    Returns:
        str: merged onomatopoeia text
    """
    new_words = []
    while True:
        line = input("input onomatopoeias, null to exit:\n").strip()
        if line == "":
            break
        assert re.search(rf'^[{Japanese_characters}]+', line) is not None, "input must be kana"
        new_words.append(line)
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
        self.special_chars = [ "あ","ぁ", "へ", "ぉ", "お", "れろ", "ん", "う", "ぅ", "ぃ", "ー", "～", "〜", "っ", "つ","ッ", "゛", "ル", "ォォ", "ォ"]
        ## exceptions are words that are not onomatopoeia but are match the pattern
        self.exceptions = ['ううん', 'ううんっ','はぁーい', 'はぁい', 'あっつ', 'やぁっ', 'あほっ', 'おはっ']
        ## unknown not sure onomatopoeia or not
        self.unkowns = ['こく']
        self.known_onomato = ['いっぱぁい']
        # Build the regex pattern
        self._build_pattern()
    
    def _build_pattern(self):
        ## test case
        # self.candidate_words = ['っぅう', 'っぁん']
        # self.special_chars = [ "あ","ん", "う", "ぅ", "っ", "つ"]
        # Escape special characters in candidate words
        escaped_candidates = [re.escape(word) for word in self.candidate_words]
        # Join candidates with OR operator
        candidates_pattern = '|'.join(escaped_candidates)
        
        # Escape special characters in special words
        escaped_specials = [re.escape(word) for word in self.special_chars]
        # Join special words with OR operator and allow repetition of each special word
        specials_pattern = '|'.join(f'(?:{word})' for word in escaped_specials)
        
        # Complete pattern:
        # - (?:{candidates}) : One candidate word
        # - (?:(?:{specials}))* : Zero or more groups of repeated special words
        # - (?: ... )+ : One or more of the above combination
        # Matched Pattern:
        # consecutive special words or (non-initial "ぃ" + zero or more special words + candidate word + zero or more special words)+
        final_pattern = rf'''
            \b[っつぁあ]\b|
            ^(?<![ぃいっ])(?:{specials_pattern}){{2,}}|
            ^(?<![ぃいっ])(?:(?:{specials_pattern})*(?:{candidates_pattern})(?:{specials_pattern})*)+
        '''
        self.pattern = re.compile(final_pattern,re.VERBOSE)
    
    def find_matches(self, text):
        """Find all onomatopoeia matches in the given text."""
        return self.pattern.finditer(text)
    
    def is_match(self, text):
        """Check if the entire text is a valid onomatopoeia."""
        if text in self.exceptions:
            return False
        elif text in self.unkowns:
            logger.warning(f'unknown onomatopoeia: {text}')
        elif text in self.known_onomato:
            return True
        return bool(self.pattern.fullmatch(text))

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
    # japanese_characters = r"\p{Hiragana}\p{IsKatakana}\p{IsHan}ー゛゜々ゝヽヾ\uFF5E\u301C"
    # full_width_alpnums = r'A-Za-z0-9\uFF21-\uFF3A\uFF41-\uFF5A\uFF10-\uFF19'
    brackets = r'「[^」]*」|『[^』]*』|（[^）]*）|〈[^〉]*〉|［[^］]*］|【[^】]*】|｛[^｝]*｝|《[^》]*》'
    # Regex pattern:
    # - Japanese characters followed by zero or more weak delimiters, then a strong delimiter or newline
    # - Or, sequences of weak delimiters alone
    pattern = rf'''
        (?P<bracket>{brackets})
        |(?P<group>[{weak_delimiters}]*
        (?:[{Japanese_characters}{Full_width_alpnums}]+)
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

def filter_onomatopoeia_from_text(text):
    """
    filter out onomatopoeia patterns from text
    """
    text_final = preprocess_text(text)
    text_segments = segment_to_words(text_final)
    matcher = OnomatopoeiaPatternMatcher('onomato.txt')
    @lru_cache(maxsize=None)
    def is_onomato(subword):
        return matcher.is_match(subword)

    result = []
    for i,word in enumerate(text_segments):
        clean_word = re.sub(f"[^{Japanese_characters}{Full_width_alpnums}]", "", word)
        if is_onomato(clean_word):
            result.append('\u3000')
        else:
            result.append(word)
    post_pattern = ['こく、こく', 'こくっ、こくっ', 'お、', 'ぉ、', 'う、', 'あ、']
    post_pattern = '|'.join(post_pattern)
    result = re.sub(rf'(?<!\p{{L}})({post_pattern})', '', ''.join(result))
    result = postprocess_text(result)
    return result

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
    inserted_chars = segment_to_words(''.join([char[1] for char in inserted]))
    deleted_chars = segment_to_words(''.join([char[1] for char in deleted]))
    matcher = OnomatopoeiaPatternMatcher('onomato.txt')
    final_deleted = []
    for char in deleted_chars:
        match = re.search(r'\p{L}+', char)
        if match:
            if match.group() not in matcher.candidate_words:
                final_deleted.append(char)
    return inserted_chars, final_deleted
