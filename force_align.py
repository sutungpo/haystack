from pydoc import text
import regex as re
import math
import unicodedata
from pathlib import Path
from functools import partial
from logging import getLogger, basicConfig, DEBUG

basicConfig(level=DEBUG)
logger = getLogger(__name__)    

class Interval:
    def __init__(self, xmin, xmax, text):
        self.start = xmin
        self.end = xmax
        self.text = text

    def __repr__(self):
        return f'Interval(start={self.xmin}, end={self.xmax}, text="{self.text}")'

class IntervalTier:
    def __init__(self, name, xmin, xmax, intervals):
        self.name = name
        self.start = xmin
        self.end = xmax
        self.intervals = intervals

    def __repr__(self):
        return f'IntervalTier(name="{self.name}", xmin={self.start}, xmax={self.end}, intervals={self.intervals})'

class TextGrid:
    def __init__(self, file_path=None):
        self.start = 0.0
        self.end = 0.0
        self.tiers = []
        if file_path:
            self.read_textgrid(file_path)

    def __repr__(self):
        return f'TextGrid(xmin={self.start}, xmax={self.end}, tiers={self.tiers})'

    def read_textgrid(self,file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        self.start = float(lines[3].split('=')[1].strip())
        self.end = float(lines[4].split('=')[1].strip())
        size_tiers = int(lines[6].split('=')[1].strip())

        tiers = []
        i = 8
        for _ in range(size_tiers):
            name = lines[i+2].split('=')[1].strip().strip('"')
            xmin_tier = float(lines[i + 3].split('=')[1].strip())
            xmax_tier = float(lines[i + 4].split('=')[1].strip())
            size_intervals = int(lines[i + 5].split('=')[1].strip())
            intervals = []
            i += 6
            for _ in range(size_intervals):
                xmin_interval = float(lines[i + 1].split('=')[1].strip())
                xmax_interval = float(lines[i + 2].split('=')[1].strip())
                text = lines[i + 3].split('=')[1].strip().strip('"')
                intervals.append(Interval(xmin_interval, xmax_interval, text))
                i += 4
            self.tiers.append(IntervalTier(name, xmin_tier, xmax_tier, intervals))

    def write_textgrid(self,textgrid, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write('File type = "ooTextFile"\n')
            file.write('Object class = "TextGrid"\n')
            file.write('\n')
            file.write(f'xmin = {textgrid.start}\n')
            file.write(f'xmax = {textgrid.end}\n')
            file.write('tiers? <exists>\n')
            file.write(f'size = {len(textgrid.tiers)}\n')
            file.write('item []:\n')
            for i, tier in enumerate(textgrid.tiers):
                file.write(f'    item [{i + 1}]:\n')
                file.write(f'        class = "IntervalTier"\n')
                file.write(f'        name = "{tier.name}"\n')
                file.write(f'        xmin = {tier.start}\n')
                file.write(f'        xmax = {tier.end}\n')
                file.write(f'        intervals: size = {len(tier.intervals)}\n')
                for j, interval in enumerate(tier.intervals):
                    file.write(f'        intervals [{j + 1}]:\n')
                    file.write(f'            xmin = {interval.start}\n')
                    file.write(f'            xmax = {interval.end}\n')
                    file.write(f'            text = "{interval.text}"\n')

def tokenize(text):
    from japanese import JapaneseTokenizer
    tokenizer = JapaneseTokenizer()
    tokens = tokenizer(text)
    result = tokens[0].split()
    return result

def preprocess_text(text):
    invisible_pattern = r'[\p{Z}]'
    final_text = []
    for line in text.split('\n'):
        line = re.sub(invisible_pattern, '', line.strip())
        line = unicodedata.normalize('NFKC', line)
        if line == '':
            continue
        if line.startswith('(') or line.startswith('（'):
            continue
        final_text.append(line)
    return final_text

def merge_text(text_with_timestamp):
    SPAN_TIME = 10.0
    merged_text = []
    current_line = text_with_timestamp[0]
    current_num = 1
    for line in text_with_timestamp[1:]:
        _, current_line_text, current_line_start_time, _ = current_line.strip().split('\t')
        current_line_start_time = float(current_line_start_time)
        _, text, start_time, end_time = line.strip().split('\t')
        start_time, end_time = float(start_time), float(end_time)
        if end_time - current_line_start_time < SPAN_TIME:
            end_mark = '' if re.search('[。！？]$', current_line_text) else '。'
            current_line_text = current_line_text + end_mark + text
            current_line = f'{current_num}\t{current_line_text}\t{current_line_start_time}\t{end_time}\n'
        else:
            current_num += 1
            merged_text.append(current_line)
            num_pattern = r'^\d+'
            current_line = re.sub(num_pattern, str(current_num), line)
    merged_text.append(current_line)
    prev_end_time = None
    for i, line in enumerate(merged_text):
        _, _, start_time, end_time = line.strip().split('\t')
        start_time, end_time = float(start_time), float(end_time)
        if prev_end_time is not None and math.isclose(prev_end_time, start_time):
            logger.warning(f'Line {i+1} start time is the same as line {i} end_time')
        prev_end_time = end_time
    return merged_text

def align_line_timestamps(transcript, intervals):
    # iterate over each line of the transcript
    # for each line iteration, first tokenize the line as token set, then iterate over each interval until the interval's text is not in the set
    # cache these iterated intervals, its first interval's start time and last interval's end time as the line's start and end time
    # track the intervals that have been iterated over to avoid iterating over them again
    punctuation_pattern = r'[\p{P}\p{S}]'
    strip_lines_list = preprocess_text(transcript)
    current_interval_idx = 0
    refined_lines = []
    for line_idx, line in enumerate(strip_lines_list): 
        t_list = tokenize(line)
        non_punc_tokens_list = [token for token in t_list if not re.match(punctuation_pattern, token)]
        if not non_punc_tokens_list:
            continue
        non_punc_token_set = set(non_punc_tokens_list)
        start_time = None
        start_token = None
        end_time = None
        end_token = None
        matched_nums = 0
        for i in range(current_interval_idx, len(intervals)):
            if matched_nums == len(non_punc_tokens_list):
                break
            if intervals[i].text in non_punc_token_set:
                if start_time is None:
                    start_time = intervals[i].start
                    start_token = intervals[i].text
                end_time = intervals[i].end
                end_token = intervals[i].text
                current_interval_idx = i + 1
                matched_nums += 1
        if start_token != non_punc_tokens_list[0] or end_token != non_punc_tokens_list[-1]:
            logger.warning(f'Line {line_idx+1} start with "{non_punc_tokens_list[0]}" does not match with the corresponding interval')
        start_time = start_time if start_time is not None else 0.0
        end_time = end_time if end_time is not None else 0.0
        refined_line = str(line_idx+1) + '\t' + line + '\t' + f'{start_time:.2f}' +'\t' + f'{end_time:.2f}' + '\n'
        refined_lines.append(refined_line)
    return refined_lines

if __name__ == '__main__':
    textgrid_file = r"D:\codes\mfa\暇つぶしセックス.TextGrid"
    transcript_file = r"E:\jav\RJ codes\101-\RJ01051681\1 『暇つぶしセックス。どーお』.txt"
    audio_file = r".\プロローグ.mp3"
    textgrid = TextGrid(textgrid_file)
    with open(transcript_file, 'r', encoding='utf-8') as file:
        transcript = file.read()
    intervals = TextGrid(textgrid_file).tiers[0].intervals
    refined_lines = align_line_timestamps(transcript, intervals)
    transcript_refined_file = Path(transcript_file).stem + '_refined.txt'
    with open(transcript_refined_file, 'w', encoding='utf-8') as file:
        file.write(''.join(refined_lines))
    refined_lines = merge_text(refined_lines)
    transcript_merged = Path(transcript_file).stem + 'merged.txt'
    with open(transcript_merged, 'w', encoding='utf-8') as file:
        file.write(''.join(refined_lines))
    # result_path = Path(transcript_file).parent / 'result'
    # result_path.mkdir(exist_ok=True)
    # for line in refined_lines:
    #     line_num, text, start_time, end_time = line.strip().split('\t')
    #     line_num, start_time, end_time = int(line_num), float(start_time), float(end_time)
    #     audio_num = result_path / f'{line_num}.mp3'
    #     text_num = result_path / f'{line_num}.txt'
    #     with open(text_num, 'w', encoding='utf-8') as file:
    #         file.write(text)
    #     cmd = ['ffmpeg', '-i', audio_file, '-ss', str(start_time), '-to', str(end_time), '-c', '-loglevel', 'quiet','copy', str(audio_num)]
    #     import subprocess
    #     subprocess.run(cmd)

    
