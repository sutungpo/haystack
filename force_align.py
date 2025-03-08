from pydoc import text
import regex as re
from pathlib import Path
from logging import getLogger, basicConfig, DEBUG
from onomato import *
import textgrid
import unicodedata
import subprocess
from difflib import SequenceMatcher
from typing import List, Tuple, Optional
from dataclasses import dataclass

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
    
    def __iter__(self):
        return self.intervals

class TextGrid:
    def __init__(self, file_path=None):
        self.start = 0.0
        self.end = 0.0
        self.tiers = []
        if file_path:
            self.read_textgrid(file_path)

    def __repr__(self):
        return f'TextGrid(xmin={self.start}, xmax={self.end}, tiers={self.tiers})'
    
    def get_tier(self, name):
        for tier in self.tiers:
            if tier.name == name:
                return tier
        return None

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

@dataclass
class TextSegment:
    """Represents a segment of text with timing information"""
    start_time: float
    end_time: float
    line_text: str

@dataclass
class LineSegment:
    """Represents timing information for a full line of text"""
    line_num: int
    start_time: float
    end_time: float
    confidence: float
    line_text: str

class JapaneseTextAligner:
    def __init__(self, textgrid_path: str | Path):
        self.textgrid_path = textgrid_path
        self.start = 0
    
    def _filter_non_japanese(self, text: str) -> str:
        """Remove non-Japanese characters from text"""
        return re.sub(rf'[^{Japanese_characters}{Full_width_alpnums}]', '', text)

    def _normalize_japanese(self, text: str) -> str:
        """Normalize Japanese text for better matching"""
        text = unicodedata.normalize('NFKC', text)
        # the alphanumeric characters are converted from full width to ascii lowercase
        text = text.lower()
        return ''.join(text.split())

    def _get_word_segments(self, tg: textgrid.TextGrid) -> List[TextSegment]:
        """Extract word segments with timing from TextGrid"""
        segments = []
        word_tier = tg[0]
        for interval in word_tier:
            if interval.mark.strip():
                segments.append(TextSegment(
                    start_time=float(interval.minTime),
                    end_time=float(interval.maxTime),
                    line_text=interval.mark,
                ))
        # Add a dummy segment to decline the similarity score for the last line
        segments.append(TextSegment(
            start_time=0.0,
            end_time=0.0,
            line_text="++",
        ))
        return segments

    def _find_growing_sequence(self, line: str, segments: List[TextSegment]) -> Tuple[int, int, float]:
        """
        Find the sequence with linearly growing similarity scores
        
        Args:
            line: Target line to match
            segments: List of available segments
            
        Returns:
            Tuple of (start_index, end_index, confidence)
        """
        matcher = SequenceMatcher(None, "", line)
        
        best_start = 0
        best_end = 0
        best_score = 0.0
        
        start = self.start
        scores = []
        combined_text = ""
        
        # Build sequence and track scores
        for end in range(start, len(segments)):
            combined_text += segments[end].line_text
            matcher.set_seq1(combined_text)
            score = matcher.ratio()
            if score < 0.01:
                scores = []
                combined_text = ""
                start = start + 1
                continue
            scores.append(score)
            
            # Need at least 3 points to check growth pattern
            if len(scores) >= 2:
                # Check if scores are growing linearly
                is_growing = all(scores[i] < scores[i+1] for i in range(len(scores)-1))
                
                # Check if growth has peaked
                if not is_growing:
                    current_score = scores[-2]  # Use peak score
                    best_score = current_score
                    best_start = start
                    best_end = end - 1  # Use position before decline
                    self.start = end
                    break
        
        return best_start, best_end, best_score

    def _find_line_matches(self, line: str, segments: List[TextSegment], line_num: int) -> Optional[LineSegment]:
        """
        Find best matching sequence for a line, segments are list from textgrid word elements
        """
        if not line.strip():
            return None
        MAX_LINE_TIME = 10.0
        MIN_LINE_INTERVAL = 0.5
        filtered_line = self._filter_non_japanese(line)
        filtered_line = self._normalize_japanese(filtered_line)
        start_idx, end_idx, confidence = self._find_growing_sequence(filtered_line, segments)
        
        if confidence < 0.6:  # Minimum threshold
            logger.warning(f"Line {line_num} {line} has low confidence: {confidence:.2f}")
        start_text = segments[start_idx].line_text
        end_text = segments[end_idx].line_text
        start_time = segments[start_idx].start_time
        end_time = segments[end_idx].end_time
        if line_num > 1:
            pre_end_idx = start_idx - 1 if segments[start_idx - 1].line_text else start_idx - 2
            pre_end_time = segments[pre_end_idx].end_time
            if start_time - pre_end_time < MIN_LINE_INTERVAL:
                logger.warning(f"Line {line_num} too close with previous line: {start_time - pre_end_time:.2f} seconds")
        # error detection, too long means this line's match error, it will cover next lines' timestamps, and make them errors too, if the line's endtime is too close(<0.2s) to next line's starttime, it will be considered as a match error for both of these two lines
        if end_time - start_time > MAX_LINE_TIME:
            logger.error(f"Line {line_num} {line} is too long: {end_time - start_time:.2f} seconds")
        # Check if the start and end texts match the line
        if not re.search(f'^{start_text}', filtered_line):
            logger.warning(f"Line {line_num} Start text mismatch: {start_text} vs {filtered_line}")
        elif not re.search(f'{end_text}$', filtered_line):
            logger.warning(f"Line {line_num} End text mismatch: {end_text} vs {filtered_line}")
        
        return LineSegment(
            line_num= line_num,
            start_time=segments[start_idx].start_time,
            end_time=segments[end_idx].end_time,
            confidence=confidence,
            line_text=line,
        )

    def align_text(self):
        """
        Align text lines with TextGrid timestamps, default text file is the same as the textgrid file with .txt extension
        first align each line start and end timestamp with textgrid, then merge lines that are too close to each other
        side effect is to write a new text file with all lines' timestamps to ".aligned.txt" and another text with merged lines' timestamps to ".merged_aligned.txt"
        the text and textgrid are only iterated only each once, each line content of text should be the same as textgrid or just one character difference, otherwise the alignmen will be wrong.
        """
        MAX_MERGED_LINE_TIME = 25.0
        tg_path = Path(self.textgrid_path)
        if not tg_path.exists():
            return
        text_path = tg_path.with_suffix('.txt')
        if not text_path.exists():
            return
        with open(text_path, 'r', encoding='utf-8') as f:
            text_lines = [line.strip() for line in f if line.strip()]
        tg = textgrid.TextGrid.fromFile(tg_path)
        segments = self._get_word_segments(tg)    

        # align each line start and end timestamp with textgrid
        skip = False
        aligned_txt = tg_path.with_suffix('.aligned.txt')
        if aligned_txt.exists():
            response = input(f"{aligned_txt} already exists, do you want to overwrite it? (y/n)")
            skip = response.lower().strip() == 'n'
        if not skip:
            with open(aligned_txt, 'w', encoding='utf-8') as f:
                for i, line in enumerate(text_lines):
                    line_num = i + 1
                    line_timestamps = self._find_line_matches(line, segments, line_num)
                    f.write(f"{line_num}\t{line_timestamps.start_time:07.2f}\t{line_timestamps.end_time:07.2f}\t{line}\n")

        # then merge lines that are too close to each other
        skip = False
        merged_lines_txt = tg_path.with_suffix('.merged_aligned.txt')
        if merged_lines_txt.exists():
            response = input(f"{merged_lines_txt} already exists, do you want to overwrite it? (y/n)")
            skip = response.lower().strip() == 'n'
        if skip:
            return
        with open(aligned_txt, 'r', encoding='utf-8') as f:
            all_line_timestamps = [TextSegment(*map(float, line.split('\t')[1:3]), line.split('\t')[3].strip()) for line in f]
        merged_line_timestamps = []
        current_start = all_line_timestamps[0].start_time
        current_end = all_line_timestamps[0].end_time
        current_text = all_line_timestamps[0].line_text
        for timestamp in all_line_timestamps[1:]:
            if timestamp.end_time - current_start > MAX_MERGED_LINE_TIME:
                merged_line_timestamps.append(TextSegment(current_start, current_end,current_text))
                current_start = timestamp.start_time
                current_text = ""
            current_end = timestamp.end_time
            connector = "、" if re.search(fr'[{Japanese_characters}{Full_width_alpnums}]$', current_text) else ""
            current_text += connector + timestamp.line_text
        merged_line_timestamps.append(TextSegment(current_start, current_end, current_text))
        with open(merged_lines_txt, 'w', encoding='utf-8') as f:
            for i, line in enumerate(merged_line_timestamps):
                if i > 0 and merged_line_timestamps[i].start_time - merged_line_timestamps[i-1].end_time < 0.5:
                    logger.warning(f"Merged_line {i+1} too close to previous line: {merged_line_timestamps[i].start_time - merged_line_timestamps[i-1].end_time:.2f} seconds")
                line_num = i + 1
                def format_time(total_seconds):
                    minutes, seconds = divmod(total_seconds, 60)
                    return f"{int(minutes):02}:{seconds:05.2f}"
                f.write(f"{line_num}\t{format_time(line.start_time)}\t{format_time(line.end_time)}\t{line.line_text}\n")

    def split_audio(self, timestamps: List[LineSegment],audio_path = None):
        """Split audio based on timestamps"""
        if not timestamps or not audio_path:
            return
        audio = Path(audio_path)
        if not audio.exists():
            return
        output = audio.parent / "split"
        output.mkdir(parents=True, exist_ok=True)
        timestamps.sort(key=lambda x: x.start_time)
        time_ranges = []
        time_boundary = 25.0
        current_start = timestamps[0].start_time
        current_end = timestamps[0].end_time
        for timestamp in timestamps[1:]:
            if timestamp.end_time - current_start > time_boundary:
                time_ranges.append((current_start, current_end))
                current_start = timestamp.start_time
            current_end = timestamp.end_time
        time_ranges.append((current_start, current_end))
        for time_range in time_ranges:
            start_time = time_range[0]
            end_time = time_range[1]
            output_path = output.joinpath(audio.stem + f"_{start_time:.1f}_{end_time:.1f}{audio.suffix}")
            subprocess.run([
                "ffmpeg", "-i", audio_path, "-ss", str(start_time), "-to", str(end_time),
                "-c", "copy", output_path
            ])
    
